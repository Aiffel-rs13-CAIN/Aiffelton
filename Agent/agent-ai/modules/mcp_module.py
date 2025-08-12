# agent-ai/modules/mcp_module.py
import asyncio
import json
import os
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# MCP 어댑터
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

# LangGraph / LangChain
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
)


# -------------------------------
# 내부 유틸 / 프록시
# 툴 집합을 보관/교체
# -------------------------------

class _AgentProxy:
    def __init__(self):
        self._agent = None
        self._tools = []
        self._lock = threading.RLock()

    # 에이전트/툴 세트 교환
    def swap(self, agent, tools):
        with self._lock:
            self._agent = agent
            self._tools = tools

    # 현재 에이전트
    def current(self):
        with self._lock:
            return self._agent

    # 현재 등록된 툴 목록
    def get_tools(self):
        with self._lock:
            return list(self._tools)


def _load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _to_mcp_client_config(cfg: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    mcp_config.json의 "servers"와 "mcpServers" 블록을 MultiServerMCPClient 형식으로 변환
    두 형식을 모두 지원:
    1. "servers": {"name": {"transport": "stdio", "command": "...", ...}} (기존 형식)
    2. "mcpServers": {"name": {"command": "...", "args": [...], "cwd": "..."}} (Smithery 형식)
    """
    out: Dict[str, Dict[str, Any]] = {}

    # "servers" 형식 처리 (직접 만드는 경우)
    for name, s in cfg.get("servers", {}).items():
        t = s.get("transport")
        if t == "stdio":
            out[name] = {
                "transport": "stdio",
                "command": s["command"],
                "args": s.get("args", []),
                "env": s.get("env", {}),
            }
            if "cwd" in s:
                out[name]["cwd"] = s["cwd"]
        elif t == "streamable_http":
            out[name] = {
                "transport": "streamable_http",
                "url": s["url"],
                "headers": s.get("headers", {}),
            }
        else:
            print(f"Unsupported transport in servers: {t}")

    # "mcpServers" 형식 처리 (Smithery 스타일)
    for name, s in cfg.get("mcpServers", {}).items():
        server_config = {
            "transport": "stdio",
            "command": s.get("command", "python"),
            "args": s.get("args", []),
            "env": s.get("env", {}),
        }

        if "cwd" in s:
            server_config["cwd"] = s["cwd"]

        out[name] = server_config
        print(f"📦 Added mcpServer: {name} -> {s.get('command')} {s.get('args', [])}")

    return out


def _parse_model_id(raw: str) -> str:
    """
    "openai:gpt-4o-mini" 같은 형식도 허용. 콜론 뒤 토큰을 모델명으로 사용.
    """
    if not raw:
        return "gpt-4o"
    return raw.split(":")[-1].strip() or "gpt-4o"


def _normalize_messages(messages: List[Any]) -> List[BaseMessage]:
    """
    입력 messages를 LangChain BaseMessage들로 정규화.
    """
    norm: List[BaseMessage] = []

    def _from_role(role: str, content: Any) -> BaseMessage:
        r = (role or "").lower()
        if r in ("human", "user"):
            return HumanMessage(content=str(content))
        if r in ("ai", "assistant"):
            return AIMessage(content=str(content))
        if r == "system":
            return SystemMessage(content=str(content))
        if r == "tool":
            return ToolMessage(content=str(content), tool_call_id="dynamic-mcp")
        return HumanMessage(content=str(content))

    for m in messages:
        if isinstance(m, BaseMessage):
            norm.append(m)
        elif isinstance(m, str):
            norm.append(HumanMessage(content=m))
        elif isinstance(m, tuple) and len(m) == 2:
            role, content = m
            norm.append(_from_role(str(role), content))
        elif isinstance(m, dict):
            role = m.get("role", "user")
            content = m.get("content", "")
            norm.append(_from_role(str(role), content))
        else:
            norm.append(HumanMessage(content=str(m)))
    return norm


async def _build_agent(cfg: Dict[str, Any]):
    """
    - MCP 서버 연결 (servers + mcpServers 모두 처리)
    - 서버별 세션을 열어 툴 로딩/필터링
    - LLM 인스턴스 생성
    - ReAct agent 구성
    """
    client = MultiServerMCPClient(_to_mcp_client_config(cfg))

    # 모든 서버에서 툴 수집
    all_tools = []

    # servers와 mcpServers 모두에서 서버 이름 수집
    all_server_names = list(cfg.get("servers", {}).keys()) + list(cfg.get("mcpServers", {}).keys())

    print(f"🔌 Connecting to {len(all_server_names)} MCP servers: {all_server_names}")

    for server_name in all_server_names:
        try:
            async with client.session(server_name) as session:
                ts = await load_mcp_tools(session)
                all_tools.extend(ts)
                print(f"✅ {server_name}: loaded {len(ts)} tools")
        except Exception as e:
            print(f"❌ {server_name}: connection failed - {e}")
            # 한 서버가 실패해도 계속 진행

    print("🧰 Total loaded MCP tools:", [t.name for t in all_tools])

    # allow/deny 필터
    allow = set(cfg.get("tool_filters", {}).get("allow", []))
    deny = set(cfg.get("tool_filters", {}).get("deny", []))
    tools = all_tools
    if allow:
        tools = [t for t in tools if t.name in allow]
        print(f"🔍 Filtered by allow list: {[t.name for t in tools]}")
    if deny:
        tools = [t for t in tools if t.name not in deny]
        print(f"🔍 Filtered by deny list: {[t.name for t in tools]}")

    # LLM 모델 인스턴스 준비
    raw_model = cfg.get("model", "gpt-4o")
    model_id = _parse_model_id(raw_model)
    llm = ChatOpenAI(model=model_id, temperature=0)

    # ✅ 간단한 프롬프트로 변경 (Gemini 호환성 개선)
    # 아래 프롬프트는 테스트용 (임시)
    base_prompt = cfg.get("prompt", "You are a helpful agent.")
    enhanced_prompt = f"""{base_prompt}

사용자가 시간이나 날짜를 물어보면 get_current_time 도구를 사용해 정확한 정보를 제공하세요.
수학 계산이 필요하면 calculate_math 도구를 사용하세요.

Available tools: {[t.name for t in tools]}
"""

    # 툴 호출과 추론을 자동으로 오케스트레이션하는 langgraph의 프리셋 에이전트
    agent = create_react_agent(model=llm, tools=tools, prompt=enhanced_prompt)
    return agent, tools


# -------------------------------
# 파일 변경 감지 핸들러
# -------------------------------

class _ReloadHandler(FileSystemEventHandler):
    def __init__(self, config_path: Path, proxy: _AgentProxy, loop: asyncio.AbstractEventLoop):
        self.config_path = config_path
        self.proxy = proxy
        self.loop = loop
        self._last_mtime = 0

    def on_modified(self, event):
        if event.is_directory:
            return
        if Path(event.src_path) != self.config_path:
            return
        try:
            mtime = os.path.getmtime(self.config_path)
        except FileNotFoundError:
            return
        if mtime == self._last_mtime:
            return
        self._last_mtime = mtime
        asyncio.run_coroutine_threadsafe(self._reload(), self.loop)

    async def _reload(self):
        try:
            cfg = _load_json(self.config_path)
            agent, tools = await _build_agent(cfg)
            self.proxy.swap(agent, tools)
            print("🔁 MCP config reloaded and agent swapped (servers + mcpServers)")
        except Exception as e:
            print(f"❌ Reload failed: {e}")


# -------------------------------
# 퍼블릭 매니저
# 오케스트레이터 역할을 함
# -------------------------------

class DynamicMCPManager:
    """
    - config/mcp_config.json 변경 시 MCP 툴/에이전트 자동 재구성
    - "servers"와 "mcpServers" 두 형식 모두 지원
    - 외부에서는 ainvoke_messages와 get_available_tools 호출 가능
    """

    def __init__(self, config_path: str = "config/mcp_config.json"):
        # 경로 보정: 상대경로면 프로젝트 루트(agent-ai) 기준
        base = Path(__file__).resolve().parents[1]  # .../agent-ai
        p = Path(config_path)
        if not p.is_absolute():
            p = (base / p).resolve()
        if not p.exists():
            # 백업 후보
            alt = (base / "config" / "mcp_config.json").resolve()
            if alt.exists():
                p = alt
        self.config_path = p

        self.proxy = _AgentProxy()
        self._observer: Optional[Observer] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def start(self):
        """
        툴 세팅 최초 1회 초기화 + 파일 감시 시작
        """
        self._loop = asyncio.get_running_loop()

        print(f"🔧 Loading MCP config from: {self.config_path}")
        print(f"🔧 Config exists: {self.config_path.exists()}")

        if not self.config_path.exists():
            print(f"❌ MCP config file not found: {self.config_path}")
            # 빈 도구로 초기화
            self.proxy.swap(None, [])
            return

        try:
            cfg = _load_json(self.config_path)
            print(f"🔧 Config loaded successfully")

            agent, tools = await _build_agent(cfg)
            self.proxy.swap(agent, tools)

            # 서버 개수 표시
            server_count = len(cfg.get("servers", {})) + len(cfg.get("mcpServers", {}))
            print(
                f"✅ MCP agent initialized with {server_count} servers, {len(tools)} tools (config={self.config_path})")

            # 도구 목록 출력
            if tools:
                print("🔧 Available MCP tools:")
                for tool in tools:
                    print(f"   - {tool.name}: {tool.description}")
            else:
                print("⚠️  No MCP tools available")

            handler = _ReloadHandler(self.config_path, self.proxy, self._loop)
            self._observer = Observer()
            self._observer.schedule(handler, self.config_path.parent.as_posix(), recursive=False)
            self._observer.start()
            print(f"👀 Watching: {self.config_path}")

        except Exception as e:
            print(f"❌ Failed to initialize MCP agent: {e}")
            import traceback
            traceback.print_exc()
            # 빈 도구로 초기화
            self.proxy.swap(None, [])

    async def ainvoke_messages(self, state_messages: List[Any]) -> List[BaseMessage]:
        """
        create_react_agent 규약: {"messages": [...]} I/O
        ✅ Gemini API 호환성을 위한 메시지 정리 추가
        """
        agent = self.proxy.current()
        if agent is None:
            raise RuntimeError("MCP agent not ready")

        normalized = _normalize_messages(state_messages)

        # ✅ Gemini API를 위한 메시지 시퀀스 정리
        cleaned_messages = []
        for msg in normalized:
            # 사용자 메시지만 유지 (함수 호출 순서 문제 방지)
            if isinstance(msg, HumanMessage):
                cleaned_messages.append(msg)

        if not cleaned_messages:
            # 메시지가 없으면 빈 결과 반환
            return normalized

        try:
            result: Dict[str, Any] = await agent.ainvoke({"messages": cleaned_messages})
            return result.get("messages", result)
        except Exception as e:
            print(f"MCP agent 호출 오류: {e}")
            # 실패시 원본 메시지에 시간 정보 추가
            from datetime import datetime
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 시간 관련 응답 생성
            time_response = AIMessage(content=f"현재 시간은 {current_time} 입니다.")
            return normalized + [time_response]

    def get_available_tools(self) -> List[Any]:
        """사용 가능한 도구 목록 반환"""
        return self.proxy.get_tools()

    def stop(self):
        if self._observer:
            self._observer.stop()
            self._observer.join()
            print("🛑 File watcher stopped.")