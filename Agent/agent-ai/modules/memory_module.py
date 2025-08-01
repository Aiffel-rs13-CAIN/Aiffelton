import os
import warnings
from typing import Dict, Any, List, Optional
from mem0 import Memory, MemoryClient
from dotenv import load_dotenv

# mem0 라이브러리의 DeprecationWarning 숨기기
warnings.filterwarnings("ignore", category=DeprecationWarning, module="mem0")

load_dotenv()

class MemoryNode:
    def __init__(self, config):
        self.config = config.get('memory', {})
        

        self.memory_type = self.config.get('type', 'in_memory')
        self.default_user_id = self.config.get('default_user_id', 'default_user')
        self.settings = self.config.get('settings', {})
        

        self.search_limit = self.settings.get('search_limit', 5)
        self.history_limit = self.settings.get('history_limit', 50)
        self.auto_save = self.settings.get('auto_save', True)
        self.compression_threshold = self.settings.get('compression_threshold', 1000)
        
        self.memory = None
        if self.memory_type == 'mem0':
            self._initialize_memory()
        
        print(f"🧠 메모리 모듈 초기화 완료:")
        print(f"   - 타입: {self.memory_type}")
        print(f"   - 기본 사용자 ID: {self.default_user_id}")
        print(f"   - 검색 제한: {self.search_limit}")
        print(f"   - 기록 제한: {self.history_limit}")
        print(f"   - 자동 저장: {self.auto_save}")
        print(f"   - 압축 임계값: {self.compression_threshold}")
        
    def _initialize_memory(self):
        try:
            mem0_api_key = os.getenv("MEM0_API_KEY")
            
            if mem0_api_key and mem0_api_key != "your_mem0_api_key_here":
                # 클라우드 mem0 MemoryClient 사용
                print("🌐 mem0 클라우드 서비스에 연결 중...")
                self.memory = MemoryClient(api_key=mem0_api_key)
                print("✅ mem0 클라우드 메모리가 성공적으로 초기화되었습니다.")
            else:
                # 로컬 mem0 Memory 사용
                print("💻 로컬 mem0 메모리 초기화 중...")
                self.memory = Memory()
                print("✅ 로컬 mem0 메모리가 성공적으로 초기화되었습니다.")
                
        except Exception as e:
            print(f"⚠️ mem0 초기화 실패: {e}")
            print("기본 메모리 모드로 실행합니다.")
            self.memory = None
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """메모리 노드 처리 로직"""
        messages = state.get("messages", [])
        
        # mem0 타입이 아니면 기본 처리
        if self.memory_type != 'mem0' or not self.memory:
            return {**state, "memory": {"status": "disabled", "type": self.memory_type}}
        
        # 자동 저장이 비활성화된 경우 저장하지 않음
        if not self.auto_save:
            return {**state, "memory": {"status": "auto_save_disabled"}}
        
        try:
            if messages:
                # 사용자 ID 결정 (state에서 지정된 값 또는 기본값 사용)
                user_id = state.get("user_id", self.default_user_id)
                latest_message = messages[-1]
                content = latest_message.content if hasattr(latest_message, 'content') else str(latest_message)
                
                if content and content.strip():
                    print(f"💾 메모리에 저장 중: [{user_id}] {content[:50]}...")
                    
                    # MemoryClient와 Memory의 API 차이 처리
                    try:
                        if isinstance(self.memory, MemoryClient):
                            # MemoryClient는 messages를 리스트로 기대
                            add_result = self.memory.add(
                                messages=[{"role": "user", "content": content}],
                                user_id=user_id
                            )
                        else:
                            # 기본 Memory는 문자열도 허용
                            add_result = self.memory.add(
                                messages=content,
                                user_id=user_id
                            )
                        print(f"💾 메모리 저장 결과: {add_result}")
                    except Exception as add_error:
                        print(f"⚠️ 메모리 저장 실패: {add_error}")
                        add_result = None
                    
                    # 관련 메모리 검색 (설정된 제한값 사용)
                    search_result = self.memory.search(
                        query=content, 
                        user_id=user_id,
                        limit=self.search_limit
                    )
                    
                    # mem0 검색 결과가 딕셔너리 형태일 경우 리스트로 변환
                    if isinstance(search_result, dict) and 'results' in search_result:
                        related_memories = search_result['results']
                    elif isinstance(search_result, list):
                        related_memories = search_result
                    else:
                        related_memories = []
                    
                    print(f"🔍 관련 메모리 검색 결과: {len(related_memories)}개")
                    
                    return {
                        **state,  # 기존 상태 유지
                        "memory": {
                            "status": "active",
                            "related_memories": related_memories,
                            "user_id": user_id
                        }
                    }
            
            return {**state, "memory": {"status": "no_messages"}}
            
        except Exception as e:
            print(f"⚠️ 메모리 처리 중 오류: {e}")
            return {**state, "memory": {"status": "error", "error": str(e)}}

    def get_conversation_history(self, user_id: Optional[str] = None, limit: Optional[int] = None) -> List[Dict]:
        """대화 기록 조회"""
        if not self.memory:
            return []
        
        # 사용자 ID와 제한값 설정
        user_id = user_id or self.default_user_id
        limit = limit or self.history_limit
        
        try:
            return self.memory.get_all(user_id=user_id, limit=limit)
        except Exception as e:
            print(f"⚠️ 대화 기록 조회 중 오류: {e}")
            return []
    
    def clear_memory(self, user_id: Optional[str] = None) -> bool:
        """특정 사용자의 메모리 삭제"""
        if not self.memory:
            return False
        
        user_id = user_id or self.default_user_id
        
        try:
            memories = self.memory.get_all(user_id=user_id)
            for memory in memories:
                if 'id' in memory:
                    self.memory.delete(memory['id'])
            print(f"🗑️ 사용자 '{user_id}'의 메모리가 삭제되었습니다.")
            return True
        except Exception as e:
            print(f"⚠️ 메모리 삭제 중 오류: {e}")
            return False

    def get_memory_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """메모리 통계 정보 반환"""
        if not self.memory:
            return {"status": "disabled"}
        
        user_id = user_id or self.default_user_id
        
        try:
            memories = self.memory.get_all(user_id=user_id)
            memory_count = len(memories)
            
            return {
                "user_id": user_id,
                "memory_count": memory_count,
                "compression_needed": memory_count > self.compression_threshold,
                "settings": {
                    "search_limit": self.search_limit,
                    "history_limit": self.history_limit,
                    "auto_save": self.auto_save,
                    "compression_threshold": self.compression_threshold
                }
            }
        except Exception as e:
            print(f"⚠️ 메모리 통계 조회 중 오류: {e}")
            return {"status": "error", "error": str(e)}

    def compress_memory(self, user_id: Optional[str] = None) -> bool:
        """메모리 압축 (오래된 메모리 정리)"""
        if not self.memory:
            return False
        
        user_id = user_id or self.default_user_id
        
        try:
            memories = self.memory.get_all(user_id=user_id)
            
            if len(memories) <= self.compression_threshold:
                print(f"📊 압축이 필요하지 않습니다. 현재 메모리 수: {len(memories)}")
                return True
            
            # 오래된 메모리의 절반을 삭제
            memories_to_delete = memories[self.compression_threshold//2:]
            
            for memory in memories_to_delete:
                if 'id' in memory:
                    self.memory.delete(memory['id'])
            
            print(f"🗜️ 메모리 압축 완료: {len(memories_to_delete)}개 삭제")
            return True
            
        except Exception as e:
            print(f"⚠️ 메모리 압축 중 오류: {e}")
            return False