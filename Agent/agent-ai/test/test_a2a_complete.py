#!/usr/bin/env python3
"""
A2A 시스템 통합 테스트
- 로컬 서버 생성 및 시작
- A2A 통신 테스트 
- 에이전트 간 대화 시뮬레이션
"""

import sys
import os
import asyncio
import time

# 프로젝트 루트 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from modules.a2a_module import A2ANode


async def test_a2a_system():
    """A2A 시스템 통합 테스트"""
    
    print("🚀 A2A 시스템 통합 테스트")
    print("=" * 50)
    
    a2a_node = A2ANode()
    
    try:
        print("\n1️⃣ A2A 시스템 초기화 (로컬 서버 포함)")
        print("-" * 40)
        
        # 로컬 서버와 함께 초기화
        await a2a_node.initialize(start_local_servers=True)
        
        print("\n2️⃣ 서버 상태 확인")
        print("-" * 40)
        
        # 서버 통계 확인
        stats = a2a_node.get_server_stats()
        for name, stat in stats.items():
            status = "🟢 실행 중" if stat["running"] else "🔴 중지됨"
            print(f"   {name}: {status} (포트 {stat['port']})")
        
        print("\n3️⃣ 사용 가능한 에이전트 확인")
        print("-" * 40)
        
        # 사용 가능한 에이전트 확인
        available_agents = a2a_node.get_available_agents()
        print(f"🔍 발견된 에이전트: {len(available_agents)}개")
        for agent in available_agents:
            print(f"   • {agent}")
        
        print("\n4️⃣ 에이전트 간 대화 테스트")
        print("-" * 40)
        
        if len(available_agents) >= 2:
            # 대화 시나리오
            conversations = [
                (available_agents[0], "안녕하세요! AI와 창의성에 대해 어떻게 생각하시나요?"),
                (available_agents[1], "미래의 인공지능 기술은 어떤 모습일까요?"),
                (available_agents[0], "데이터 분석과 직관적 사고의 균형이 중요할까요?")
            ]
            
            for i, (agent_name, message) in enumerate(conversations, 1):
                print(f"\n{i}. 💬 {agent_name}에게 메시지 전송")
                print(f"   📤 메시지: {message}")
                
                # 실제 A2A 통신
                response = await a2a_node.send_message(agent_name, message)
                
                if response:
                    print(f"   ✅ 응답 수신:")
                    for j, resp in enumerate(response, 1):
                        print(f"      {j}. {resp}")
                else:
                    print(f"   ❌ 응답 없음")
                
                # 다음 메시지 전송 전 대기
                await asyncio.sleep(1)
        
        else:
            print("⚠️ 대화 테스트를 위해 최소 2개의 에이전트가 필요합니다.")
        
        print("\n5️⃣ 최종 통계")
        print("-" * 40)
        
        # 최종 서버 통계
        final_stats = a2a_node.get_server_stats()
        for name, stat in final_stats.items():
            print(f"📊 {name}:")
            print(f"   - 상태: {'실행 중' if stat['running'] else '중지됨'}")
            print(f"   - 수신 메시지: {stat['messages_received']}개")
        
        print("\n🎉 A2A 시스템 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        print("\n🧹 시스템 정리 중...")
        await a2a_node.cleanup()


async def main():
    """메인 함수"""
    print("🎯 A2A 시스템 통합 테스트")
    print("로컬 서버 실행부터 에이전트 간 통신까지 전체 시스템을 테스트합니다.\n")
    
    success = await test_a2a_system()
    
    print("\n" + "="*50)
    if success:
        print("✅ 모든 테스트 성공!")
        print("💡 A2A 시스템이 정상적으로 작동하고 있습니다!")
    else:
        print("❌ 테스트 실패")
    
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
