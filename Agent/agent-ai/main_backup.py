
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

    initial_state = {
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
        workflow.invoke(initial_state)
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

class AgentManager:
    """A2A 서버와 클라이언트를 관리하는 클래스"""
    
    def __init__(self):
        self.servers = []
        self.client = None
        self.config_dir = None
        
    async def start_a2a_servers(self, config_dir):
        """A2A 서버들을 시작"""
        self.config_dir = config_dir
        print("\n🚀 A2A 서버 시작 중...")
        
        # Summarize Agent 서버
        summarize_server = A2AServerModule()
        if summarize_server.start_by_name("Summarize Agent", config_dir):
            print("✅ Summarize Agent 서버 시작 성공")
            self.servers.append(summarize_server)
        else:
            print("⚠️ Summarize Agent 서버 시작 실패")
        
        # Recorder Agent 서버  
        recorder_server = A2AServerModule()
        if recorder_server.start_by_name("Recorder Agent", config_dir):
            print("✅ Recorder Agent 서버 시작 성공")
            self.servers.append(recorder_server)
        else:
            print("⚠️ Recorder Agent 서버 시작 실패")
        
        if self.servers:
            print(f"✅ {len(self.servers)}개의 A2A 서버가 시작되었습니다.")
            # 서버 준비 대기 (더 길게)
            print("⏳ 서버 준비 대기 중...")
            await asyncio.sleep(5)
        else:
            print("⚠️ 시작된 A2A 서버가 없습니다.")
    
    async def initialize_client(self):
        """A2A 클라이언트 초기화 (옵셔널)"""
        if not self.config_dir:
            return False
            
        try:
            print("\n🔗 A2A 클라이언트 초기화 중...")
            self.client = A2AClientModule()
            
            # 더 안전한 초기화
            await self.client.initialize(self.config_dir)
            
            # 클라이언트 준비 대기 (더 길게)
            print("⏳ 클라이언트 준비 대기 중...")
            await asyncio.sleep(3)
            
            if self.client.ready:
                print("✅ A2A 클라이언트 초기화 성공")
                
                # 연결된 에이전트 확인
                if hasattr(self.client, '_client') and self.client._client:
                    if hasattr(self.client._client, 'remote_agent_connections'):
                        connections = self.client._client.remote_agent_connections
                        if connections:
                            print(f"🔗 연결된 에이전트: {list(connections.keys())}")
                        else:
                            print("⚠️ 연결된 에이전트가 없습니다.")
                    
                    # 사용 가능한 에이전트 확인
                    if hasattr(self.client, '_entries') and self.client._entries:
                        agent_names = [entry.get('agent_name', 'Unknown') for entry in self.client._entries]
                        print(f"📋 사용 가능한 에이전트: {agent_names}")
                
                return True
            else:
                print("⚠️ A2A 클라이언트 초기화 실패")
                return False
                
        except Exception as e:
            print(f"⚠️ A2A 클라이언트 초기화 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def send_message(self, agent_name, message):
        """A2A를 통해 메시지 전송"""
        if not self.client or not self.client.ready:
            print("⚠️ A2A 클라이언트가 준비되지 않았습니다.")
            print("💡 클라이언트 재초기화를 시도합니다...")
            
            # 클라이언트 재초기화 시도
            success = await self.initialize_client()
            if not success:
                print("❌ 클라이언트 재초기화 실패")
                return None
            
        try:
            print(f"📤 {agent_name}에게 메시지 전송 중: {message[:50]}...")
            response = await self.client.send(agent_name, message, config_dir=self.config_dir)
            
            if response:
                print(f"📨 응답 받음: {len(response)}개의 메시지")
            else:
                print("📭 응답이 없습니다.")
                
            return response
        except Exception as e:
            print(f"⚠️ A2A 메시지 전송 오류: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def cleanup(self):
        """리소스 정리"""
        print("\n🛑 A2A 서버들 중지 중...")
        for i, server in enumerate(self.servers):
            try:
                server.stop()
                print(f"✅ 서버 {i+1} 중지 완료")
            except Exception as e:
                print(f"⚠️ 서버 {i+1} 중지 중 오류: {e}")
        
        if self.client:
            try:
                # 클라이언트 정리는 비동기이므로 여기서는 스킵
                print("✅ A2A 클라이언트 정리 예정")
            except Exception as e:
                print(f"⚠️ 클라이언트 정리 중 오류: {e}")

# 전역 에이전트 매니저 인스턴스
agent_manager = AgentManager()

def cleanup_on_exit():
    """프로그램 종료 시 정리 함수"""
    agent_manager.cleanup()

async def main():
    # 종료 시 정리 함수 등록
    atexit.register(cleanup_on_exit)
    
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
    config = load_config(config_path)
    
    # A2A 설정 디렉토리
    a2a_config_dir = os.path.join(os.path.dirname(__file__), 'config', 'a2a')
    
    # A2A 서버 시작
    await agent_manager.start_a2a_servers(a2a_config_dir)
    
    # A2A 클라이언트 초기화 (옵셔널)
    client_ready = await agent_manager.initialize_client()
    
    print("\n" + "="*50)
    print("🤖 에이전트를 시작합니다.")
    print("📝 명령어:")
    print("  - 'exit' : 종료")
    print("  - 'debug' : 상태 확인")
    if client_ready:
        print("  - '/a2a <agent_name> <message>' : A2A 통신")
        print("    예: /a2a 'Summarize Agent' '이 텍스트를 요약해주세요'")
    else:
        print("  ⚠️ A2A 통신 기능이 비활성화되었습니다.")
    print("="*50)

    workflow = create_single_agent_workflow(config)

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
        "last_response": "",
        "agent_manager": agent_manager  # AgentManager 인스턴스 추가
    }

    try:
        workflow.invoke(initial_state)
    finally:
        # 클라이언트 정리
        if agent_manager.client:
            try:
                await agent_manager.client.close()
                print("✅ A2A 클라이언트 정리 완료")
            except Exception as e:
                print(f"⚠️ A2A 클라이언트 정리 오류: {e}")

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
