#!/usr/bin/env python3
"""
A2A 두 서버 + 클라이언트 통신 테스트
"""
import os
import sys
import time
import asyncio
import requests

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(__file__))

from modules.a2a_server_module import A2AServerModule
from modules.a2a_client_module import A2AClientModule


async def test_full_a2a_communication():
    """A2A 전체 시스템 통신 테스트"""
    print("🧪 A2A 전체 시스템 통신 테스트")
    print("=" * 50)
    
    config_dir = os.path.join(os.path.dirname(__file__), 'config', 'a2a')
    
    servers = []
    
    try:
        # 1. 두 서버 모두 시작
        print("1️⃣ A2A 서버들 시작...")
        
        # Summarize Agent 서버
        summarize_server = A2AServerModule()
        if summarize_server.start_by_name("Summarize Agent", config_dir):
            print("✅ Summarize Agent 서버 시작 성공")
            servers.append(summarize_server)
        else:
            print("❌ Summarize Agent 서버 시작 실패")
        
        # Recorder Agent 서버  
        recorder_server = A2AServerModule()
        if recorder_server.start_by_name("Recorder Agent", config_dir):
            print("✅ Recorder Agent 서버 시작 성공")
            servers.append(recorder_server)
        else:
            print("❌ Recorder Agent 서버 시작 실패")
        
        if not servers:
            print("❌ 서버가 하나도 시작되지 않았습니다")
            return
        
        # 서버 준비 대기
        print("⏳ 서버들 준비 대기...")
        await asyncio.sleep(5)
        
        # 2. 서버 상태 확인
        print("\n2️⃣ 서버 상태 확인...")
        test_ports = [10000, 10001]
        for port in test_ports:
            try:
                response = requests.get(f"http://localhost:{port}/.well-known/agent-card.json", timeout=5)
                if response.status_code == 200:
                    card = response.json()
                    print(f"✅ 포트 {port}: {card.get('name')} - {card.get('description')[:30]}...")
                else:
                    print(f"❌ 포트 {port}: HTTP {response.status_code}")
            except Exception as e:
                print(f"❌ 포트 {port}: 연결 실패 - {e}")
        
        # 3. 클라이언트 초기화
        print("\n3️⃣ A2A 클라이언트 초기화...")
        client = A2AClientModule()
        await client.initialize(config_dir)
        
        # 클라이언트 준비 대기
        print("⏳ 클라이언트 카드 수집 대기...")
        await asyncio.sleep(3)
        
        if not client.ready:
            print("❌ 클라이언트 초기화 실패")
            return
        
        print("✅ 클라이언트 초기화 성공")
        
        # 4. 사용 가능한 에이전트 확인
        print("\n4️⃣ 사용 가능한 에이전트 확인...")
        if hasattr(client._client, 'list_remote_agents'):
            agents = client._client.list_remote_agents()
            print(f"📋 발견된 에이전트 수: {len(agents)}")
            for agent in agents:
                print(f"   - {agent.get('name')}: {agent.get('description')}")
        
        # 연결된 에이전트 확인
        if hasattr(client._client, 'remote_agent_connections'):
            connections = client._client.remote_agent_connections
            print(f"\n🔗 연결된 에이전트: {list(connections.keys())}")
        
        # 5. 메시지 전송 테스트 - Recorder Agent
        if "Recorder Agent" in connections:
            print("\n5️⃣ Recorder Agent 메시지 전송 테스트...")
            try:
                test_message = "안녕하세요! Recorder Agent에게 보내는 테스트 메시지입니다."
                print(f"📤 전송 메시지: {test_message}")
                
                response = await client.send(
                    "Recorder Agent", 
                    test_message,
                    config_dir=config_dir
                )
                
                if response:
                    print("✅ Recorder Agent 응답 수신 성공:")
                    for i, resp in enumerate(response):
                        print(f"   응답 {i+1}: {resp}")
                else:
                    print("⚠️ Recorder Agent 응답이 없습니다")
                    
            except Exception as e:
                print(f"❌ Recorder Agent 메시지 전송 실패: {e}")
                import traceback
                traceback.print_exc()
        
        # 6. 메시지 전송 테스트 - Summarize Agent
        if "Summarize Agent" in connections:
            print("\n6️⃣ Summarize Agent 메시지 전송 테스트...")
            try:
                test_message = "이것은 긴 텍스트입니다. 여러 문장으로 이루어져 있고, 요약을 테스트하기 위한 내용입니다. A2A 프로토콜을 통해 에이전트 간 통신이 정상적으로 작동하는지 확인하는 것이 목적입니다."
                print(f"📤 전송 메시지: {test_message}")
                
                response = await client.send(
                    "Summarize Agent",
                    test_message,
                    config_dir=config_dir
                )
                
                if response:
                    print("✅ Summarize Agent 응답 수신 성공:")
                    for i, resp in enumerate(response):
                        print(f"   응답 {i+1}: {resp}")
                else:
                    print("⚠️ Summarize Agent 응답이 없습니다")
                    
            except Exception as e:
                print(f"❌ Summarize Agent 메시지 전송 실패: {e}")
                import traceback
                traceback.print_exc()
        
        # 클라이언트 정리
        await client.close()
        print("\n✅ 클라이언트 정리 완료")
        
    finally:
        # 서버들 정리
        print("\n🛑 서버들 중지...")
        for i, server in enumerate(servers):
            try:
                server.stop()
                print(f"✅ 서버 {i+1} 중지 완료")
            except Exception as e:
                print(f"⚠️ 서버 {i+1} 중지 중 오류: {e}")


if __name__ == "__main__":
    asyncio.run(test_full_a2a_communication())
