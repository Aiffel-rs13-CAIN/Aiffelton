
import httpx
import uuid

from typing import Any
from uuid import uuid4

import sys
import os
# 상위 디렉토리 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from modules.a2a_core.a2a_client import A2AClientAgent
from modules.a2a_core.config_loader import get_server_list


 

async def main() -> None:

    # 1. 설정 디렉터리에서 모든 A2A 서버 주소 로드
    config_dir ="../config/a2a"
    a2a_server_entries = get_server_list(config_dir)
   

    # 2. A2A Client Agent 
    async with httpx.AsyncClient() as httpx_client:
        # 2. A2A Client Agent 초기화
        a2a_client = A2AClientAgent(a2a_server_entries, httpx_client, None )
        
        # 서버 초기화 완료 대기 
        await asyncio.sleep(1)  # init_remote_agent_addresses가 loop.create_task로 동작하므로 잠시 대기
        
        # 3. 사용 가능한 에이전트 목록 출력
        print("\n📡 등록된 에이전트 목록:")
        for info in a2a_client.list_remote_agents():
            print("  -", info["name"], ":", info["description"])


       

        # 4. sumarizer에 메시지 전송
        agent_name = "Summarize Agent"
        if agent_name not in a2a_client.remote_agent_connections:
            print(f"❌ 에이전트 '{agent_name}' 을 찾을 수 없습니다.")
            return



        user_text = "A2A Client Test Message"
   
        response = await a2a_client.send_message(agent_name, user_text, task_id=None, context_id=None)
        #response = await a2a_client.send_message(agent_name, user_text)
        if response : 
            for i, item in enumerate(response):
                print(f"  Part {i + 1}:")
                print(item)
        else : 
            print("⚠️ 응답이 없습니다 (response is None).")

        
      


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())

