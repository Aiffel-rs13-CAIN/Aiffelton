import logging
import os
import sys

import uvicorn
import asyncio
import nest_asyncio  # 중첩 루프 허용


from modules.a2a_core.server_factory import build_server_from_config


async def server_agent(config_path: str):
    
    server_config, app = build_server_from_config(config_path)
    
    host = server_config["host"]
    port = server_config["port"]
    name = server_config["name"]
    config = uvicorn.Config(app=app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    print(f"✅ A2A Server {name} is running at http://{host}:{port}/")
    await server.serve()


def main(config_path: str):
    """Starts the Test Agent server with A2A protocol."""
    nest_asyncio.apply()  # 중첩 루프 허용
    asyncio.run(server_agent(config_path))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_config.json>")
        sys.exit(1)
    main(sys.argv[1])