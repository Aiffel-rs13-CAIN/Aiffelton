from modules.memory_module import MemoryNode
from modules.rag_module import RAGNode
from modules.llm_module import LLMNode
from modules.tool_module import ToolNode
from modules.user_input_module import UserInputNode
from modules.output_module import OutputNode
from workflows.workflow_controller import WorkflowController

class WorkflowFactory:
    """워크플로우 생성을 위한 팩토리 클래스"""
    
    def __init__(self, agent_core):
        self.agent_core = agent_core
        # 노드 인스턴스 생성
        self.user_input_node = UserInputNode(agent_core)
        self.memory_node = MemoryNode(agent_core)
        self.rag_node = RAGNode(agent_core)
        self.llm_node = LLMNode(agent_core)
        self.tool_node = ToolNode(agent_core)
        self.output_node = OutputNode(agent_core)
        self.controller = WorkflowController(agent_core)
    
    def user_input_node_func(self, state):
        """사용자 입력 노드 함수"""
        return self.user_input_node.process(state)
    
    def memory_node_func(self, state):
        """메모리 노드 함수"""
        return self.memory_node.process(state)
    
    def rag_node_func(self, state):
        """RAG 노드 함수"""
        return self.rag_node.process(state)
    
    def llm_node_func(self, state):
        """LLM 노드 함수"""
        return self.llm_node.process(state)
    
    def tool_node_func(self, state):
        """도구 노드 함수"""
        return self.tool_node.process(state)
    
    def output_node_func(self, state):
        """출력 노드 함수"""
        return self.output_node.process(state)
    
    def should_continue(self, state):
        """워크플로우 계속 진행 여부 결정"""
        return self.controller.should_continue(state)
    
    def should_exit(self, state):
        """종료 여부 결정"""
        return "exit" if state.get("should_exit", False) else "continue"
