import os
import yaml
import re
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

# 모듈 임포트
from modules.agent_core import AgentCore
from config.langgraph.single_agent_flow import create_single_agent_workflow
from dotenv import load_dotenv

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

    # AgentCore 및 LangGraph 워크플로우 초기화
    try:
        agent_core = AgentCore(config)
        workflow = create_single_agent_workflow(agent_core)
    except ValueError as e:
        print(f"오류: {e}")
        return

    print(f"'{config['agent']['name']}' 에이전트가 준비되었습니다. 질문을 입력하세요. (종료하려면 'exit' 입력)")

    while True:
        try:
            query = input("사용자: ")
            if query.lower() == 'exit':
                print("에이전트를 종료합니다.")
                break
            # LangGraph 워크플로우 실행
            inputs = {"messages": [HumanMessage(content=query)]}
            # stream()을 사용하면 중간 과정을 볼 수 있습니다.
            for output in workflow.stream(inputs):
                # stream()의 각 출력은 key-value 쌍입니다.
                for key, value in output.items():
                    if key == "llm":
                        if value.get('messages') and value['messages'][-1].content:
                            print(f"에이전트: {value['messages'][-1].content}")
        except (KeyboardInterrupt, EOFError):
            print("\n에이전트를 종료합니다.")
            break

if __name__ == "__main__":
    main()
