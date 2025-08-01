import uvicorn
import asyncio
import nest_asyncio  # 중첩 루프 허용
import httpx
import uuid
import os
import sys

from typing import Any
from uuid import uuid4

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageRequest,
)

from modules.a2a_core.server_factory import build_server_from_config
from modules.a2a_core.a2a_client import A2AClientAgent
from modules.a2a_core.config_loader import load_a2a_server_addresses_from_config_dir
#from modules.a2a_core.server_executor import a2a_client as global_client_agent
import modules.a2a_core.server_executor as server_executor



def get_server_list(config_path):
    
    # 1. 설정 디렉터리에서 나를 제외한 모든 A2A 서버 주소 로드
    config_dir ="config/a2a"
    my_file = os.path.basename(config_path) 

    a2a_server_entries = load_a2a_server_addresses_from_config_dir(config_dir, my_file)
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

  
    return a2a_server_addresses


async def server_agent(config_path: str):
    
    server_config, app = build_server_from_config(config_path)
    
    host = server_config["host"]
    port = server_config["port"]
    name = server_config["name"]
    config = uvicorn.Config(app=app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    print(f"✅ {name} A2A Server is running at http://{host}:{port}/")
    await server.serve()


async def main(config_path: str):
    """Starts the Test Agent with A2A protocol."""

    # A2A 서버 목록 가져오기
    a2a_server_addresses = get_server_list(config_path)
   
    # A2A 클라이언트 에이전트 생성
    client =  A2AClientAgent(a2a_server_addresses, auto_init = True)
    server_executor.a2a_client = client  # 전역 변수에 저장

    # 클라이언트 에이전트 초기화 (비동기)
    #await client.init_remote_agent_addresses(a2a_server_addresses)

    # 서버 에이전트 실행 (비동기)
    await server_agent(config_path)





if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_config.json>")
        sys.exit(1)

    config_path = sys.argv[1]
    asyncio.run(main(config_path))
    