import uvicorn
import asyncio
import sys
import os

# 상위 디렉토리 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from modules.a2a_core.server_factory import build_server_from_config


async def main(config_path: str):
    """Starts the Test Agent with A2A protocol."""

    # A2A 클라이언트 에이전트 생성
    # config_dir ="config/a2a"
    # my_file = os.path.basename(config_path)
    # a2a_server_entries = get_server_list(config_dir, my_file)
    # client =  A2AClientAgent(a2a_server_entries, auto_init = True)
    # server_executor.a2a_client = client  # 전역 변수에 저장

    # Get My Own Server Config and Other Server List
    server_config, app = build_server_from_config(config_path)
    
    host = server_config["host"]
    port = server_config["port"]
    name = server_config["name"]
    config = uvicorn.Config(app=app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    print(f"✅ {name} A2A Server is running at http://{host}:{port}/")
    await server.serve()

    


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_config.json>")
        sys.exit(1)

    config_path = sys.argv[1]
    asyncio.run(main(config_path))
    