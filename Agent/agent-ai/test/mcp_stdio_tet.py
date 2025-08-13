import json, os, sys, subprocess
from pathlib import Path

# 이 파일 기준 경로 계산: test/ → agent-ai/ → repo 루트
HERE = Path(__file__).resolve()
AGENT_AI = HERE.parents[1]               # .../Agent/agent-ai
REPO = AGENT_AI.parents[1]               # .../Aiffelton

PY = sys.executable                      # 현재 파이썬(venv 포함)
SERVER = AGENT_AI / "servers" / "mcp_server.py"
CWD = AGENT_AI

def must_exist(p: Path, label: str):
    if not p.exists():
        raise FileNotFoundError(f"{label} not found: {p}")
    return p

# 경로 검증
must_exist(Path(PY), "Python executable")
must_exist(SERVER, "MCP server")
must_exist(CWD, "CWD")

print("[PATH] PY =", PY)
print("[PATH] SERVER =", SERVER)
print("[PATH] CWD =", CWD)

# 서버 프로세스 실행 (stdio)
proc = subprocess.Popen(
    [PY, "-u", str(SERVER)],
    cwd=str(CWD),
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

def send(req):
    line = json.dumps(req, ensure_ascii=True)
    proc.stdin.write(line + "\n")
    proc.stdin.flush()
    resp = proc.stdout.readline().strip()
    print("RESP:", resp)

try:
    send({"jsonrpc":"2.0","id":1,"method":"initialize"})
    send({"jsonrpc":"2.0","id":2,"method":"tools/list"})
    send({
        "jsonrpc":"2.0","id":3,"method":"tools/call",
        "params":{"name":"get_current_time","arguments":{"timezone":"Asia/Seoul"}}
    })
finally:
    proc.kill()
