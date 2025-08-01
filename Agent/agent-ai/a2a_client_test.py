
import httpx
import uuid

from typing import Any
from uuid import uuid4

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageRequest,
)
from modules.a2a_core.a2a_client import A2AClientAgent
from modules.a2a_core.config_loader import load_a2a_server_addresses_from_config_dir


 

async def main() -> None:

    # 1. 설정 디렉터리에서 모든 A2A 서버 주소 로드
    config_dir ="config/a2a"
    a2a_server_entries = load_a2a_server_addresses_from_config_dir(config_dir)
    if not a2a_server_entries:
        print("❌ A2A 서버 주소가 없습니다.")
        return

    print("✅ 서버 목록:")
    a2a_server_addresses = []
    for entry in a2a_server_entries:
        url = entry["url"]
        name = entry["name"]
        a2a_server_addresses.append(url)
        print(f"A2A Server {name} : {url}")

    
    async with httpx.AsyncClient() as httpx_client:
        # 2. A2A Client Agent 초기화
        a2a_client = A2AClientAgent(a2a_server_addresses, httpx_client, None )
        
        # 서버 초기화 완료 대기 
        await asyncio.sleep(1)  # init_remote_agent_addresses가 loop.create_task로 동작하므로 잠시 대기
        
        # 3. 사용 가능한 에이전트 목록 출력
        print("\n📡 등록된 에이전트 목록:")
        for info in a2a_client.list_remote_agents():
            print("  -", info["name"], ":", info["description"])


        # new task 
        task_id = str(uuid.uuid4())
        context_id = str(uuid.uuid4())

        # 4. sumarizer에 메시지 전송
        agent_name = "Summarize Agent"
        if agent_name not in a2a_client.remote_agent_connections:
            print(f"❌ 에이전트 '{agent_name}' 을 찾을 수 없습니다.")
            return

        user_text = "A2A Client Test Message"
        response = await a2a_client.send_message(agent_name, task_id, context_id, user_text)
        print("Response:")
        if response : 
            for i, item in enumerate(response):
                print(f"  Part {i + 1}:")
                print(item)
        else : 
            print("⚠️ 응답이 없습니다 (response is None).")

        
      


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())

