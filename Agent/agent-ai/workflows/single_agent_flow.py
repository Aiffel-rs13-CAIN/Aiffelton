from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage
from typing import TypedDict, Annotated, Sequence
import operator
from dotenv import load_dotenv

# 워크플로우 팩토리 import
from workflows.workflow_factory import WorkflowFactory

load_dotenv()

#그래프 상태(메모리) 정의
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    context: str = ""
    memory: dict = {}
    tool_results: list = []
    should_exit: bool = False
    user_id: str = "default_user"
    last_response: str = ""

def create_single_agent_workflow(agent_core):
    factory = WorkflowFactory(agent_core)

    workflow = StateGraph(AgentState)

    workflow.add_node("user_input", factory.user_input_node_func)
    workflow.add_node("memory", factory.memory_node_func)
    workflow.add_node("rag", factory.rag_node_func)
    workflow.add_node("llm", factory.llm_node_func)
    workflow.add_node("tools", factory.tool_node_func)
    workflow.add_node("mcp_tools", factory.mcp_tool_node_func) # MCP 도구 노드 추가
    workflow.add_node("output", factory.output_node_func)

    workflow.set_entry_point("user_input")

    # 사용자 입력 후 종료 여부 확인
    workflow.add_conditional_edges(
        "user_input",
        factory.should_exit,
        {
            "exit": END,
            "continue": "memory"
        }
    )

    # 메모리 -> RAG -> LLM 순서로 진행 (MCP 도구는 LLM 이후로 이동)
    workflow.add_edge("memory", "rag")
    workflow.add_edge("rag", "llm")

    # ✅ LLM 후 조건부 분기: MCP 도구 우선 실행 (툴 콜링 이슈로 인한 임시 코드)
    def decide_after_llm(state):
        """LLM 후 다음 단계 결정 - 시간 관련 요청은 MCP 도구 우선"""
        messages = state.get("messages", [])
        if not messages:
            return "output"

        # 원본 사용자 메시지에서 시간 관련 키워드 확인
        user_messages = []
        for msg in messages:
            if hasattr(msg, 'type') and msg.type == 'human':
                user_messages.append(msg)
            elif hasattr(msg, 'content') and not hasattr(msg, 'tool_calls'):
                # HumanMessage 클래스인 경우
                if 'HumanMessage' in str(type(msg)):
                    user_messages.append(msg)

        if user_messages:
            last_user_msg = user_messages[-1]
            content = ""
            if hasattr(last_user_msg, 'content'):
                content = str(last_user_msg.content).lower()

            # 시간 관련 키워드 확인 (더 넓은 범위)
            time_keywords = [
                '시간', '현재시간', '지금시간', '몇시', '시각',
                'time', 'current time', 'what time',
                '날짜', '오늘', '지금', 'date', 'today', 'now',
                '언제', 'when'
            ]

            for keyword in time_keywords:
                if keyword in content:
                    print(f"🕒 시간 관련 키워드 '{keyword}' 감지, MCP 도구 실행")
                    return "mcp_tools"

        # AI 메시지에 tool_calls가 있으면 기존 도구 사용
        last_message = messages[-1]
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"

        return "output"

    workflow.add_conditional_edges(
        "llm",
        decide_after_llm,
        {
            "tools": "tools",
            "mcp_tools": "mcp_tools",
            "output": "output"
        }
    )

    # 도구 실행 후 다시 LLM으로 (기존 도구)
    workflow.add_edge("tools", "llm")

    # MCP 도구 실행 후 출력으로 직접 이동
    workflow.add_edge("mcp_tools", "output")

    # 출력 후 종료 여부 확인 (루프 제어)
    workflow.add_conditional_edges(
        "output",
        factory.should_exit,
        {
            "exit": END,
            "continue": "user_input"
        }
    )

    return workflow.compile()