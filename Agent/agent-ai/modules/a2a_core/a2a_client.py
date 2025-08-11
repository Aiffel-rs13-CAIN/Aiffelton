import httpx
import asyncio
import os
import base64
import json
import uuid


from uuid import uuid4
from typing import Any
from typing import Optional
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    JSONRPCErrorResponse,
    Message,
    MessageSendParams,
    MessageSendConfiguration,
    SendMessageRequest,
    SendStreamingMessageRequest,
    Task,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
    DataPart,
    Part,
    TextPart,
)
from collections.abc import Callable

PUBLIC_AGENT_CARD_PATH = '/.well-known/agent.json'
EXTENDED_AGENT_CARD_PATH = '/agent/authenticatedExtendedCard'

TaskCallbackArg = Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent
TaskUpdateCallback = Callable[[TaskCallbackArg, AgentCard], Task]



from pydantic import BaseModel, HttpUrl
class A2AServerEntry(BaseModel):
    """A class to hold the information to the remote agents. """
    name: str
    url: HttpUrl

class RemoteAgentConnections:
    """A class to hold the connections to the remote agents."""

    def __init__(self, client: httpx.AsyncClient, agent_card: AgentCard):
        self.agent_client = A2AClient(client, agent_card)
        self.card = agent_card
        self.pending_tasks = set()
        print('A2AClient initialized : ', agent_card)

    def get_agent(self) -> AgentCard:
        return self.card

    async def send_message(
        self,
        request: MessageSendParams,
        task_callback: TaskUpdateCallback | None,
    ) -> Task | Message | None:
        if self.card.capabilities.streaming:
            task = None
            print("send_message : streaming")
            async for response in self.agent_client.send_message_streaming(
                SendStreamingMessageRequest(id=str(uuid4()), params=request)
            ):
                if not response.root.result:
                    return response.root.error
                # In the case a message is returned, that is the end of the interaction.
                event = response.root.result
                if isinstance(event, Message):
                    return event

                # Otherwise we are in the Task + TaskUpdate cycle.
                if task_callback and event:
                    task = task_callback(event, self.card)
                if hasattr(event, 'final') and event.final:
                    break
            return task
        
        print("send_message : Non-streaming")
        # Non-streaming
        response = await self.agent_client.send_message(
            SendMessageRequest(id=str(uuid4()), params=request)
        )
        if isinstance(response.root, JSONRPCErrorResponse):
            return response.root.error
        if isinstance(response.root.result, Message):
            return response.root.result

        if task_callback:
            task_callback(response.root.result, self.card)
        return response.root.result



