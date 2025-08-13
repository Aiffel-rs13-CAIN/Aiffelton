"""
A2A 클라이언트 모듈
- a2a_core.a2a_client.A2AClientAgent를 래핑하여 필요할 때만 초기화/사용.

핵심 API
- A2AClientModule.initialize(config_dir, except_file): 서버 카드 사전 로드(옵셔널)
- A2AClientModule.send(agent_name, text): 메시지 전송(필요 시 지연 초기화 포함)
- A2AClientModule.close(): 정리
"""
from __future__ import annotations

import asyncio
from typing import Optional, List

import httpx

from .a2a_core.a2a_client import A2AClientAgent
from .a2a_core.config_loader import get_server_list


class A2AClientModule:
	def __init__(self) -> None:
		self._client: Optional[A2AClientAgent] = None
		self._httpx: Optional[httpx.AsyncClient] = None
		self._entries = None

	@property
	def ready(self) -> bool:
		return self._client is not None

	async def initialize(self, config_dir: str, except_file: str | None = None) -> None:
		"""원격 에이전트 목록을 불러와 A2AClientAgent를 준비.

		except_file는 자신의 서버 설정 파일명(있다면)으로, 목록에서 제외.
		"""
		self._entries = get_server_list(config_dir, except_file)
		if not self._entries:
			print("ℹ️ 원격 서버 엔트리가 없어도 클라이언트는 지연 초기화로 동작합니다.")

		self._httpx = httpx.AsyncClient()
		self._client = A2AClientAgent(remote_agent_entries=self._entries or [], http_client=self._httpx)

	async def ensure_initialized(self, config_dir: str, except_file: str | None = None) -> None:
		if not self.ready:
			await self.initialize(config_dir, except_file)

	async def send(self, agent_name: str, text: str, *, config_dir: str, except_file: str | None = None) -> Optional[List[str]]:
		"""원격 에이전트로 메시지 전송. 필요 시 즉시 초기화.

		Returns: List[str] | None
		"""
		await self.ensure_initialized(config_dir, except_file)

		try:
			response = await self._client.send_message(agent_name, text, task_id=None, context_id=None)
			if response:
				return [str(p) for p in response]
			return None
		except Exception as e:
			print(f"❌ 전송 실패: {e}")
			return None

	async def close(self) -> None:
		if self._client:
			await self._client.close()
		if self._httpx:
			await self._httpx.aclose()
		self._client = None
		self._httpx = None

	# 내부 클라이언트에 접근(서버와 선택적 연동용)
	@property
	def client_agent(self) -> Optional[A2AClientAgent]:
		return self._client


# 편의 함수
async def create_client(config_dir: str, except_file: str | None = None) -> A2AClientModule:
	cli = A2AClientModule()
	await cli.initialize(config_dir, except_file)
	return cli

