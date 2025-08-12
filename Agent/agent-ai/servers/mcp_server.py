import sys
import os
import json
import threading
import importlib.util
import subprocess
import requests
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo  # Python 3.9+
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# UTF-8
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    except Exception:
        pass

# -------------------------------
# 경로
# -------------------------------
ROOT = Path(__file__).resolve().parents[1]  # .../agent-ai
_env_path = os.environ.get("MCP_CONFIG_PATH", "").strip()

if _env_path:
    CONFIG_PATH = Path(_env_path)
    if not CONFIG_PATH.is_absolute():
        CONFIG_PATH = (ROOT / CONFIG_PATH).resolve()
else:
    CONFIG_PATH = (ROOT / "config" / "mcp_config.json").resolve()


# -------------------------------
# 로깅
# -------------------------------
def _log(msg: str):
    sys.stderr.write(f"[dynamic-mcp] {msg}\n")
    sys.stderr.flush()


# -------------------------------
# Dynamic Tool Execution Engine (툴 실행기)
# -------------------------------
class DynamicToolExecutor:
    """완전히 동적인 도구 실행 엔진"""

    def __init__(self):
        self.safe_builtins = {
            # 안전한 내장 함수들
            'len', 'str', 'int', 'float', 'bool', 'list', 'dict', 'tuple', 'set',
            'min', 'max', 'sum', 'abs', 'round', 'sorted', 'reversed',
            'range', 'enumerate', 'zip', 'map', 'filter',
            'print'  # 디버깅용
        }

        self.safe_modules = {
            'datetime': ['datetime', 'timezone', 'timedelta'],
            'zoneinfo': ['ZoneInfo'],
            'math': ['sin', 'cos', 'tan', 'sqrt', 'pow', 'log', 'exp', 'pi', 'e'],
            'random': ['random', 'randint', 'choice', 'shuffle'],
            'json': ['loads', 'dumps'],
            're': ['match', 'search', 'findall', 'sub', 'split'],
            'requests': ['get', 'post', 'put', 'delete'],
            'subprocess': ['run', 'PIPE'],
            'pathlib': ['Path'],
            'os': ['getenv', 'listdir', 'getcwd'],
        }

    def create_safe_globals(self):
        """안전한 실행 환경 생성"""
        safe_globals = {
            '__builtins__': {name: getattr(__builtins__, name)
                             for name in self.safe_builtins
                             if hasattr(__builtins__, name)}
        }

        # 안전한 모듈들 임포트
        for module_name, allowed_attrs in self.safe_modules.items():
            try:
                module = importlib.import_module(module_name)
                safe_globals[module_name] = type('Module', (), {
                    attr: getattr(module, attr)
                    for attr in allowed_attrs
                    if hasattr(module, attr)
                })()
            except ImportError:
                _log(f"Module {module_name} not available")

        return safe_globals

    def execute_tool(self, tool_config: dict, params: dict):
        """도구 실행"""
        tool_type = tool_config.get("type", "python")

        if tool_type == "python":
            return self._execute_python(tool_config, params)
        elif tool_type == "shell":
            return self._execute_shell(tool_config, params)
        elif tool_type == "http":
            return self._execute_http(tool_config, params)
        elif tool_type == "file":
            return self._execute_file(tool_config, params)
        else:
            return f"Unsupported tool type: {tool_type}"

    def _execute_python(self, tool_config: dict, params: dict):
        """Python 코드 실행"""
        code = tool_config.get("code", "")
        if not code:
            return "No Python code provided"

        try:
            safe_globals = self.create_safe_globals()
            safe_globals['params'] = params
            safe_globals['result'] = None

            exec(code, safe_globals)
            return safe_globals.get('result', 'No result returned')
        except Exception as e:
            return f"Python execution error: {str(e)}"

    def _execute_shell(self, tool_config: dict, params: dict):
        """Shell 명령 실행"""
        command = tool_config.get("command", "")
        if not command:
            return "No shell command provided"

        # 파라미터를 명령어에 치환
        for key, value in params.items():
            command = command.replace(f"{{{key}}}", str(value))

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30  # 30초 타임아웃
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"Command failed: {result.stderr.strip()}"
        except subprocess.TimeoutExpired:
            return "Command timed out"
        except Exception as e:
            return f"Shell execution error: {str(e)}"

    def _execute_http(self, tool_config: dict, params: dict):
        """HTTP 요청 실행"""
        method = tool_config.get("method", "GET").upper()
        url = tool_config.get("url", "")
        headers = tool_config.get("headers", {})

        if not url:
            return "No URL provided"

        # URL에 파라미터 치환
        for key, value in params.items():
            url = url.replace(f"{{{key}}}", str(value))

        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=params, headers=headers, timeout=10)
            elif method == "PUT":
                response = requests.put(url, json=params, headers=headers, timeout=10)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                return f"Unsupported HTTP method: {method}"

            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.text
            }
        except Exception as e:
            return f"HTTP request error: {str(e)}"

    def _execute_file(self, tool_config: dict, params: dict):
        """파일 작업 실행"""
        operation = tool_config.get("operation", "read")
        file_path = tool_config.get("path", "")

        if not file_path:
            return "No file path provided"

        # 파라미터로 파일 경로 치환
        for key, value in params.items():
            file_path = file_path.replace(f"{{{key}}}", str(value))

        try:
            path = Path(file_path)

            if operation == "read":
                if not path.exists():
                    return f"File not found: {file_path}"
                return path.read_text(encoding="utf-8")

            elif operation == "write":
                content = params.get("content", "")
                path.write_text(content, encoding="utf-8")
                return f"File written: {file_path}"

            elif operation == "append":
                content = params.get("content", "")
                with open(path, "a", encoding="utf-8") as f:
                    f.write(content)
                return f"Content appended to: {file_path}"

            elif operation == "exists":
                return path.exists()

            elif operation == "list":
                if path.is_dir():
                    return [str(p) for p in path.iterdir()]
                else:
                    return f"Not a directory: {file_path}"

            else:
                return f"Unsupported file operation: {operation}"

        except Exception as e:
            return f"File operation error: {str(e)}"


