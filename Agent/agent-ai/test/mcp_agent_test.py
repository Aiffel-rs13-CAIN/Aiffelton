# agent-ai/test/mcp_agent_test.py
import sys, asyncio
from pathlib import Path
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage

load_dotenv()

HERE = Path(__file__).resolve()
AGENT_AI = HERE.parents[1]
SERVER = AGENT_AI / "servers" / "mcp_server.py"
assert SERVER.exists(), f"Server not found: {SERVER}"

SYSTEM = """You have tools available.
- When the user asks for the current time, you MUST call the `get_current_time` tool with timezone (default: Asia/Seoul).
- Do NOT say you cannot access real-time information if a tool can provide it.
- If the user did not specify timezone, assume Asia/Seoul.
Return concise, direct answers."""

async def build_agent():
    # ✅ 이 버전 포맷: transport는 문자열, retry 제거
    cfg = {
        "dynamic": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(SERVER)],
            # "retry": {"retries": 0},  # ← 제거! (이 키 때문에 _create_stdio_session 에러)
        }
    }

    client = MultiServerMCPClient(cfg)

    # 버전마다 시그니처가 달라서 두 가지 경로 시도
    try:
        tools = await client.get_tools(server_name="dynamic")
    except TypeError:
        tools = await client.get_tools()

    print("🧰 MCP tools loaded:", [t.name for t in tools])

    # (디버그) 툴 직접 호출
    tb = {t.name: t for t in tools}
    if "get_current_time" in tb:
        direct = await tb["get_current_time"].ainvoke({"timezone": "Asia/Seoul"})
        print("🧪 direct tool call:", direct)

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM),
        ("human", "{input}"),
    ])
    llm_with_system = prompt | llm

    agent = create_react_agent(llm, tools=tools)

    # 호출 시 입력에 규칙을 함께 적어 툴 사용을 유도
    query = "현재 시간을 알려줘 (Asia/Seoul). 반드시 get_current_time 툴을 사용해서 ISO8601로 답해."
    out = agent.invoke({"messages": [HumanMessage(content=query)]})
    return agent

if __name__ == "__main__":
    agent = asyncio.run(build_agent())
    out = agent.invoke({"input": "현재 시간을 알려줘"})
    print("\n=== AGENT OUTPUT ===")
    print(out["output"] if isinstance(out, dict) and "output" in out else str(out))
