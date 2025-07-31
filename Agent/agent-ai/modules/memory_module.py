from typing import Dict, Any

class MemoryNode:
    def __init__(self, agent_core):
        self.agent_core = agent_core
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """메모리 노드 처리 로직"""
        # 현재는 메모리 기능이 제거되었으므로 빈 딕셔너리 반환
        return {"memory": {}}