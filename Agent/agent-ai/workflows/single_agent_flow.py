# workflows/single_agent_flow.py
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage
from typing import TypedDict, Annotated, Sequence, List
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
    agent_manager: object  = None
def create_single_agent_workflow(agent_core, all_tools):
    factory = WorkflowFactory(agent_core, all_tools)
    

    workflow = StateGraph(AgentState)

    # 노드 추가
    workflow.add_node("user_input", factory.user_input_node_func)
    workflow.add_node("memory", factory.memory_node_func)
    workflow.add_node("rag", factory.rag_node_func)
    workflow.add_node("llm", factory.llm_node_func)
    workflow.add_node("tools", factory.tool_node_func)
    workflow.add_node("post_process", factory.post_process_node_func) # 후처리 노드 추가
    workflow.add_node("output", factory.output_node_func)

    # 엣지(흐름) 구성
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
    
    # 출력 후 종료 여부 확인 (루프 제어)

        # 도구 실행 후 다시 LLM으로
    workflow.add_edge("tools", "post_process")

    workflow.add_edge("post_process", "output")    

    workflow.add_conditional_edges(
        "output",
        factory.should_exit,
        {
            "exit": END,
            "continue": "user_input"
        }
    )

    # workflow.add_edge("output", END)  # 후처리 후 다시 LLM으로

    return workflow.compile()
