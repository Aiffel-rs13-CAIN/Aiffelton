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

    # ✅ RAG와 LLM 사이에 MCP 도구 결정 로직 추가
    def decide_before_llm(state):
        messages = state.get("messages", [])
        if not messages:
            return "output"

        last_user_msg = messages[0]  # 첫 번째 메시지가 사용자 메시지라고 가정
        if hasattr(last_user_msg, 'content'):
            content = str(last_user_msg.content).lower()

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

        # 시간 관련 키워드가 없으면 LLM으로 진행
        return "llm"

    workflow.add_conditional_edges(
        "rag",  # RAG 노드 다음에 조건부 엣지 추가
        decide_before_llm,
        {
            "mcp_tools": "mcp_tools",
            "llm": "llm"
        }
    )

    # LLM 노드 후에는 툴 호출이 없으면 바로 출력으로 이동
    def decide_after_llm_simplified(state):
        """LLM 후 다음 단계 결정 - 시간 관련 요청은 MCP 도구 우선"""
        messages = state.get("messages", [])
        if hasattr(messages[-1], 'tool_calls') and messages[-1].tool_calls:
            return "mcp_tools"  # LLM이 툴 호출을 결정했다면 다시 mcp_tools로
        return "output"

    # LLM 노드의 조건부 엣지 수정
    workflow.add_conditional_edges(
        "llm",
        decide_after_llm_simplified,
        {
            "mcp_tools": "mcp_tools",
            "output": "output"
        }
    )

    # 툴 실행 후 LLM으로 돌아가기
    workflow.add_edge("mcp_tools", "llm")

    # ✅ LLM의 최종 응답은 출력으로 이동
    workflow.add_edge("llm", "output")

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