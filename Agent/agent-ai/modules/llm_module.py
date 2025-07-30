import os
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage
from dotenv import load_dotenv

load_dotenv()

class LLMModule:
    def __init__(self, provider: str):
        if provider == 'openai':
            if not os.getenv("OPENAI_API_KEY"):
                raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
            self.llm = ChatOpenAI()
        elif provider == 'gemini':
            if not os.getenv("GOOGLE_API_KEY"):
                raise ValueError("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
            self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
        else:
            raise ValueError(f"지원하지 않는 제공자입니다: {provider}. 'openai' 또는 'gemini'를 선택해주세요.")

    def process(self, query: str) -> str:

        response: BaseMessage = self.llm.invoke(query)
        return response.content
