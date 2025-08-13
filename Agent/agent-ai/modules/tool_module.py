import asyncio
import sys
import os
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

        # ✅ 수정: __init__ 메서드에서 비동기 루프 관련 로직을 모두 제거합니다.
        # DynamicMCPManager의 시작은 main.py의 메인 루프에서 담당하도록 합니다.
        if not ToolNode._started:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                tmp_loop = asyncio.new_event_loop()
                tmp_loop.run_until_complete(ToolNode._manager.start())
            else:
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

        # ✅ new_messages 변수를 미리 선언합니다.
        new_messages = []

        try:
            print("DEBUG: ainvoke_messages 호출 전. 입력 메시지:", messages)
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 러닝 루프에서는 별도 임시 루프 사용
                tmp = asyncio.new_event_loop()
                new_messages = tmp.run_until_complete(
                    ToolNode._manager.ainvoke_messages(messages)
                )
            else:
                new_messages = loop.run_until_complete(
                    ToolNode._manager.ainvoke_messages(messages)
                )
            print("DEBUG: ainvoke_messages 호출 후. 반환된 메시지:", new_messages)
        except RuntimeError:
            # 루프가 없으면 새로 만들어 실행
            tmp = asyncio.new_event_loop()
            asyncio.set_event_loop(tmp)
            new_messages = tmp.run_until_complete(
                ToolNode._manager.ainvoke_messages(messages)
            )
            print("DEBUG: ainvoke_messages 호출 후. 반환된 메시지 (예외 처리):", new_messages)

        # -------------------------------------------------------------------
        # ✅ 여기부터는 new_messages 변수가 항상 유효하도록 보장됨
        # -------------------------------------------------------------------

        # tool_results에 MCP agent 실행 흔적 남기기
        tool_results = state.get("tool_results", [])

        # ✅ ToolMessage에 오류가 있는지 확인하고 상태에 반영
        has_error = False
        for msg in new_messages:
            if hasattr(msg, 'status') and msg.status == 'error':
                print(f"DEBUG: 툴 실행 오류 감지! 메시지: {msg.content}")
                has_error = True
                tool_results.append({
                    "tool": "mcp_react_agent",
                    "result": "execution_failed",
                    "error_message": msg.content
                })
                # 오류 발생 시 더 이상 진행하지 않고 상태를 반환
                return {
                    **state,
                    "messages": new_messages,
                    "tool_results": tool_results,
                    "should_exit": True  # 워크플로우에 따라 적절히 변경 필요
                }

        # ✅ 사용된 도구들을 감지해서 기록
        used_tools = []
        for msg in new_messages:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                print(f"DEBUG: 'tool_calls' 감지! 메시지 내용: {msg}")
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