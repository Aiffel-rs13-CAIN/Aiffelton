import os
from typing import Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

class LLMNode:
    def __init__(self, config, tools):
        self.config = config.get('llm', {})
        self.tools = tools
        
        # LLM 자체 초기화
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
        """LLM에 모든 도구를 바인딩 (A2A + 기존 도구)"""
        try:
            tools_to_bind = []
            
            # A2A 도구 추가
            tools_to_bind.append(self._a2a_tool_spec())
            
            # 기존 도구들 추가
            if self.tools:
                tools_to_bind.extend(self.tools)
            
            if hasattr(llm, "bind_tools") and tools_to_bind:
                return llm.bind_tools(tools_to_bind)
            else:
                if not tools_to_bind:
                    print("⚠️ 바인딩할 도구가 없습니다.")
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

        # 메시지 구성 (시스템 메시지는 config에서 가져옴)
        enhanced_messages = [SystemMessage(content=system_content)]

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

    async def post_process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """도구 실행 결과를 자연스러운 언어로 후처리하고, 대화 기록을 관리합니다."""
        messages = state.get("messages", [])
        
        user_question = ""
        tool_results_content = []
        last_human_message_index = -1

        for i, msg in enumerate(messages):
            if isinstance(msg, HumanMessage):
                user_question = msg.content
                last_human_message_index = i
            elif hasattr(msg, 'tool_call_id'):
                tool_results_content.append(str(msg.content))
        
        if not tool_results_content:
            return state

        prompt = f"""Based on the following user question and the data received from a tool, provide a final, comprehensive, and user-friendly answer in Korean.
        Original Question: {user_question}
        Tool-provided Data: {', '.join(tool_results_content)}
        Final Answer:"""
        
        final_response = await self.llm.ainvoke(prompt)

        # 마지막 사용자 질문까지의 기록을 유지하고, 그 뒤에 최종 답변을 추가합니다.
        # 이렇게 하면 tool_call, ToolMessage 같은 중간 과정이 정리됩니다.
        if last_human_message_index != -1:
            final_messages = messages[:last_human_message_index + 1] + [final_response]
        else: # 예외적인 경우
            final_messages = messages + [final_response]

        return {"messages": final_messages, "last_response": final_response.content}