from typing import Dict, Any

class WorkflowController:
    def __init__(self, config: Dict[str, Any] = None):
        """
        워크플로우 컨트롤러 초기화
        
        Args:
            config: 워크플로우 제어 관련 설정
        """
        if config is None:
            config = {}
        self.config = config
    
    def should_continue(self, state: Dict[str, Any]) -> str:
        """워크플로우 계속 진행 여부 결정"""
        messages = state.get('messages', [])
        if not messages:
            return "end"
        
        last_message = messages[-1]
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        return "end"
    
    def should_exit(self, state: Dict[str, Any]) -> str:
        """워크플로우 종료 여부 결정"""
        should_exit = state.get("should_exit", False)
        if should_exit:
            return "exit"
        return "continue"

# 향후 워크플로우 관련 클래스들을 여기에 추가할 수 있습니다
# class ConditionalRouter:
#     pass
# class StateManager:
#     pass
