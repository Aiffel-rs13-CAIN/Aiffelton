# modules/tool_module.py
import asyncio
from typing import List, Dict, Any, Coroutine
from langchain_core.tools import BaseTool
from langchain_core.messages import ToolMessage

class ToolNode:
    """LLM이 요청한 도구를 이름으로 직접 찾아 실행하는 커스텀 노드"""
    def __init__(self, tools: List[BaseTool]):
        # 도구 이름으로 빠르게 찾을 수 있도록 딕셔너리로 변환하여 저장
        self.tools_by_name = {tool.name: tool for tool in tools}

    async def _execute_tool(self, tool_call: Dict[str, Any]) -> ToolMessage:
        """단일 도구 호출을 비동기적으로 실행하고 결과를 ToolMessage로 반환합니다."""
        tool_name = tool_call.get("name")
        tool_to_invoke = self.tools_by_name.get(tool_name)
        
        if not tool_to_invoke:
            # 해당 이름의 도구가 없으면 에러 메시지를 반환
            observation = f"Error: Tool '{tool_name}' not found."
        else:
            try:
                # 도구를 비동기적으로 실행
                observation = await tool_to_invoke.ainvoke(tool_call.get("args", {}))
            except Exception as e:
                observation = f"Error executing tool {tool_name}: {e}"
        
        # 결과를 ToolMessage로 포장하여 반환
        return ToolMessage(
            content=str(observation),
            tool_call_id=tool_call.get('id')
        )

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """상태(state)에서 tool_calls를 찾아 모든 도구를 병렬로 실행합니다."""
        messages = state.get("messages", [])
        last_message = messages[-1]
        tool_calls = getattr(last_message, "tool_calls", None)

        if not tool_calls:
            return state # 도구 호출이 없으면 종료

        print(f"🔧 도구 호출 감지: {len(tool_calls)}개")

        # 모든 도구 호출을 비동기 작업으로 생성
        tasks: List[Coroutine] = [self._execute_tool(call) for call in tool_calls]
        
        # asyncio.gather를 사용해 모든 도구를 병렬로 실행
        results: List[ToolMessage] = await asyncio.gather(*tasks)

        # 새로운 상태를 반환
        new_messages = list(messages) + results
        return {"messages": new_messages}
