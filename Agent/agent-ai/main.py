import os
import yaml
import re
import asyncio
import atexit
import sys
import json
import glob
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

def get_available_agents():
    """사용 가능한 에이전트 카드 목록을 반환"""
    config_dir = os.path.join(os.path.dirname(__file__), 'config', 'a2a')
    agent_cards = {}
    
    # *.json 파일들을 검색
    json_files = glob.glob(os.path.join(config_dir, "*.json"))
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                card_data = json.load(f)
                agent_name = card_data.get('name')
                if agent_name:
                    agent_cards[agent_name.lower().replace(' ', '_')] = {
                        'name': agent_name,
                        'file': json_file,
                        'description': card_data.get('description', ''),
                        'port': card_data.get('port', 0),
                        'data': card_data
                    }
        except Exception as e:
            print(f"⚠️ 에이전트 카드 로드 실패 ({json_file}): {e}")
    
    return agent_cards

async def run_agent_by_name(agent_name: str):
    """에이전트 이름으로 특정 에이전트 실행"""
    agents = get_available_agents()
    agent_key = agent_name.lower().replace(' ', '_').replace('-', '_')
    
    if agent_key not in agents:
        print(f"❌ 에이전트를 찾을 수 없습니다: {agent_name}")
        print(f"💡 사용 가능한 에이전트:")
        for key, info in agents.items():
            print(f"  - {key} ({info['name']}) - {info['description']}")
        return
    
    agent_info = agents[agent_key]
    agent_display_name = agent_info['name']
    port = agent_info['port']
    
    print(f"\n🚀 {agent_display_name} 서버 시작 중...")
    
    # A2A Manager 초기화
    a2a_manager = get_a2a_manager()
    
    # 특정 에이전트 서버만 시작
    await a2a_manager.start_specific_server(agent_display_name)
    
    # 종료 시 정리 함수 등록
    def cleanup_on_exit():
        try:
            asyncio.run(a2a_manager.close())
        except:
            pass
    atexit.register(cleanup_on_exit)
    
    print("\n" + "="*60)
    print(f"📡 {agent_display_name} 서버가 포트 {port}에서 실행 중입니다.")
    print(f"📝 설명: {agent_info['description']}")
    print("📨 메시지 수신 대기 중...")
    print("📝 명령어:")
    print("  - 'exit' : 종료")
    print("  - 'status' : 상태 확인")
    print("  - 'info' : 에이전트 정보")
    print("="*60)
    
    try:
        # 대화형 루프 (간단한 상태 확인용)
        while True:
            user_input = input(f"\n[{agent_display_name}]> ").strip()
            
            if user_input.lower() == 'exit':
                print(f"\n👋 {agent_display_name}를 종료합니다.")
                break
            elif user_input.lower() == 'status':
                print(f"📊 {agent_display_name} 상태: 실행 중 (포트 {port})")
            elif user_input.lower() == 'info':
                print(f"� 에이전트 정보:")
                print(f"  이름: {agent_display_name}")
                print(f"  포트: {port}")
                print(f"  설명: {agent_info['description']}")
                skills = agent_info['data'].get('skills', [])
                if skills:
                    print(f"  스킬:")
                    for skill in skills:
                        print(f"    - {skill.get('name', 'Unknown')}: {skill.get('description', '')}")
            else:
                print("💡 사용 가능한 명령어: 'exit', 'status', 'info'")
                
    except KeyboardInterrupt:
        print(f"\n\n👋 {agent_display_name}를 종료합니다.")
    finally:
        # A2A 정리
        await a2a_manager.close()

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

def run_agent(agent_name: str):
    """특정 에이전트를 비동기로 실행"""
    try:
        asyncio.run(run_agent_by_name(agent_name))
    except KeyboardInterrupt:
        print(f"\n\n👋 {agent_name} 에이전트를 종료합니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

def list_agents():
    """사용 가능한 에이전트 목록 출력"""
    agents = get_available_agents()
    print("\n📋 사용 가능한 에이전트:")
    print("="*50)
    for key, info in agents.items():
        print(f"🤖 {key}")
        print(f"   이름: {info['name']}")
        print(f"   설명: {info['description']}")
        print(f"   포트: {info['port']}")
        print(f"   실행: python main.py {key}")
        print("-" * 40)

def show_help():
    """사용법 출력"""
    agents = get_available_agents()
    
    print("\n사용법:")
    print("  python main.py                    - 전체 시스템 실행")
    print("  python main.py <agent_name>       - 특정 에이전트만 실행")
    print("  python main.py list               - 사용 가능한 에이전트 목록")
    print("  python main.py --help             - 도움말 출력")
    print("\n사용 가능한 에이전트:")
    for key, info in agents.items():
        print(f"  - {key:<20} ({info['name']})")

if __name__ == "__main__":
    # 커맨드라인 인자 확인
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg in ['--help', '-h', 'help']:
            show_help()
        elif arg == 'list':
            list_agents()
        else:
            # 에이전트 이름으로 실행 시도
            agents = get_available_agents()
            if arg in agents:
                run_agent(arg)
            else:
                print(f"❌ 알 수 없는 에이전트: {sys.argv[1]}")
                print(f"💡 사용 가능한 에이전트: {', '.join(agents.keys())}")
                print(f"💡 전체 목록: python main.py list")
    else:
        # 인자가 없으면 전체 시스템 실행
        run_main()
