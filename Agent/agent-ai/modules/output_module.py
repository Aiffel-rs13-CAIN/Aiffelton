from typing import Dict, Any

class OutputNode:
    def __init__(self, agent_core):
        self.agent_core = agent_core
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        messages = state.get("messages", [])
        
        if messages:
            last_message = messages[-1]
            # AI 메시지인 경우 출력
            if hasattr(last_message, 'content'):
                print(f"에이전트: {last_message.content}")
            else:
                print(f"에이전트: {str(last_message)}")
        
        # 상태를 그대로 반환 (should_exit 포함)
        return {
            **state,
            "should_exit": state.get("should_exit", False)
        }
