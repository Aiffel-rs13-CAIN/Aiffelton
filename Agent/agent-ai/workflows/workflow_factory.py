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
        self.mcp_tool_node = None # MCP 도구 노드 인스턴스 (늦은 초기화)

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

    # MCP 도구 노드 함수 - 메시지 시퀀스 안전하게 처리
    def mcp_tool_node_func(self, state):
        """MCP 도구 노드 함수 - 자율적 도구 사용 (메시지 시퀀스 안전)"""
        try:
            # 메시지가 없거나 이미 도구가 실행된 경우 스킵
            messages = list(state.get("messages", []))
            if not messages:
                return state

            # 마지막 메시지가 사용자 메시지인지 확인
            from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
            last_message = messages[-1] if messages else None

            # 사용자 메시지가 아니거나 이미 MCP 도구가 실행된 경우 스킵
            if not isinstance(last_message, HumanMessage):
                return state

            # 이미 도구 결과가 있는 경우 중복 실행 방지
            tool_results = state.get("tool_results", [])
            for result in tool_results:
                if result.get("tool") == "mcp_react_agent":
                    return state

            # 늦은 임포트로 순환 참조 방지
            if self.mcp_tool_node is None:
                from modules.tool_module import ToolNode as MCPToolNode
                # agent_core에서 config 추출
                config = getattr(self.agent_core, 'config', {})
                self.mcp_tool_node = MCPToolNode(config)

            # 상태를 딕셔너리로 변환하여 MCP 도구 실행
            state_dict = {
                "messages": messages,
                "context": state.get("context", ""),
                "memory": state.get("memory", {}),
                "tool_results": list(tool_results),
                "should_exit": state.get("should_exit", False),
                "user_id": state.get("user_id", "default_user"),
                "last_response": state.get("last_response", "")
            }

            # MCP 도구 처리
            result_state = self.mcp_tool_node.process(state_dict)

            # 결과 메시지들을 안전하게 필터링
            result_messages = result_state.get("messages", [])
            filtered_messages = []

            for msg in result_messages:
                # 메시지 타입 검증
                if isinstance(msg, (HumanMessage, AIMessage, ToolMessage)):
                    filtered_messages.append(msg)
                elif hasattr(msg, 'content'):  # 기타 메시지 객체
                    filtered_messages.append(msg)

            # 결과를 원래 상태 형식으로 반환
            return {
                "messages": filtered_messages,
                "context": result_state.get("context", ""),
                "memory": result_state.get("memory", {}),
                "tool_results": result_state.get("tool_results", []),
                "should_exit": result_state.get("should_exit", False),
                "user_id": result_state.get("user_id", "default_user"),
                "last_response": result_state.get("last_response", "")
            }

        except ImportError:
            # MCP 모듈이 없으면 상태 그대로 반환
            print("ℹ️  MCP 모듈을 찾을 수 없습니다.")
            return state
        except Exception as e:
            # 오류 발생해도 워크플로우 계속 진행
            print(f"⚠️  MCP 도구 실행 중 오류: {e}")
            return state

    def should_continue(self, state):
        """워크플로우 계속 진행 여부 결정"""
        return self.controller.should_continue(state)

    def should_exit(self, state):
        """종료 여부 결정"""
        return "exit" if state.get("should_exit", False) else "continue"