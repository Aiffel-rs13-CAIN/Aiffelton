from typing import Dict, Any

# 간단한 메시지 클래스 (LangChain 없을 때 사용)
class HumanMessage:
    def __init__(self, content):
        self.content = content

# LangChain이 있다면 사용
try:
    from langchain_core.messages import HumanMessage as LangChainHumanMessage
    HumanMessage = LangChainHumanMessage
except ImportError:
    pass  # 위에서 정의한 간단한 HumanMessage 사용

class UserInputNode:
    def __init__(self, agent_core):
        self.agent_core = agent_core
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        try:
            user_input = input("사용자: ")
            
            # 종료 조건
            if user_input.lower() in ['exit', 'quit', '종료']:
                return {"should_exit": True, "messages": state.get("messages", [])}
            
            # 새로운 메시지를 상태에 추가
            current_messages = state.get("messages", [])
            new_message = HumanMessage(content=user_input)
            
            return {
                **state,  # 기존 상태 유지
                "messages": current_messages + [new_message],
                "should_exit": False
            }
            
        except (KeyboardInterrupt, EOFError):
            print("\n에이전트를 종료합니다.")
            return {"should_exit": True, "messages": state.get("messages", [])}
