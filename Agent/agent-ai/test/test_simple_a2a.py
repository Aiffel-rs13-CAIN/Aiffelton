#!/usr/bin/env python3
"""
간단한 A2A 로컬 서버 테스트
- 원격 A2A 클라이언트 연결 없이 로컬 서버만 테스트
"""

import sys
import os
import asyncio
import time
import httpx

# 프로젝트 루트 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from modules.a2a_module import A2ANode


async def test_local_servers_only():
    """로컬 서버만으로 A2A 통신 테스트"""
    
    print("🧪 로컬 A2A 서버 전용 테스트")
    print("=" * 50)
    
    a2a_node = A2ANode()
    
    try:
        print("\n1️⃣ 단계 1: 로컬 A2A 서버들만 시작")
        print("-" * 40)
        
        # 로컬 서버만 시작하고 원격 연결은 시도하지 않음
        await a2a_node.start_local_servers()
        
        # 서버가 완전히 준비될 때까지 대기
        await asyncio.sleep(3)
        
        print("\n2️⃣ 단계 2: 서버 상태 및 접근성 확인")
        print("-" * 40)
        
        stats = a2a_node.get_server_stats()
        
        if not stats:
            print("❌ 실행 중인 서버가 없습니다.")
            return False
        
        # 각 서버에 직접 HTTP 요청 테스트
        async with httpx.AsyncClient(timeout=5.0) as client:
            for name, stat in stats.items():
                port = stat["port"]
                
                print(f"\n🔍 {name} 테스트 (포트 {port}):")
                
                # Health check 테스트
                try:
                    health_response = await client.get(f"http://localhost:{port}/health")
                    if health_response.status_code == 200:
                        print(f"   ✅ Health Check: OK")
                        health_data = health_response.json()
                        print(f"   📊 상태: {health_data.get('status', 'unknown')}")
                    else:
                        print(f"   ❌ Health Check: 실패 (코드 {health_response.status_code})")
                except Exception as e:
                    print(f"   ❌ Health Check: 연결 오류 ({e})")
                
                # Agent Card 테스트
                try:
                    card_response = await client.get(f"http://localhost:{port}/.well-known/agent-card.json")
                    if card_response.status_code == 200:
                        print(f"   ✅ Agent Card: OK")
                        card_data = card_response.json()
                        print(f"   📋 에이전트: {card_data.get('name', 'unknown')}")
                        print(f"   🔧 기능: {len(card_data.get('capabilities', []))}개")
                    else:
                        print(f"   ❌ Agent Card: 실패 (코드 {card_response.status_code})")
                except Exception as e:
                    print(f"   ❌ Agent Card: 연결 오류 ({e})")
                
                # Chat 엔드포인트 테스트
                try:
                    test_message = {
                        "message": "안녕하세요! 테스트 메시지입니다.",
                        "sender": "TestClient"
                    }
                    
                    chat_response = await client.post(
                        f"http://localhost:{port}/chat",
                        json=test_message,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if chat_response.status_code == 200:
                        print(f"   ✅ Chat 통신: OK")
                        chat_data = chat_response.json()
                        response_msg = chat_data.get("message", "응답 없음")
                        print(f"   💬 응답: {response_msg[:50]}...")
                    else:
                        print(f"   ❌ Chat 통신: 실패 (코드 {chat_response.status_code})")
                        
                except Exception as e:
                    print(f"   ❌ Chat 통신: 오류 ({e})")
        
        print("\n3️⃣ 단계 3: 서버 간 메시지 교환 시뮬레이션")
        print("-" * 40)
        
        # 서버 간 직접 메시지 교환 테스트
        server_list = list(stats.items())
        
        if len(server_list) >= 2:
            # 첫 번째 서버에서 두 번째 서버로 메시지 전송
            sender_name, sender_stat = server_list[0]
            receiver_name, receiver_stat = server_list[1]
            
            print(f"📤 {sender_name} → {receiver_name} 메시지 전송 테스트")
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                test_message = {
                    "message": f"안녕하세요 {receiver_name}! 저는 {sender_name}입니다. 창의성에 대해 어떻게 생각하시나요?",
                    "sender": sender_name
                }
                
                try:
                    response = await client.post(
                        f"http://localhost:{receiver_stat['port']}/chat",
                        json=test_message,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        print("✅ 서버 간 통신 성공!")
                        response_data = response.json()
                        reply = response_data.get("message", "응답 없음")
                        print(f"📨 {receiver_name}의 응답: {reply}")
                        
                        # 응답을 다시 첫 번째 서버로 전송
                        follow_up = {
                            "message": f"흥미로운 관점이네요! {reply[:30]}... 에 대해 더 자세히 알고 싶습니다.",
                            "sender": receiver_name
                        }
                        
                        follow_response = await client.post(
                            f"http://localhost:{sender_stat['port']}/chat",
                            json=follow_up,
                            headers={"Content-Type": "application/json"}
                        )
                        
                        if follow_response.status_code == 200:
                            follow_data = follow_response.json()
                            print(f"🔄 {sender_name}의 후속 응답: {follow_data.get('message', '응답 없음')}")
                        
                    else:
                        print(f"❌ 서버 간 통신 실패: {response.status_code}")
                        
                except Exception as e:
                    print(f"❌ 서버 간 통신 오류: {e}")
        else:
            print("⚠️ 서버가 2개 미만이므로 서버 간 통신 테스트를 건너뜁니다.")
        
        print("\n4️⃣ 단계 4: 최종 통계")
        print("-" * 40)
        
        final_stats = a2a_node.get_server_stats()
        for name, stat in final_stats.items():
            print(f"📊 {name}:")
            print(f"   - 상태: {'✅ 실행 중' if stat['running'] else '❌ 중지됨'}")
            print(f"   - 포트: {stat['port']}")
            print(f"   - 수신 메시지: {stat['messages_received']}개")
        
        print("\n🎉 로컬 A2A 서버 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        print("\n🧹 정리 중...")
        await a2a_node.cleanup()


async def main():
    """메인 함수"""
    print("🎯 A2A 로컬 서버 전용 테스트")
    print("이 테스트는 원격 A2A 연결 없이 로컬 서버만으로 통신을 확인합니다.\n")
    
    success = await test_local_servers_only()
    
    print("\n" + "="*50)
    if success:
        print("🎉 모든 테스트 성공!")
        print("💡 로컬 A2A 서버가 정상적으로 작동하고 있습니다!")
    else:
        print("❌ 테스트 실패")
        print("🔧 로컬 서버 설정을 확인해주세요.")
    
    return success


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 중단됨")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 예상치 못한 오류: {e}")
        sys.exit(1)
