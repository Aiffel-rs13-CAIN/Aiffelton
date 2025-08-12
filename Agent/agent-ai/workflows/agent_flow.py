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
    # A2A 통신 관련 상태
    a2a_request: dict = {}  # A2A 요청 정보
    a2a_response: list = []  # A2A 응답
    a2a_task: object = None  # A2A 비동기 태스크

def create_single_agent_workflow(config_path: str = "config/config.yaml"):
    """단일 에이전트 워크플로우 생성"""
    factory = WorkflowFactory(config_path)
    

    workflow = StateGraph(AgentState)
    
    workflow.add_node("user_input", factory.user_input_node_func)
    workflow.add_node("memory", factory.memory_node_func)
    workflow.add_node("rag", factory.rag_node_func)
    workflow.add_node("llm", factory.llm_node_func)
    workflow.add_node("tools", factory.tool_node_func)
    workflow.add_node("a2a_comm", factory.a2a_comm_node_func)
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
    
    # 도구 실행 후 다시 LLM으로
    workflow.add_edge("tools", "llm")
    
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


async def create_a2a_enabled_workflow(config_path: str = "config/config.yaml", a2a_config=None):
    """A2A 통신이 활성화된 워크플로우 생성"""
    factory = WorkflowFactory(config_path)
    
    # A2A 통신 노드 초기화
    await factory.initialize_a2a_node(a2a_config)
    
    workflow = StateGraph(AgentState)
    
    workflow.add_node("user_input", factory.user_input_node_func)
    workflow.add_node("memory", factory.memory_node_func)
    workflow.add_node("rag", factory.rag_node_func)
    workflow.add_node("llm", factory.llm_node_func)
    workflow.add_node("tools", factory.tool_node_func)
    workflow.add_node("a2a_comm", factory.a2a_comm_node_func)
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
    
    # LLM 후 A2A 통신 필요 여부 확인
    def should_use_a2a(state):
        """A2A 통신 사용 여부 결정"""
        if state.get("a2a_request"):
            return "a2a_comm"
        return factory.should_continue(state)
    
    workflow.add_conditional_edges(
        "llm",
        should_use_a2a,
        {
            "a2a_comm": "a2a_comm",
            "tools": "tools", 
            "end": "output"
        }
    )
    
    # A2A 통신 후 출력으로
    workflow.add_edge("a2a_comm", "output")
    
    # 도구 실행 후 다시 LLM으로
    workflow.add_edge("tools", "llm")
    
    # 출력 후 종료 여부 확인 (루프 제어)
    workflow.add_conditional_edges(
        "output",
        factory.should_exit,
        {
            "exit": END,
            "continue": "user_input"
        }
    )
    
    compiled_workflow = workflow.compile()
    
    # 정리 함수를 workflow에 추가
    compiled_workflow._factory = factory
    compiled_workflow.cleanup = factory.cleanup_a2a_node
    
    return compiled_workflow
