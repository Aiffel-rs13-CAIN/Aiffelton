from typing import Dict, Any

class WorkflowController:
    def __init__(self, agent_core):
        self.agent_core = agent_core
    
    def should_continue(self, state: Dict[str, Any]) -> str:
        messages = state.get('messages', [])
        if not messages:
            return "end"
        
        last_message = messages[-1]
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        return "end"

# 향후 워크플로우 관련 클래스들을 여기에 추가할 수 있습니다
# class ConditionalRouter:
#     pass
# class StateManager:
#     pass