# -------------------------------
# Dynamic config state (툴 상태 저장 + 로드/갱신)
# -------------------------------
class ConfigState:
    def __init__(self):
        self.lock = threading.RLock()
        self.tools = []  # MCP tool definitions
        self.tool_configs = {}  # tool_name -> tool_config
        self.executor = DynamicToolExecutor()

    def load(self):
        with self.lock:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)

            tools = cfg.get("dynamic_tools", [])
            valid_tools = []
            tool_configs = {}

            for tool in tools:
                if not all(k in tool for k in ("name", "description")):
                    continue

                # MCP tool definition
                schema = tool.get("schema", {"type": "object", "properties": {}})
                valid_tools.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "inputSchema": schema,
                })

                # Tool execution config
                tool_configs[tool["name"]] = {
                    "type": tool.get("type", "python"),
                    "code": tool.get("code", ""),
                    "command": tool.get("command", ""),
                    "url": tool.get("url", ""),
                    "method": tool.get("method", "GET"),
                    "headers": tool.get("headers", {}),
                    "operation": tool.get("operation", "read"),
                    "path": tool.get("path", "")
                }

            self.tools = valid_tools
            self.tool_configs = tool_configs
            _log(f"Loaded {len(valid_tools)} dynamic tools")

    def list_tools(self):
        with self.lock:
            return list(self.tools)

    def execute_tool(self, tool_name: str, params: dict):
        with self.lock:
            tool_config = self.tool_configs.get(tool_name)
            if not tool_config:
                return f"Tool not found: {tool_name}"

            return self.executor.execute_tool(tool_config, params)


STATE = ConfigState()

# Initial load
try:
    STATE.load()
except FileNotFoundError:
    _log(f"config not found: {CONFIG_PATH}")
except Exception as e:
    _log(f"initial load error: {e}")


# -------------------------------
# 감시자 (핫 리로드 -> mcp_config 파일이 수정되면 중단 없이 재적용)
# -------------------------------
class _ReloadHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return
        if Path(event.src_path) != CONFIG_PATH:
            return
        try:
            STATE.load()
            _log("dynamic_tools reloaded")
        except Exception as e:
            _log(f"reload failed: {e}")


# -------------------------------
# JSON-RPC helpers
# -------------------------------
def _ok(id_, result_obj):
    return {"jsonrpc": "2.0", "id": id_, "result": result_obj}


def _error(id_, code, message):
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


# -------------------------------
# Request handler (라우터)
# -------------------------------
def handle_request(req):
    rid = req.get("id")
    method = req.get("method")

    if method == "initialize":
        _log("initialize received")
        return _ok(rid, {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "dynamic-mcp-server", "version": "0.2.0"},
            "capabilities": {
                "tools": {"listChanged": True}
            },
        })

    if method in ("tools/list", "list_tools"):
        _log("tools/list requested")
        return _ok(rid, {"tools": STATE.list_tools()})

    if method in ("tools/call", "call_tool"):
        params = req.get("params", {}) or {}
        name = params.get("name")
        args = params.get("arguments", {}) or {}

        if not name:
            return _error(rid, -32602, "Missing tool name")

        try:
            result = STATE.execute_tool(name, args)

            # 결과를 문자열로 변환
            if isinstance(result, str):
                text = result
            else:
                text = json.dumps(result, ensure_ascii=False)

            return _ok(rid, {"content": [{"type": "text", "text": text}]})
        except Exception as e:
            return _ok(rid, {
                "content": [{"type": "text", "text": str(e)}],
                "isError": True
            })

    if method == "notifications/subscribe":
        _log("notifications/subscribe received")
        return _ok(rid, {})

    return _error(rid, -32601, f"Unknown method: {method}")


# -------------------------------
# Main loop (서버 구동, 핫 리로드 구동, JSON-RPC 처리/응답)
# -------------------------------
def main():
    # Start watcher
    observer = Observer()
    observer.schedule(_ReloadHandler(), CONFIG_PATH.parent.as_posix(), recursive=False)
    observer.start()
    _log(f"dynamic MCP server started. Watching: {CONFIG_PATH}")

    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except json.JSONDecodeError:
                _log(f"invalid json: {line[:120]}...")
                continue

            resp = handle_request(req)
            print(json.dumps(resp, ensure_ascii=True))
            sys.stdout.flush()
    finally:
        observer.stop()
        observer.join()
        _log("file watcher stopped")


if __name__ == "__main__":
    main()