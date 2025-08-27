# agent-ai/modules/mcp_module.py
import json
from pathlib import Path
from typing import List, Dict, Any

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools


def _to_mcp_client_config(cfg: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    mcp.json의 "mcpServers" 블록을 MultiServerMCPClient 형식으로 변환
    """
    out: Dict[str, Dict[str, Any]] = {}
    for name, s in cfg.get("mcpServers", {}).items():
        transport = s.get("transport", "stdio")
        if transport == "stdio":
            server_config = {
                "transport": "stdio",
                "command": s.get("command", "python"),
                "args": s.get("args", []),
                "env": s.get("env", {}),
            }
            if "cwd" in s:
                server_config["cwd"] = s["cwd"]
            out[name] = server_config
        elif transport == "streamable_http":
            out[name] = {
                "transport": "streamable_http",
                "url": s["url"],
                "headers": s.get("headers", {}),
            }
    return out

async def load_mcp_tools_from_config(mcp_config_path: str) -> List[Any]:
    """
    지정된 경로의 MCP 설정 파일을 읽어 모든 서버의 도구를 로드합니다.
    """
    base_path = Path(__file__).resolve().parents[1] # .../agent-ai
    config_file = Path(mcp_config_path)
    if not config_file.is_absolute():
        config_file = (base_path / config_file).resolve()

    if not config_file.exists():
        print(f"[MCP Module] Warning: MCP config file not found at {config_file}")
        return []

    with open(config_file, "r", encoding="utf-8") as f:
        mcp_config = json.load(f)

    client_config = _to_mcp_client_config(mcp_config)
    if not client_config:
        print("[MCP Module] Warning: No valid MCP servers found in config.")
        return []

    client = MultiServerMCPClient(client_config)
    # client.get_tools()는 모든 서버에 연결하여 도구를 수집하는 상위 레벨 함수입니다.
    print(f"[MCP Module] Fetching tools from all configured MCP servers...")
    all_tools = await client.get_tools()

    print(f"[MCP Module] Total loaded MCP tools: {len(all_tools)}")
    return all_tools
