# Agent/agent-ai/test/mcp_smoketest.py
import asyncio, json, pathlib, os
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "mcp_config.json"

def load_cfg():
    with open(CONFIG, "r", encoding="utf-8") as f:
        return json.load(f)

def to_client_cfg(cfg):
    out = {}
    ROOT = CONFIG.parents[1]  # .../agent-ai
    for name, s in cfg.get("servers", {}).items():
        t = s.get("transport")
        if t == "stdio":
            cmd = s["command"]
            args = list(s.get("args", []))
            # 서버 스크립트 경로를 절대경로로
            if args and not os.path.isabs(args[0]):
                args[0] = str((ROOT / args[0]).resolve())

            # ✅ MCP_CONFIG_PATH 절대경로 강제 주입
            env = dict(s.get("env", {}))
            env["MCP_CONFIG_PATH"] = str(CONFIG.resolve())

            out[name] = {
                "transport": "stdio",
                "command": cmd,
                "args": args,
                "env": env,
            }
        elif t == "streamable_http":
            out[name] = {
                "transport": "streamable_http",
                "url": s["url"],
                "headers": s.get("headers", {}),
            }
    return out


async def main():
    cfg = load_cfg()
    client_cfg = to_client_cfg(cfg)
    client = MultiServerMCPClient(client_cfg)

    # 우선 서버 이름을 뽑아 온다.
    server_names = list(client_cfg.keys())
    if not server_names:
        print("❌ No MCP servers configured.")
        return

    # 하나만 테스트해도 되고, 여러 개면 합칠 수도 있음
    name = server_names[0]
    print(f"🔌 Using MCP server: {name}")

    async with client.session(name) as session:
        tools = await load_mcp_tools(session)
        print("🧰 tools:", [t.name for t in tools])

        time_now = next((t for t in tools if t.name == "time_now"), None)
        if not time_now:
            print("❌ 'time_now' tool not found. Check dynamic_tools in mcp_config.json")
            return

        out = await time_now.ainvoke({"tz": "Asia/Seoul"})
        print("⏰ time_now:", out)

if __name__ == "__main__":
    asyncio.run(main())