class A2AClientAgent:
    """The client agent.

    This is the agent responsible for choosing which remote agents to send
    tasks to and coordinate their work.
    """
 
    def __init__(
        self,
        remote_agent_entries: list[A2AServerEntry],
        http_client: httpx.AsyncClient | None = None,
        task_callback: TaskUpdateCallback | None = None,
        auto_init: bool = True,
    ):
        self.task_callback = task_callback
        self.httpx_client = http_client or httpx.AsyncClient()
        self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
        self.cards: dict[str, AgentCard] = {}
        self.agents: str = ''
        self.remote_agent_entries = remote_agent_entries
        
        if auto_init : 
            loop = asyncio.get_running_loop()
            loop.create_task(
                self.init_remote_agents(self.remote_agent_entries)
            )
            #loop.create_task(
            #   self.reconnect_loop()
            #)  # 🔁 재시도 루프


    async def init_remote_agents(
        self, entries: list[A2AServerEntry]
    ):
        async with asyncio.TaskGroup() as task_group:
            for entry in entries:
                task_group.create_task(self.retrieve_card(entry))
        # The task groups run in the background and complete.
        # Once completed the self.agents string is set and the remote
        # connections are established


    async def retrieve_card(self, entry: A2AServerEntry):
        address = str(entry.url)
        card_resolver = A2ACardResolver(self.httpx_client, address)
        card = await card_resolver.get_agent_card()
        self.register_agent_card(card)


    def register_agent_card(self, card: AgentCard):
        remote_connection = RemoteAgentConnections(self.httpx_client, card)
        self.remote_agent_connections[card.name] = remote_connection
        self.cards[card.name] = card
        agent_info = []
        for ra in self.list_remote_agents():
            agent_info.append(json.dumps(ra))
        self.agents = '\n'.join(agent_info)

    async def retrieve_card_by_name(self, name: str):
        """
        remote_agent_entries 목록에서 name으로 A2AServerEntry를 찾아
        해당 entry에 대해 retrieve_card() 실행.
        """
        # self.remote_agent_entries가 존재하는지 확인
        if not self.remote_agent_entries:
            raise ValueError("⚠️ remote_agent_entries가 초기화되지 않았습니다.")

        # name으로 entry 찾기
        entry = next((e for e in self.remote_agent_entries if e.name == name), None)
        if entry is None:
            raise ValueError(f"❌ 이름이 '{name}'인 A2A 서버 엔트리를 찾을 수 없습니다.")

        # retrieve_card 실행
        await self.retrieve_card(entry)

    def list_remote_agents(self):
        """List the available remote agents you can use to delegate the task."""
        if not self.remote_agent_connections:
            return []

        remote_agent_info = []
        for card in self.cards.values():
            remote_agent_info.append(
                {'name': card.name, 'description': card.description}
            )
        return remote_agent_info



    async def send_message(self, agent_name:str, user_text: str, 
                            task_id:Optional[str] = None, context_id:Optional[str] = None ) -> Any:
        """Sends a task either streaming (if supported) or non-streaming.

        This will send a message to the remote agent named agent_name.

        Args:
          agent_name: The name of the agent to send the task to.
          message: The message to send to the agent for the task.
          tool_context: The tool context this method runs in.

        Yields:
          A dictionary of JSON data.
        """
        
        # server list에서 agent_name을 찾는다. 
        if agent_name not in self.remote_agent_connections:
            raise ValueError(f'Agent {agent_name} not found')
        
        client = self.remote_agent_connections[agent_name]
        if not client:
            raise ValueError(f'Client not available for {agent_name}')


        # setting request message
        #if not task_id:
        #    task_id = str(uuid.uuid4())
                        
        #if not context_id:
        #    context_id = str(uuid.uuid4())
        #print(f"task_id={task_id}, context_id={context_id}")
       
        #message_id = str(uuid.uuid4())

        print(f"TextPart: {TextPart(text=user_text)}")
        request: MessageSendParams = MessageSendParams(
            id=str(uuid.uuid4()),
            message=Message(
                role='user',
                parts=[TextPart(text=user_text)],
                message_id=str(uuid.uuid4()),
                #**{"messageId": message_id},   # alias 이름으로 명시적 전달
                context_id=context_id,
                task_id=task_id
            ),
            configuration=MessageSendConfiguration(
                accepted_output_modes=['text', 'text/plain', 'image/png'],
            ),
        )

        # message 전송 및 응답 수신
        response = await client.send_message(request, task_callback=None)
        print("Response :", response.model_dump(mode='json', exclude_none=True))

        if isinstance(response, Message):
            #message_id = response.messageId
            message_id = response.message_id
            print(f"Message ID: {message_id}")
            return await self.convert_parts(response.parts)
        elif isinstance(response, Task):
            task: Task = response
            # TODO : task state 관리 

            # Task Message or Artifacts 
            result = []
            if task.status.message:
                # Assume the information is in the task message.
                result.extend(
                    await self.convert_parts(task.status.message.parts)
                )
            if task.artifacts:
                for artifact in task.artifacts:
                    result.extend(
                        await self.convert_parts(artifact.parts)
                    )
            return result

        
    async def convert_parts(self, parts: list[Part]):
        rval = []
        for p in parts:
            rval.append(await self.convert_part(p))
        return rval


    async def convert_part(self, part: Part):
        if part.root.kind == 'text':
            return part.root.text
        if part.root.kind == 'data':
            return part.root.data
        if part.root.kind == 'file':
            # Repackage A2A FilePart to google.genai Blob
            # Currently not considering plain text as files
            file_id = part.root.file.name
            file_bytes = base64.b64decode(part.root.file.bytes)
            file_part = types.Part(
                inline_data=types.Blob(
                    mime_type=part.root.file.mime_type, data=file_bytes
                )
            )
            
            return DataPart(data={'artifact-file-id': file_id})

        return f'Unknown type: {part.kind}'

    async def close(self):
        await self.httpx_client.aclose()



async def fetch_agent_card(httpx_client:httpx.AsyncClient, url: str):
    async with httpx_client:
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=url)
        try:
            card = await resolver.get_agent_card()
            print('Successfully fetched public agent card:')
            print(card.model_dump_json(indent=2, exclude_none=True))
            return card
        except Exception as e:
            print(f"Failed to fetch agent card from {url}: {e}")
            return None

async def select_agent_by_capability(agent_urls, required_capability):
    for url in agent_urls:
        card = await fetch_agent_card(url)
        if card and required_capability in card.capabilities.tags:
            print(f"Selected agent {card.name} at {url} with capability {required_capability}")
            return url
    print("No agent found with required capability")
    return None



# global 
a2a_client : Optional[A2AClientAgent] = None 