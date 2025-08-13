from typing import Dict, Any

class OutputNode:
    def __init__(self, config):
        self.config = config
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        messages = state.get("messages", [])
        tool_results = state.get("tool_results", [])
        
        # 도구 결과가 있으면 먼저 출력
        if tool_results:
            print("🔧 도구 실행 결과:")
            for result in tool_results:
                tool_name = result.get("tool", "unknown")
                tool_result = result.get("result", "결과 없음")
                print(f"  - {tool_name}: {tool_result}")
            print()
        
        # 일반 메시지 출력
        if messages:
            last_message = messages[-1]
            # AI 메시지인 경우 출력
            if hasattr(last_message, 'content') and last_message.content:
                print(f"에이전트: {last_message.content}")
            elif hasattr(last_message, 'content'):
                # tool_calls만 있고 content가 없는 경우
                if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                    if not tool_results:  # 도구 결과가 없다면 처리 중 메시지
                        print("에이전트: 요청을 처리하고 있습니다...")
                else:
                    print(f"에이전트: {str(last_message)}")
        
        # 출력 완료 후 다음 사용자 입력을 위해 should_exit을 False로 설정
        # 단, 명시적으로 종료 요청이 있었다면 유지
        explicit_exit = state.get("should_exit", False)
        
        return {
            **state,
            "should_exit": explicit_exit,
            # tool_results 초기화 (한 번 출력 후 제거)
            "tool_results": []
        }
