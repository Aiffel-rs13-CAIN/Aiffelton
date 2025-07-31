from typing import Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage


# init 
# process

class LLMNode:
    def __init__(self, agent_core):
        self.agent_core = agent_core
        # init
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        messages = state.get('messages', [])
        
        # RAG 컨텍스트 추가
        if state.get('context'):
            context_msg = HumanMessage(content=f"[참고 컨텍스트]\n{state['context']}")
            messages = list(messages) + [context_msg]
        
        try:
            response = self.agent_core.get_llm().invoke(messages)
            return {"messages": [response]}
        except Exception as e:
            print(f"LLM 호출 오류: {e}")
            return {"messages": []}