import os
import asyncio
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message

from .a2a_client import A2AClientAgent
from .a2a_client import A2AServerEntry
from typing import Optional
a2a_client : Optional[A2AClientAgent] = None 


class A2AServerAgentExecutor(AgentExecutor):

    def __init__(self, remote_agent_entries: list[A2AServerEntry]):
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
        if a2a_client : 
            agent_name = "Recorder Agent"
            user_text = "A2A Client Test Message to Recoder Agent "
            await self.send_to_other(agent_name, user_text)
        #asyncio.create_task(send_to_recoder())  # ✅ 백그라운드 실행
        # TEST }


        # 3. 응답 전송
        response_text = "test response"
        await event_queue.enqueue_event(new_agent_text_message(response_text))
    
    async def send_to_other(agent_name:str, user_text:str) -> None:
        if a2a_client is None:
            raise RuntimeError("A2AClientAgent is not initialized.")

        if agent_name not in a2a_client.remote_agent_connections:
            print(f"❌ 에이전트 '{agent_name}' 을 찾을 수 없습니다.")
            return

    
        response = await a2a_client.send_message(agent_name, None, None, user_text)
        print("Response:")
        if response : 
            for i, item in enumerate(response):
                print(f"  Part {i + 1}:")
                print(item)
        else : 
            print("⚠️ 응답이 없습니다 (response is None).")
            print()


    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise Exception('cancel not supported')


class A2ACombinedAgentExecutor(AgentExecutor):

    def __init__(self,
        remote_agent_entries: list[A2AServerEntry]):

        self.client_agent = A2AClientAgent(remote_agent_entries)
        
        
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
        if self.client_agent : 
            agent_name = "Recorder Agent"
            user_text = "A2A Client Test Message to Recoder Agent "
            await self.send_to_other(agent_name, user_text)
      

        response_text = "test response"
        # TEST }


        # 3. 응답 전송
        await event_queue.enqueue_event(new_agent_text_message(response_text))
    
    async def send_to_other(self, agent_name:str, user_text:str) -> None:
        
        if agent_name not in self.client_agent.remote_agent_connections:
            print(f"❌ 에이전트 '{agent_name}' 을 찾을 수 없습니다.")
            
            # TODO : remote_server_enties에서 agent_name을 찾아서, 연결한다. 
            #
            return

           
        response = await self.client_agent.send_message(agent_name, None, None, user_text)
        print("Response:")
        if response : 
            for i, item in enumerate(response):
                print(f"  Part {i + 1}:")
                print(item)
        else : 
            print("⚠️ 응답이 없습니다 (response is None).")
            print()


    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise Exception('cancel not supported')