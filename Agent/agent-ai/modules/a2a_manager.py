"""
A2AManager: A2A 서버/클라이언트 라이프사이클과 전송을 관리하는 매니저
- 기존 main.py의 AgentManager 기능을 모듈화
- 싱글톤 패턴으로 전역에서 접근 가능
"""
import os
import asyncio
from typing import Optional, List, Dict, Any

from .a2a_client_module import A2AClientModule
from .a2a_server_module import A2AServerModule


class A2AManager:
    def __init__(self, config_dir: Optional[str] = None):
        # 기본 config 디렉터리 설정
        if config_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_dir = os.path.join(os.path.dirname(base_dir), "config", "a2a")
        
        self.config_dir = config_dir
        self._servers: List[A2AServerModule] = []
        self._client: Optional[A2AClientModule] = None
        self._ready = False

    @property
    def ready(self) -> bool:
        """A2A 시스템이 준비되었는지 확인"""
        return self._ready and self._client is not None and self._client.ready

    async def start(self, start_servers: bool = False) -> None:
        """A2A 환경을 시작합니다"""
        print("🚀 A2A Manager 시작 중...")
        
        if start_servers:
            # 서버 시작
            await self._start_servers()
        
        # 클라이언트 초기화
        await self._initialize_client()
        
        self._ready = True
        print(f"✅ A2A Manager 준비 완료 (서버: {len(self._servers)}개, 클라이언트: {'준비됨' if self.ready else '실패'})")

    async def _start_servers(self) -> None:
        """A2A 서버들을 시작합니다"""
        server_names = ["LabAssistant", "Summarize Agent", "Recorder Agent"]
        
        for server_name in server_names:
            try:
                server = A2AServerModule()
                if server.start_by_name(server_name, self.config_dir):
                    self._servers.append(server)
                    print(f"  ✅ 서버 시작됨: {server_name}")
                else:
                    print(f"  ⚠️ 서버 시작 실패: {server_name}")
            except Exception as e:
                print(f"  ❌ 서버 오류 ({server_name}): {e}")
        
        if self._servers:
            print(f"  ⏳ 서버 준비 대기 중... (3초)")
            await asyncio.sleep(3)

    async def start_specific_server(self, server_name: str) -> bool:
        """특정 A2A 서버만 시작합니다"""
        try:
            server = A2AServerModule()
            if server.start_by_name(server_name, self.config_dir):
                self._servers.append(server)
                print(f"  ✅ 서버 시작됨: {server_name}")
                
                # 서버 준비 대기
                print(f"  ⏳ 서버 준비 대기 중... (3초)")
                await asyncio.sleep(3)
                
                # 무한 대기 (서버 유지)
                print(f"  🔄 {server_name} 서버 실행 중...")
                while True:
                    await asyncio.sleep(1)
                    
            else:
                print(f"  ⚠️ 서버 시작 실패: {server_name}")
                return False
        except Exception as e:
            print(f"  ❌ 서버 오류 ({server_name}): {e}")
            return False

    async def _initialize_client(self) -> None:
        """A2A 클라이언트를 초기화합니다"""
        try:
            self._client = A2AClientModule()
            await self._client.initialize(self.config_dir)
            
            # 에이전트 카드 수집 대기
            await asyncio.sleep(1.5)
            
            if self._client.ready:
                print("  ✅ A2A 클라이언트 준비 완료")
            else:
                print("  ⚠️ A2A 클라이언트 준비되지 않음")
                
        except Exception as e:
            print(f"  ❌ A2A 클라이언트 초기화 오류: {e}")

    async def send(self, agent_name: str, text: str) -> Optional[List[str]]:
        """다른 에이전트에게 메시지를 전송합니다"""
        if not self.ready:
            print(f"⚠️ A2A Manager가 준비되지 않음. 자동 초기화 시도...")
            await self.start()
        
        if not self._client or not self._client.ready:
            print(f"❌ A2A 클라이언트가 준비되지 않음")
            return None

        try:
            print(f"📤 A2A 전송 중: '{agent_name}'에게 → {text[:50]}...")
            response = await self._client.send(agent_name, text, config_dir=self.config_dir)
            print(f"📥 A2A 응답 받음: {response}")
            return response
        except Exception as e:
            print(f"❌ A2A 전송 오류: {e}")
            return None

    async def close(self) -> None:
        """A2A 환경을 정리합니다"""
        print("🛑 A2A Manager 종료 중...")
        
        if self._client:
            try:
                await self._client.close()
            except Exception as e:
                print(f"클라이언트 종료 오류: {e}")
        
        for server in self._servers:
            try:
                server.stop()
            except Exception as e:
                print(f"서버 종료 오류: {e}")
        
        self._servers.clear()
        self._client = None
        self._ready = False
        print("✅ A2A Manager 종료 완료")


# 전역 싱글톤 인스턴스
_global_manager: Optional[A2AManager] = None


def get_a2a_manager() -> A2AManager:
    """전역 A2A Manager 인스턴스를 반환합니다"""
    global _global_manager
    if _global_manager is None:
        _global_manager = A2AManager()
    return _global_manager
