import asyncio
from typing import List, Dict, Any, Coroutine
from langchain_core.tools import BaseTool
from langchain_core.messages import ToolMessage
from concurrent.futures import ThreadPoolExecutor
from .a2a_manager import get_a2a_manager

class ToolNode:
    def __init__(self,tools: List[BaseTool]):
        self.tools_by_name = {tool.name: tool for tool in tools}

    async def _execute_tool(self, tool_call: Dict[str, Any]) -> ToolMessage:
        """단일 도구 호출을 비동기적으로 실행하고 결과를 ToolMessage로 반환"""
        print(f"[ToolNode] tool_call 요청: {tool_call}")
        tool_name = tool_call.get("name")
        tool_args = tool_call.get("args", {}) or {}
        tool_id = tool_call.get("id")

        observation = None
        if tool_name == "a2a_send":
            try:
                observation = await self._handle_a2a_send(tool_args)
            except Exception as e:
                observation = f"Error during a2a_send: {e}"
        else:
            tool_to_invoke = self.tools_by_name.get(tool_name)
            if not tool_to_invoke:
                observation = f"Error: Tool '{tool_name}' not found."
            else:
                try:
                    # 도구를 비동기적으로 실행
                    observation = await tool_to_invoke.ainvoke(tool_args)
                except Exception as e:
                    observation = f"Error executing tool {tool_name}: {e}"

        # 안전한 디버그 출력: observation이 항상 정의되도록 보장
        print(f"[ToolNode] tool_call 결과: {observation}")

        return ToolMessage(
            content=str(observation),
            tool_call_id=tool_id
        )
    
    async def _handle_a2a_send(self, args: Dict[str, Any]) -> str:
        """A2A 전송을 비동기로 처리"""
        agent_name = args.get("agent_name") or args.get("agent")
        text = args.get("text") or args.get("message")
        if not agent_name or not text:
            return "오류: agent_name과 text가 필요합니다."
        try:
            manager = get_a2a_manager()
            response = await manager.send(agent_name, text)
            if response:
                return f"✅ '{agent_name}'에게 메시지 전송 완료. 응답: {response}"
            else:
                return f"⚠️ '{agent_name}'에게 메시지 전송했지만 응답이 없습니다."
        except Exception as e:
            return f"❌ A2A 전송 오류: {str(e)}"

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """상태(state)에서 tool_calls를 찾아 모든 도구를 병렬로 실행"""
        messages = state.get("messages", [])
        if not messages:
            return state
        last_message = messages[-1]
        tool_calls = getattr(last_message, "tool_calls", None)
        if not tool_calls:
            return state

        print(f"🔧 도구 호출 감지: {len(tool_calls)}개")
        tasks: List[Coroutine] = [self._execute_tool(call) for call in tool_calls]
        results: List[ToolMessage] = await asyncio.gather(*tasks)
        new_messages = list(messages) + results
        return {"messages": new_messages}

# 향후 도구 관련 클래스들을 여기에 추가할 수 있습니다
# class CalculatorTool:
#     pass
# class SearchTool:
#     pass
