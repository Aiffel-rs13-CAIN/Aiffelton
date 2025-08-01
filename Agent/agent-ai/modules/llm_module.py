from typing import Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

class LLMNode:
    def __init__(self, agent_core):
        self.agent_core = agent_core
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LLM 노드 처리 로직"""
        messages = state.get("messages", [])
        context = state.get("context", "")
        memory_data = state.get("memory", {})
        
        # 시스템 메시지 구성
        system_content = """당신은 사용자와의 대화를 기억할 수 있는 AI 어시스턴트입니다.
        사용자가 이전에 말한 내용이나 요청한 정보를 기억하고 활용해서 답변하세요."""
        
        # 메모리에서 관련 정보 추가
        if memory_data.get('status') == 'active' and memory_data.get('related_memories'):
            related_memories = memory_data['related_memories']
            
            if related_memories and isinstance(related_memories, list):
                memory_items = []
                for memory in related_memories[:5]:  # 최대 5개의 관련 메모리
                    if isinstance(memory, dict):
                        memory_text = memory.get('memory', '')
                    else:
                        memory_text = str(memory)
                    
                    if memory_text.strip():
                        memory_items.append(f"- {memory_text}")
                
                if memory_items:
                    memory_context = "\n".join(memory_items)
                    system_content += f"\n\n📝 이전 대화에서 기억할 내용:\n{memory_context}\n\n위 정보를 참고해서 답변해주세요."
        
        # RAG 컨텍스트 추가
        if context:
            system_content += f"\n\n[참고 컨텍스트]\n{context}"
        
        # 메시지 구성
        enhanced_messages = [SystemMessage(content=system_content)]
        
        # 기존 메시지들 추가 (최근 대화만)
        if messages:
            # 최근 5개 메시지만 포함 (메모리 효율성)
            recent_messages = messages[-5:] if len(messages) > 5 else messages
            enhanced_messages.extend(recent_messages)
        
        try:
            # LLM 호출
            response = self.agent_core.get_llm().invoke(enhanced_messages)
            
            # 응답을 상태에 추가
            updated_messages = list(messages) + [response] if messages else [response]
            
            return {
                "messages": updated_messages,
                "last_response": response.content if hasattr(response, 'content') else str(response),
                "should_exit": state.get("should_exit", False)
            }
            
        except Exception as e:
            print(f"LLM 호출 오류: {e}")
            # 오류 발생 시 기본 응답
            error_message = HumanMessage(content="죄송합니다. 현재 응답을 생성할 수 없습니다.")
            return {
                "messages": list(messages) + [error_message] if messages else [error_message],
                "last_response": "오류가 발생했습니다.",
                "should_exit": state.get("should_exit", False)
            }