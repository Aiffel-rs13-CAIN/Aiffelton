import os
import asyncio
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message

from .a2a_client import A2AClientAgent
from typing import Optional
a2a_client : Optional[A2AClientAgent] = None 


async def send_to_recoder():

    if a2a_client is None:
        raise RuntimeError("A2AClientAgent is not initialized.")


    agent_name = "Recorder Agent"
    if agent_name not in a2a_client.remote_agent_connections:
        print(f"❌ 에이전트 '{agent_name}' 을 찾을 수 없습니다.")
        return

    user_text = "A2A Client Test Message to Recoder Agent "
    response = await a2a_client.send_message(agent_name, None, None, user_text)
    print("Response:")
    if response : 
        for i, item in enumerate(response):
            print(f"  Part {i + 1}:")
            print(item)
    else : 
        print("⚠️ 응답이 없습니다 (response is None).")


class A2AServerAgentExecutor(AgentExecutor):

    def __init__(self):
        # initiaize 
        print()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:

        rcvRequest = context._params
        print("Request :", rcvRequest.model_dump(mode='json', exclude_none=False))
        print()
        # 1. get user input message 
        text = context.get_user_input()
        task = context.current_task
        print("Text :", text)

        # 2. 
        # TODO : langgraph 에게 메시지 전송 
        # TODO : task state 관리 

        # TEST {
        await send_to_recoder()
        #asyncio.create_task(send_to_recoder())  # ✅ 백그라운드 실행
        # TEST }


        # 3. 응답 전송
        response_text = "test response"
        await event_queue.enqueue_event(new_agent_text_message(response_text))
    
    async def send_to_other() -> None:
        print()


    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise Exception('cancel not supported')