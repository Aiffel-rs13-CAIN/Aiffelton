import os
import asyncio
from openai import OpenAI
from dotenv import load_dotenv
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message


import httpx
from typing import Any
from uuid import uuid4
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageRequest,
)

from a2a_core.a2a_client import fetch_agent_card

load_dotenv()  # summarizer/.env 로부터 로드

class SummarizerAgent:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("❌ OPENAI_API_KEY가 .env 파일에 없습니다.")
        self.client = OpenAI(api_key=api_key)

    async def summarize(self, text):
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "너는 요약 전문가야. 사용자의 긴 글을 읽고, 그 핵심 내용을 한두 문장으로 요약해줘. 공감, 조언, 의견은 절대 넣지 마. 오직 핵심 내용만 간결하게 뽑아내."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content.strip()


class SummarizerAgentExecutor(AgentExecutor):
    """Test AgentProxy Implementation."""

    def __init__(self, recoder_url: str):
        self.agent = SummarizerAgent()
        self.recoder_url = recoder_url
        self.recoder_client = None
        self.httpx_client = httpx.AsyncClient(timeout=httpx.Timeout(15.0)) # 예: 5초

        print("recoder_url :", recoder_url)

    async def setup(self) : 
        
        #self.recoder_client = await A2AClient.get_client_from_agent_card_url(
        #    httpx.AsyncClient(), self.recoder_url
        #)
        

        card_resolver = A2ACardResolver(self.httpx_client, self.recoder_url)
        card = await card_resolver.get_agent_card()

        # 접속 확인: .well-known/agent.json 요청
        try:
            response = await self.httpx_client.get(f"{self.recoder_url}.well-known/agent.json")
            print("✅ agent.json 응답 상태:", response.status_code)
            print("✅ agent.json 내용:", response.json())
        except Exception as e:
            print("❌ recoder 접속 실패:", e)

     
        self.recoder_client = A2AClient( httpx_client=self.httpx_client, 
                                         url=self.recoder_url )
        #card = fetch_agent_card(httpx_client,self.recoder_url ) 
        
        print(type(self.recoder_client))
        print("setup recoder client :", self.recoder_client)
    
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        
        # method가 "message/send"인지  "message/stream"인지 RequestContext로는 알수가 없네..
        request = context._params
        print("Request :", request.model_dump(mode='json', exclude_none=False))
        print()
        # 1. get user input message 
        query = context.get_user_input()
        task = context.current_task
        print("Text :", query)

        # 2. 
        #summary = await self.agent.summarize( query )
        summary = "'희봉님께서는 초대를  받아 휘의록 관리를 위해 이메일 주소가 필요하다 고 합니다. 내일 상세히 설명해줄 계획이라고 합니다.'"
        print("Summary :", summary)
        #await event_queue.enqueue_event(new_agent_text_message(summary))

        # 3. recoder에게 전송 
        user_text = f'put, user_input : {query}, summary : {summary}'

        send_message_payload: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [
                    {'kind': 'text', 'text': user_text}
                ],
                'messageId': uuid4().hex,
            },
        }
        request = SendMessageRequest(
            id=str(uuid4()), params=MessageSendParams(**send_message_payload)
        )
        print("Send Request :", request.model_dump(mode='json', exclude_none=True))


        try : 
            response = await self.recoder_client.send_message(request)
            
            #streaming_request = self.recoder_client.send_message_streaming(
            #    SendStreamingMessageRequest(id=str(uuid4()), params=MessageSendParams(**send_message_payload))
            #)
            #async for chunk in streaming_request:
            #    print(chunk.model_dump(mode='json', exclude_none=True))

            print("Received Response :", response.model_dump(mode='json', exclude_none=True))
        except asyncio.CancelledError as e:
            print("⚠️ send_message 취소됨:", e)
            # 필요 시 복구 로직 또는 재시도
        except Exception as e:
            print("❌ send_message 실패:", e)
        

        # 4. 결과 전송송
        await event_queue.enqueue_event(new_agent_text_message(summary))

    
    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise Exception('cancel not supported')

    