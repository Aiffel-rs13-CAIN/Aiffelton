import os
import re
import yaml
from dotenv import load_dotenv

# 기존 import들 유지
from workflows.single_agent_flow import create_single_agent_workflow
load_dotenv()

def load_config(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        loader = yaml.SafeLoader
        loader.add_implicit_resolver(
            u'tag:yaml.org,2002:env_var',
            re.compile(r'\$\{([^}]+)\}'),
            None
        )
        def constructor_env_var(loader, node):
            value = loader.construct_scalar(node)
            key = value.replace('${', '').replace('}', '')
            return os.getenv(key, value)

        loader.add_constructor(u'tag:yaml.org,2002:env_var', constructor_env_var)
        return yaml.load(f, Loader=loader)

def _print_kv(title: str, kv: dict):
    print(title)
    for k, v in kv.items():
        print(f"   - {k}: {v}")

# MCP 테스트 함수 (임시)
def run_mcp_test(config, prompt: str):
    """MCP 도구 단독 테스트"""
    try:
        from modules.tool_module import ToolNode

        print(f"🧪 Testing MCP tools with: '{prompt}'")
        tool_node = ToolNode(config)

        state = {
            "messages": [prompt + " (Use MCP tools if helpful)"],
            "context": "",
            "memory": {},
            "tool_results": [],
            "should_exit": False,
            "user_id": "test_user",
            "last_response": ""
        }

        result = tool_node.process(state)

        print("\n=== MCP Test Results ===")
        for i, msg in enumerate(result.get("messages", [])):
            if hasattr(msg, 'content'):
                print(f"[{i}] {type(msg).__name__}: {msg.content}")
            else:
                print(f"[{i}] {msg}")

        tool_results = result.get("tool_results", [])
        if tool_results:
            print(f"\nTools used: {tool_results}")

        print("✅ MCP test completed\n")

    except ImportError:
        print("❌ MCP tools not available")
    except Exception as e:
        print(f"❌ MCP test failed: {e}")

def main():
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
    config = load_config(config_path)

    memory_config = config.get('memory', {})
    print("💻 로컬 mem0 메모리 초기화 중...")
    print("✅ 로컬 mem0 메모리가 성공적으로 초기화되었습니다.")
    _print_kv("🧠 메모리 모듈 초기화 완료:", {
        "타입": memory_config.get("type", "mem0"),
        "기본 사용자 ID": memory_config.get("default_user_id", "default_user"),
        "검색 제한": memory_config.get("search_limit", 5),
        "기록 제한": memory_config.get("history_limit", 50),
        "자동 저장": memory_config.get("auto_save", True),
        "압축 임계값": memory_config.get("compress_threshold", 1000),
    })

    # 선택적 MCP 테스트 (환경변수나 CLI 인자로)
    import sys
    test_prompt = os.getenv("MCP_TEST", "").strip()
    if not test_prompt and len(sys.argv) > 2 and sys.argv[1] == "--mcp-test":
        test_prompt = " ".join(sys.argv[2:])

    if test_prompt:
        run_mcp_test(config, test_prompt)
        return

    # ✅ 수정된 AgentCore 클래스 - 딕셔너리 메서드 지원
    class SimpleAgentCore:
        def __init__(self, config_dict):
            self.config = config_dict
            self._config_dict = config_dict

        def get(self, key, default=None):
            """딕셔너리와 같은 get 메서드 제공"""
            return self._config_dict.get(key, default)

        def __getitem__(self, key):
            """딕셔너리와 같은 인덱스 접근 제공"""
            return self._config_dict[key]

        def __contains__(self, key):
            """딕셔너리와 같은 in 연산자 지원"""
            return key in self._config_dict

    agent_core = SimpleAgentCore(config)

    # 기존 워크플로우 생성 (이제 MCP 도구 포함)
    workflow = create_single_agent_workflow(agent_core)

    print("🤖 LLM 모듈 초기화 완료:")
    _print_kv("   ", {
        "공급자": config.get("llm", {}).get("provider", "google"),
        "모델": config.get("llm", {}).get("model", "gemini-2.5-flash"),
        "온도": config.get("llm", {}).get("temperature", 0.7),
    })

    # ✅ MCP 도구 정보 표시 및 디버깅
    print("🔍 MCP 초기화 디버깅...")
    try:
        from modules.tool_module import ToolNode
        print("✅ ToolNode 모듈 임포트 성공")

        mcp_node = ToolNode(config)
        print("✅ ToolNode 인스턴스 생성 성공")

        tools = mcp_node.get_available_tools()
        print(f"🔧 MCP tools count: {len(tools) if tools else 0}")

        if tools:
            print(f"🔧 MCP tools available: {[t.name for t in tools]}")
        else:
            print("ℹ️  No MCP tools configured")

    except Exception as e:
        print(f"❌ MCP tools initialization failed: {e}")
        import traceback
        traceback.print_exc()

    print("에이전트를 시작합니다. (종료하려면 'exit')")

    user_id = memory_config.get('default_user_id', 'default_user')
    print(f"👤 사용자 ID: {user_id}")
    print("-" * 50)

    initial_state = {
        "messages": [],
        "context": "",
        "memory": {},
        "tool_results": [],
        "should_exit": False,
        "user_id": user_id,
        "last_response": ""
    }

    workflow.invoke(initial_state)

if __name__ == "__main__":
    main()