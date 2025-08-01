import os
import asyncio
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message



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



        # 3. 응답 전송
        response_text = "test response"
        await event_queue.enqueue_event(new_agent_text_message(response_text))
    
    async def send_to_other() -> None:
        print()


    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise Exception('cancel not supported')