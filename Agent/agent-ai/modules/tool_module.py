from typing import Dict, Any, List
import asyncio
from concurrent.futures import ThreadPoolExecutor
from .a2a_manager import get_a2a_manager

class ToolNode:
    def __init__(self, agent_core):
        self.agent_core = agent_core
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """도구 실행 노드 처리 로직 - LLM tool_calls 처리"""
        messages = state.get("messages", [])
        results = []
        
        if not messages:
            return {"tool_results": results}
        
        last_message = messages[-1]
        
        # LLM이 생성한 tool_calls 확인 (duck typing으로 안전하게)
        tool_calls = getattr(last_message, "tool_calls", None)
        
        if tool_calls:
            print(f"🔧 도구 호출 감지: {len(tool_calls)}개")
            
            for call in tool_calls:
                # tool_call 구조: dict 또는 객체
                if isinstance(call, dict):
                    name = call.get("name")
                    args = call.get("args", {})
                else:
                    name = getattr(call, "name", None)
                    args = getattr(call, "args", {})
                
                print(f"  📞 호출: {name} with {args}")
                
                if name == "a2a_send":
                    # A2A 전송 처리
                    result = self._handle_a2a_send(args)
                    results.append({
                        "tool": "a2a_send",
                        "args": args,
                        "result": result
                    })
                    
                else:
                    # 다른 도구들은 향후 추가
                    error_result = f"도구 '{name}'는 아직 구현되지 않았습니다."
                    results.append({
                        "tool": name or "unknown",
                        "args": args,
                        "result": error_result
                    })
        
        return {"tool_results": results}
    
    def _handle_a2a_send(self, args: Dict[str, Any]) -> str:
        """A2A 전송을 처리합니다"""
        agent_name = args.get("agent_name") or args.get("agent")
        text = args.get("text") or args.get("message")
        
        if not agent_name or not text:
            return "오류: agent_name과 text가 필요합니다."
        
        try:
            # 백그라운드 스레드에서 비동기 작업 실행 (이벤트 루프 충돌 방지)
            def run_async():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    manager = get_a2a_manager()
                    return loop.run_until_complete(manager.send(agent_name, text))
                finally:
                    loop.close()
            
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_async)
                response = future.result(timeout=30)  # 30초 타임아웃
                
                if response:
                    return f"✅ '{agent_name}'에게 메시지 전송 완료. 응답: {response}"
                else:
                    return f"⚠️ '{agent_name}'에게 메시지 전송했지만 응답이 없습니다."
                    
        except Exception as e:
            return f"❌ A2A 전송 오류: {str(e)}"

# 향후 도구 관련 클래스들을 여기에 추가할 수 있습니다
# class CalculatorTool:
#     pass
# class SearchTool:
#     pass
