from modules.memory_module import MemoryNode
from modules.rag_module import RAGNode
from modules.llm_module import LLMNode
from modules.tool_module import ToolNode
from modules.user_input_module import UserInputNode
from modules.output_module import OutputNode
from modules.a2a_module import A2ANode
from workflows.workflow_controller import WorkflowController
import yaml

class WorkflowFactory:
    """워크플로우 생성을 위한 팩토리 클래스"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        워크플로우 팩토리 초기화
        
        Args:
            config_path: 설정 파일 경로
        """
        self.config_path = config_path
        
        # 각 모듈별 설정 로드
        self.config = self._load_config()
        
        # 노드 인스턴스 생성 (config 딕셔너리를 각 모듈에 전달)
        self.user_input_node = UserInputNode(self.config.get("user_input", {}))
        self.memory_node = MemoryNode(self.config.get("memory", {}))
        self.rag_node = RAGNode(self.config.get("tools", []))
        self.llm_node = LLMNode(self.config.get("llm", {}))
        self.tool_node = ToolNode(self.config.get("tools", []))
        self.output_node = OutputNode(self.config.get("output", {}))
        
        # A2A 통신 노드 (비동기 초기화 필요)
        self.a2a_node = None
        
        # 워크플로우 컨트롤러
        self.controller = WorkflowController(self.config.get("workflow", {}))
    
    def _load_config(self):
        """설정 파일 로드"""
        try:
            import yaml
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                print(f"✅ 설정 파일 로드 완료: {self.config_path}")
                return config
        except FileNotFoundError:
            print(f"⚠️ 설정 파일을 찾을 수 없습니다: {self.config_path}")
            return {}
        except Exception as e:
            print(f"❌ 설정 파일 파싱 오류: {e}")
            return {}
    
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
    
    def a2a_node_func(self, state):
        """A2A 통신 노드 함수"""
        if self.a2a_node:
            return self.a2a_node.process(state)
        else:
            print("⚠️ A2A 노드가 초기화되지 않았습니다.")
            return state
    
    async def initialize_a2a_node(self, a2a_config=None):
        """A2A 통신 노드 비동기 초기화"""
        try:
            self.a2a_node = A2ANode(a2a_config)
            await self.a2a_node.initialize()
            print("✅ A2A 노드 초기화 완료")
        except Exception as e:
            print(f"❌ A2A 노드 초기화 실패: {e}")
            self.a2a_node = None
    
    async def cleanup_a2a_node(self):
        """A2A 노드 정리"""
        if self.a2a_node:
            await self.a2a_node.cleanup()
            self.a2a_node = None
    
    def should_continue(self, state):
        """워크플로우 계속 진행 여부 결정"""
        return self.controller.should_continue(state)
    
    def should_exit(self, state):
        """워크플로우 종료 여부 결정"""
        return self.controller.should_exit(state)
