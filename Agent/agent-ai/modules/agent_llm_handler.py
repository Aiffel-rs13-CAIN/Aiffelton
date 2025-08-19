"""
Agent-specific LLM Handler
각 에이전트가 독립적인 LLM과 설정을 가질 수 있도록 하는 클래스
"""
import os
import yaml
import re
from typing import Dict, Any, Optional
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

class AgentLLMHandler:
    def __init__(self, agent_name: str, config_path: Optional[str] = None):
        self.agent_name = agent_name
        self.config = self._load_agent_config(config_path)
        self.llm = self._initialize_llm()
        
        print(f"🤖 {agent_name} LLM 핸들러 초기화 완료:")
        print(f"   - 모델: {self.config.get('llm', {}).get('model', 'gemini-2.5-flash')}")
        print(f"   - 온도: {self.config.get('llm', {}).get('temperature', 0.7)}")
    
    def _load_agent_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """에이전트별 설정 파일 로드"""
        if config_path is None:
            # 기본 경로: config/agents/{agent_name}_config.yaml
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            agent_filename = self.agent_name.lower().replace(' ', '_').replace('-', '_')
            config_path = os.path.join(base_dir, "config", "agents", f"{agent_filename}_config.yaml")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loader = yaml.SafeLoader
                loader.add_implicit_resolver(
                    u'tag:yaml.org,2002:env_var',
                    re.compile(r'\$\{(.*)\}'),
                    None
                )
                def constructor_env_var(loader, node):
                    value = loader.construct_scalar(node)
                    key = value.replace('${', '').replace('}', '')
                    return os.getenv(key)
                loader.add_constructor(u'tag:yaml.org,2002:env_var', constructor_env_var)
                return yaml.load(f, Loader=loader)
        except FileNotFoundError:
            print(f"⚠️ {self.agent_name} 설정 파일을 찾을 수 없습니다: {config_path}")
            return self._get_default_config()
        except Exception as e:
            print(f"⚠️ {self.agent_name} 설정 파일 로드 실패: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """기본 설정 반환"""
        return {
            "llm": {
                "provider": "google",
                "model": "gemini-2.5-flash",
                "temperature": 0.7,
                "system_message": f"당신은 {self.agent_name}입니다. 사용자의 요청에 도움이 되도록 응답해주세요."
            }
        }
    
    def _initialize_llm(self):
        """LLM 초기화"""
        llm_config = self.config.get('llm', {})
        provider = llm_config.get('provider', 'google')
        model = llm_config.get('model', 'gemini-2.5-flash')
        temperature = llm_config.get('temperature', 0.7)
        
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
            print(f"⚠️ {self.agent_name} LLM 초기화 실패: {e}")
            raise
    
    async def process_message(self, user_message: str, context: Optional[str] = None) -> str:
        """사용자 메시지를 처리하고 LLM 응답 생성"""
        try:
            # 시스템 메시지 구성
            llm_config = self.config.get('llm', {})
            system_content = llm_config.get('system_message', f"당신은 {self.agent_name}입니다.")
            
            # 컨텍스트가 있으면 추가
            if context:
                system_content += f"\n\n[컨텍스트]\n{context}"
            
            # 메시지 구성
            messages = [
                SystemMessage(content=system_content),
                HumanMessage(content=user_message)
            ]
            
            # LLM 호출
            response = self.llm.invoke(messages)
            
            # 응답 내용 추출
            if hasattr(response, 'content'):
                return response.content
            else:
                return str(response)
                
        except Exception as e:
            print(f"❌ {self.agent_name} 메시지 처리 오류: {e}")
            return f"죄송합니다. {self.agent_name}에서 오류가 발생했습니다: {str(e)}"
    
    def get_agent_info(self) -> Dict[str, Any]:
        """에이전트 정보 반환"""
        agent_config = self.config.get('agent', {})
        return {
            'name': agent_config.get('name', self.agent_name),
            'description': agent_config.get('description', ''),
            'model': self.config.get('llm', {}).get('model', 'gemini-2.5-flash'),
            'provider': self.config.get('llm', {}).get('provider', 'google')
        }


# 전역 에이전트 LLM 핸들러 캐시
_agent_handlers: Dict[str, AgentLLMHandler] = {}

def get_agent_llm_handler(agent_name: str) -> AgentLLMHandler:
    """에이전트별 LLM 핸들러 반환 (싱글톤 패턴)"""
    if agent_name not in _agent_handlers:
        _agent_handlers[agent_name] = AgentLLMHandler(agent_name)
    return _agent_handlers[agent_name]
