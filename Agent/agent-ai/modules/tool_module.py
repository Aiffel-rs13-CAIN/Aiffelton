# agent-ai/modules/tool_module.py
import asyncio
from typing import Dict, Any, List
from .mcp_module import DynamicMCPManager


class ToolNode:
    """
    - LangGraph 워크플로우 내 '도구 실행' 노드
    - config/mcp_config.json만 수정/저장하면 툴 구성이 즉시 갱신(핫 리로드)
    - 입력: state(dict) - 최소 {"messages": [...]} 필요
    - 출력: {"messages": [...], "tool_results": [...]}  형태로 반환
    - ✅ 이제 LLM이 자율적으로 도구 사용을 결정할 수 있음
    """
    _manager: DynamicMCPManager = None
    _started: bool = False

    def __init__(self, config):
        # 기본 경로: config/mcp_config.json
        cfg_path = "config/mcp_config.json"
        try:
            cfg_path = config.get("tools", {}).get("mcp_config_path", cfg_path)
        except Exception:
            pass

        if ToolNode._manager is None:
            ToolNode._manager = DynamicMCPManager(cfg_path)

        if not ToolNode._started:
            # 별도 이벤트 루프 생성 후 동기 대기로 초기화 보장
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 이미 러닝 루프가 있다면, 임시 새 루프에서 실행
                    loop = asyncio.new_event_loop()
                    loop.run_until_complete(ToolNode._manager.start())
                    loop.close()
                else:
                    loop.run_until_complete(ToolNode._manager.start())
            except RuntimeError:
                # get_event_loop 실패 시 새 루프 생성
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(ToolNode._manager.start())
            ToolNode._started = True

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        동기 인터페이스: 내부에서 비동기 MCP 호출을 실행.
        ✅ MCP ReAct 에이전트가 자율적으로 도구 사용을 결정
        """
        messages: List[Any] = state.get("messages", [])
        if not messages:
            return {**state, "tool_results": state.get("tool_results", [])}

        # ✅ ainvoke_messages를 동기 실행 - ReAct 에이전트가 도구 사용을 자율 결정
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 러닝 루프에서는 별도 임시 루프 사용
                tmp = asyncio.new_event_loop()
                new_messages = tmp.run_until_complete(
                    ToolNode._manager.ainvoke_messages(messages)
                )
                tmp.close()
            else:
                new_messages = loop.run_until_complete(
                    ToolNode._manager.ainvoke_messages(messages)
                )
        except RuntimeError:
            # 루프가 없으면 새로 만들어 실행
            tmp = asyncio.new_event_loop()
            asyncio.set_event_loop(tmp)
            new_messages = tmp.run_until_complete(
                ToolNode._manager.ainvoke_messages(messages)
            )

        # tool_results에 MCP agent 실행 흔적 남기기
        tool_results = state.get("tool_results", [])

        # ✅ 사용된 도구들을 감지해서 기록
        used_tools = []
        for msg in new_messages:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    used_tools.append(tool_call.get('name', 'unknown_tool'))

        if used_tools:
            tool_results.append({
                "tool": "mcp_react_agent",
                "used_tools": used_tools,
                "result": "executed_with_tools"
            })
        else:
            tool_results.append({
                "tool": "mcp_react_agent",
                "result": "executed_without_tools"
            })

        return {
            **state,
            "messages": new_messages,
            "tool_results": tool_results,
        }

    @classmethod
    def get_available_tools(cls) -> List[Any]:
        """사용 가능한 도구 목록 반환"""
        if cls._manager is None:
            return []
        return cls._manager.get_available_tools()