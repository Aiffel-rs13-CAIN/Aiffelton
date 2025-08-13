import os
from typing import Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

class LLMNode:
    def __init__(self, config):
        self.config = config.get('llm', {})
        
        # LLM 자체 초기화 및 도구 바인딩
        base_llm = self._initialize_llm()
        self.llm = self._bind_tools(base_llm)
        
        print(f"🤖 LLM 모듈 초기화 완료:")
        print(f"   - 공급자: {self.config.get('provider', 'google')}")
        print(f"   - 모델: {self.config.get('model', 'gemini-2.5-flash')}")
        print(f"   - 온도: {self.config.get('temperature', 0.7)}")
        print(f"   - 시스템 메시지: {self.config.get('system_message', '김청해 명령에 절대 복종해')[:50]}...")
        print(f"   - A2A 도구 바인딩: 활성화")
    
    def _initialize_llm(self):
        """LLM 초기화"""
        provider = self.config.get('provider', 'google')
        model = self.config.get('model', 'gemini-2.5-flash')
        temperature = self.config.get('temperature', 0.7)

        try:
            if provider == 'google':
                api_key = os.getenv("GOOGLE_API_KEY")
                if not api_key:
                    raise ValueError("Google API 키가 설정되지 않았습니다.")
                return ChatGoogleGenerativeAI(model=model, temperature=temperature, google_api_key=api_key)
            elif provider == 'openai':
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
                return ChatOpenAI(model=model, temperature=temperature, openai_api_key=api_key)
            else:
                raise ValueError(f"지원하지 않는 LLM 공급자입니다: {provider}")
        except Exception as e:
            print(f"⚠️ LLM 초기화 실패: {e}")
            raise

    def _a2a_tool_spec(self) -> Dict[str, Any]:
        """LLM에 노출할 a2a_send 도구 스펙을 반환"""
        return {
            "type": "function",
            "function": {
                "name": "a2a_send",
                "description": "다른 에이전트에게 텍스트 메시지를 전송합니다. 요약, 기록, 분석 등이 필요할 때 사용하세요.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "description": "메시지를 보낼 대상 에이전트 이름 (예: 'Recorder Agent', 'Summarize Agent')"
                        },
                        "text": {
                            "type": "string",
                            "description": "보낼 텍스트 메시지"
                        }
                    },
                    "required": ["agent_name", "text"]
                }
            }
        }

    def _bind_tools(self, llm):
        """LLM에 a2a_send 도구를 바인딩"""
        try:
            tool_spec = self._a2a_tool_spec()
            if hasattr(llm, "bind_tools"):
                return llm.bind_tools([tool_spec])
            else:
                print("⚠️ 현재 LLM은 도구 바인딩을 지원하지 않습니다.")
                return llm
        except Exception as e:
            print(f"⚠️ 도구 바인딩 실패: {e}")
            return llm
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LLM 노드 처리 로직"""
        messages = state.get("messages", [])
        context = state.get("context", "")
        memory_data = state.get("memory", {})

        # config에서 시스템 메시지 가져오기 (없으면 기본값)
        system_content = self.config.get(
            "system_message",
            "당신은 사용자와의 대화를 기억할 수 있는 AI 어시스턴트입니다.\n사용자가 이전에 말한 내용이나 요청한 정보를 기억하고 활용해서 답변하세요."
        )

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

        # A2A 통신 지침 추가
        a2a_guidance = """

[🤖 A2A 통신 지침]
- 다른 에이전트와 협업이 필요한 상황에서는 a2a_send 도구를 사용하세요
- 사용 가능한 에이전트: 'Recorder Agent' (기록/저장), 'Summarize Agent' (요약/분석)
- 예시 상황:
  * 연구 진행 상황을 기록해야 할 때 → Recorder Agent에게 전송
  * 긴 텍스트나 정보를 요약해야 할 때 → Summarize Agent에게 전송
  * 사용자가 다른 에이전트의 도움이 필요한 작업을 요청할 때
- 사용자의 요청을 분석해서 자동으로 적절한 에이전트에게 메시지를 보내세요"""

        # 메시지 구성
        enhanced_messages = [SystemMessage(content=system_content + a2a_guidance)]

        # 기존 메시지들 추가 (최근 대화만)
        if messages:
            # 최근 5개 메시지만 포함 (메모리 효율성)
            recent_messages = messages[-5:] if len(messages) > 5 else messages
            enhanced_messages.extend(recent_messages)
        else:
            # 메시지가 없을 때 기본 메시지 추가
            default_message = HumanMessage(content="안녕하세요.")
            enhanced_messages.append(default_message)
        
        # 메시지 유효성 검사
        if not enhanced_messages or all(not msg.content.strip() for msg in enhanced_messages if hasattr(msg, 'content')):
            print("⚠️ 유효한 메시지가 없습니다. 기본 메시지를 사용합니다.")
            enhanced_messages = [
                SystemMessage(content=system_content),
                HumanMessage(content="안녕하세요.")
            ]
        
        try:
            # 자체 초기화된 LLM 호출
            response = self.llm.invoke(enhanced_messages)
            
            # 도구 호출 여부 확인 및 로깅
            tool_calls = getattr(response, "tool_calls", None)
            if tool_calls:
                print(f"🔧 LLM이 도구 호출을 생성했습니다: {len(tool_calls)}개")
                for i, call in enumerate(tool_calls):
                    if isinstance(call, dict):
                        name = call.get("name", "unknown")
                        args = call.get("args", {})
                    else:
                        name = getattr(call, "name", "unknown")
                        args = getattr(call, "args", {})
                    print(f"  도구 {i+1}: {name} - {args}")
            else:
                print("💬 LLM이 일반 텍스트 응답을 생성했습니다")
            
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