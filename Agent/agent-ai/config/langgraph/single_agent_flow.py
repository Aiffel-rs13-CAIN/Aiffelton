# agentic-ai/config/langgraph/single_agent_flow.py
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage
from typing import TypedDict, Annotated, Sequence
import operator
from dotenv import load_dotenv

load_dotenv()

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    context: str = ""  
    memory: dict = {} 
    tool_results: list = []  # 툴 실행 결과 

def create_single_agent_workflow(agent_core):
    def memory_node(state):
        memory_data = agent_core.get_memory()
        return {"memory": memory_data or {}}
    
    def rag_node(state):
        # RAG 검색 로직 (현재는 구현되지 않음)
        # context = agent_core.rag_module.search(state['messages'][-1].content)
        return {"context": "검색된 컨텍스트 (RAG 모듈 미구현)"}
    
    def llm_node(state):
        messages = state['messages']
        # RAG 컨텍스트가 있다면 추가
        if state.get('context'):
            # 시스템 메시지에 컨텍스트 추가 로직
            pass
            
        try:
            response = agent_core.get_llm().invoke(messages)
            return {"messages": [response]}
        except Exception as e:
            print(f"LLM 호출 오류: {e}")
            return {"messages": []}
    
    def tool_node(state):
        tools = agent_core.get_tools()
        # 현재는 툴이 구현되지 않아 빈 결과 반환
        return {"tool_results": []}
    
    def should_continue(state):
        last_message = state['messages'][-1]
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        return "end"
    
    workflow = StateGraph(AgentState)
    
    workflow.add_node("memory", memory_node)
    workflow.add_node("rag", rag_node)
    workflow.add_node("llm", llm_node)
    workflow.add_node("tools", tool_node)
    
    workflow.set_entry_point("memory")
    workflow.add_edge("memory", "rag")
    workflow.add_edge("rag", "llm")
    
    # LLM 이후 조건부 분기
    workflow.add_conditional_edges(
        "llm",
        should_continue,
        {
            "tools": "tools",
            "end": END
        }
    )
    
    workflow.add_edge("tools", "llm")
    
    return workflow.compile()
