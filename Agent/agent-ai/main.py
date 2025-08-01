import os
import yaml
import re
from dotenv import load_dotenv

# 모듈 임포트
from modules.agent_core import AgentCore
from workflows.single_agent_flow import create_single_agent_workflow

load_dotenv()

def load_config(path):
    with open(path, 'r') as f:
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

def main():
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
    config = load_config(config_path)
    
    agent_core = AgentCore(config)
    
    workflow = create_single_agent_workflow(agent_core)
    
    print("에이전트를 시작합니다. (종료하려면 'exit')")
    
    # config에서 기본 사용자 ID 읽기
    memory_config = config.get('memory', {})
    user_id = memory_config.get('default_user_id', 'default_user')
    
    print(f"👤 사용자 ID: {user_id}")
    print("💡 멀티턴 대화가 가능합니다. 이전 대화 내용을 기억합니다.")
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
