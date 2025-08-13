import os
import yaml
import re
import asyncio
import atexit
from dotenv import load_dotenv

# 모듈 임포트
from workflows.single_agent_flow import create_single_agent_workflow
from modules.a2a_manager import get_a2a_manager
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

async def main():
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
    config = load_config(config_path)
    
    # A2A Manager 초기화
    a2a_manager = get_a2a_manager()
    
    print("\n🚀 A2A 시스템 시작 중...")
    # A2A 서버와 클라이언트 시작 (서버도 함께 시작)
    await a2a_manager.start(start_servers=True)
    
    # 종료 시 정리 함수 등록
    def cleanup_on_exit():
        try:
            asyncio.run(a2a_manager.close())
        except:
            pass
    atexit.register(cleanup_on_exit)
    
    print("\n" + "="*50)
    print("🤖 에이전트를 시작합니다.")
    print("📝 명령어:")
    print("  - 'exit' : 종료")
    print("  - 'debug' : 상태 확인")
    if a2a_manager.ready:
        print("  - '/a2a <agent_name> <message>' : A2A 통신")
        print("    예: /a2a 'Summarize Agent' '이 텍스트를 요약해주세요'")
        print("  💡 이제 LLM이 자동으로 필요시 다른 에이전트와 통신합니다!")
    else:
        print("  ⚠️ A2A 통신 기능이 비활성화되었습니다.")
    print("="*50)

    workflow = create_single_agent_workflow(config)

    memory_config = config.get('memory', {})
    user_id = memory_config.get('default_user_id', 'default_user')

    print(f"👤 사용자 ID: {user_id}")
    print("-" * 50)

    # 대화 상태 유지
    conversation_state = {
        "messages": [],
        "context": "",
        "memory": {},
        "tool_results": [],
        "should_exit": False,
        "user_id": user_id,
        "last_response": "",
        "agent_manager": a2a_manager  # A2AManager 인스턴스 추가
    }

    try:
        # 대화형 루프
        while True:
            # 각 턴마다 새로운 실행 상태 생성
            turn_state = {
                **conversation_state,
                "should_exit": False,
                "tool_results": []
            }
            
            # 워크플로우 실행
            result = workflow.invoke(turn_state)
            
            # 결과 상태 업데이트
            conversation_state.update({
                "messages": result.get("messages", []),
                "memory": result.get("memory", {}),
                "context": result.get("context", ""),
                "last_response": result.get("last_response", "")
            })
            
            # 종료 요청 확인
            if result.get("should_exit", False):
                print("\n👋 에이전트를 종료합니다.")
                break
                
    except KeyboardInterrupt:
        print("\n\n👋 프로그램을 종료합니다.")
    finally:
        # A2A 정리
        await a2a_manager.close()

def run_main():
    """메인 함수를 비동기로 실행"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 프로그램을 종료합니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_main()
