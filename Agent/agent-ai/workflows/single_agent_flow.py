from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage
from typing import TypedDict, Annotated, Sequence
import operator
from dotenv import load_dotenv

# 워크플로우 팩토리 import
from workflows.workflow_factory import WorkflowFactory

load_dotenv()

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    context: str = ""  
    memory: dict = {} 
    tool_results: list = []
    should_exit: bool = False
    user_id: str = "default_user"
    last_response: str = ""
    agent_manager: object = None  # A2A AgentManager 추가
    
def create_single_agent_workflow(agent_core):
    """단일 에이전트 워크플로우 생성 (A2A 미포함 기본 플로우)"""
    factory = WorkflowFactory(agent_core)
    

    workflow = StateGraph(AgentState)
    
    workflow.add_node("user_input", factory.user_input_node_func)
    workflow.add_node("memory", factory.memory_node_func)
    workflow.add_node("rag", factory.rag_node_func)
    workflow.add_node("llm", factory.llm_node_func)
    workflow.add_node("tools", factory.tool_node_func)
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
    
    # 기존 워크플로우 흐름
    workflow.add_edge("memory", "rag")
    workflow.add_edge("rag", "llm")
    
    # LLM 후 도구 사용 여부 결정
    workflow.add_conditional_edges(
        "llm",
        factory.should_continue,
        {
            "tools": "tools",
            "end": "output"
        }
    )
    
    # 도구 실행 후 바로 출력으로 (LLM을 거치지 않음 - Gemini 규칙 준수)
    workflow.add_edge("tools", "output")
    
    # 출력 후 종료 (사용자가 다시 시작할 때까지)
    workflow.add_edge("output", END)
    
    return workflow.compile()
