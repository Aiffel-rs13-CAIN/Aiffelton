# main.py
import os
import yaml
import re
import asyncio
from dotenv import load_dotenv

# 모듈 임포트
from workflows.single_agent_flow import create_single_agent_workflow
from modules.mcp_module import load_mcp_tools_from_config

load_dotenv()

def load_config(path):
    with open(path, 'r', encoding='utf-8') as f:
        loader = yaml.SafeLoader
        loader.add_implicit_resolver(
            u'tag:yaml.org,2002:env_var',
            re.compile(r'\$\{(.*)\}'),
            None
        )
        def constructor_env_var(loader, node):
            value = loader.construct_scalar(node)
            key = value.replace('${', '').replace('}', '')
            return os.getenv(key)
        loader.add_constructor(u'tag:yaml.org,2002:env_var', constructor_env_var)
        return yaml.load(f, Loader=loader)

async def main():
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
    config = load_config(config_path)

    # --- 도구 준비 --- #
    normal_tools = []
    mcp_config = config.get('mcp', {})
    mcp_tools = []
    if mcp_config.get('config_path'):
        mcp_tools = await load_mcp_tools_from_config(mcp_config['config_path'])
    all_tools = normal_tools + mcp_tools

    # --- 디버깅: 최종 통합된 도구 정보 출력 --- #
    print(f"\n[Main Debug] Final tools to be passed to agent: {len(all_tools)}")
    for tool in all_tools:
        print(f"  - Tool Name: {tool.name}")
        print(f"    Description: {tool.description}")
        print(f"    Args Schema: {tool.args_schema}")
    print("-" * 20)

    # --- 워크플로우 생성 --- #
    workflow = await create_single_agent_workflow(config, all_tools)

    print("\n 에이전트를 시작합니다. (종료하려면 'exit')")

    # --- 워크플로우 실행 --- #
    memory_config = config.get('memory', {})
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
    
    await workflow.ainvoke(initial_state)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n 사용자에 의해 중단되었습니다.")
