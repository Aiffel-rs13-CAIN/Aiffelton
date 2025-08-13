"""
A2A Helper
- 워크플로우 노드에서 쉽게 A2A 클라이언트를 사용할 수 있도록 도우미 제공
- 무거운 의존성(a2a 패키지 등)은 런타임까지 지연 로드
"""
from __future__ import annotations

import asyncio
from typing import Optional, List, TYPE_CHECKING, Any

if TYPE_CHECKING:
    # 타입 체크에서만 임포트하여 런타임 임포트 비용을 제거
    from .a2a_client_module import A2AClientModule
    from .a2a_core.a2a_client import A2AClientAgent

_client_module: Optional["A2AClientModule"] = None
_client_agent: Optional["A2AClientAgent"] = None


def set_client_module(mod: "A2AClientModule") -> None:
    global _client_module
    _client_module = mod


def set_client_agent(agent: "A2AClientAgent") -> None:
    global _client_agent
    _client_agent = agent


async def send_async(agent_name: str, text: str, *, config_dir: str, except_file: str | None = None) -> Optional[List[str]]:
    """A2A 메시지를 비동기로 전송"""
    if _client_module is not None:
        return await _client_module.send(agent_name, text, config_dir=config_dir, except_file=except_file)
    if _client_agent is not None:
        # 직접 A2AClientAgent 사용
        try:
            resp = await _client_agent.send_message(agent_name, text, task_id=None, context_id=None)
            if resp:
                return [str(p) for p in resp]
            return None
        except Exception as e:
            print(f"❌ 전송 실패: {e}")
            return None
    print("ℹ️ A2A 클라이언트가 설정되지 않았습니다.")
    return None


def send_blocking(agent_name: str, text: str, *, config_dir: str, except_file: str | None = None) -> Optional[List[str]]:
    """동기 컨텍스트에서 간단히 호출하기 위한 블로킹 전송 함수"""
    coro = send_async(agent_name, text, config_dir=config_dir, except_file=except_file)
    try:
        return asyncio.run(coro)
    except RuntimeError:
        # 이미 루프가 도는 환경이면 새 루프에서 실행
        import threading

        result_holder: dict = {"val": None}

        def _runner():
            result_holder["val"] = asyncio.run(coro)

        t = threading.Thread(target=_runner, daemon=True)
        t.start()
        t.join()
        return result_holder["val"]
