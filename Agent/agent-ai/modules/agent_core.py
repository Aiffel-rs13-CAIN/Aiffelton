# agentic-ai/modules/agent_core.py
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
# from langchain.memory import RedisChatMessageHistory # (추후 구현)
# from .tools.rag_module import create_rag_tool # (추후 구현)
from dotenv import load_dotenv

load_dotenv()

class AgentCore:
    def __init__(self, config):
        self.config = config
        self.llm = self._initialize_llm()
        self.tools = self._initialize_tools()
        self.memory = self._initialize_memory()

    def _initialize_llm(self):
        llm_config = self.config.get('llm', {})
        provider = llm_config.get('provider', 'google')
        model = llm_config.get('model', 'gemini-2.5-flash')
        temperature = llm_config.get('temperature', 0.7)

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

    def _initialize_tools(self):
        tools_config = self.config.get('tools', [])
        initialized_tools = []
        for tool_conf in tools_config:
            if tool_conf.get('tool') == 'rag_tool':
                # TODO: RAG 도구 생성 로직 구현
                # rag_tool = create_rag_tool(self.config)
                # initialized_tools.append(rag_tool)
                print("알림: RAG 도구는 아직 구현되지 않았습니다.")
                pass
        return initialized_tools

    def _initialize_memory(self):
        memory_config = self.config.get('memory', {})
        mem_type = memory_config.get('type', 'in_memory')

        if mem_type == 'redis':
            # TODO: Redis 메모리 연결 로직 구현
            # host = memory_config.get('host', 'localhost')
            # port = memory_config.get('port', 6379)
            # session_id = memory_config.get('session_id', 'default')
            # return RedisChatMessageHistory(session_id=session_id, url=f"redis://{host}:{port}/0")
            print("알림: Redis 메모리는 아직 구현되지 않았습니다.")
            return None
        else:
            # 기본값은 인메모리 (별도 설정 없음)
            return None

    def get_llm(self):
        return self.llm

    def get_tools(self):
        return self.tools

    def get_memory(self):
        return self.memory
