"""
A2A 서버 모듈
- server_executor.py/server_factory.py를 활용해 에이전트 서버(ASGI 앱)를 실행/중지.
- uvicorn으로 비동기 백그라운드 실행 지원.

핵심 API
- A2AServerModule.start(config_path): 지정 JSON 설정으로 서버 실행
- A2AServerModule.stop(): 서버 중지
- A2AServerModule.is_running: 실행 상태
- A2AServerModule.start_by_name(name, config_dir): 이름으로 설정 선택 후 실행
"""
from __future__ import annotations

import os
import json
import threading
from typing import Optional

import uvicorn

from .a2a_core.server_factory import build_server_from_config
from .a2a_core.config_loader import load_a2a_config
from .a2a_core import server_executor as _server_executor_mod


class A2AServerModule:
	"""A2A 서버 실행기(래퍼)"""

	def __init__(self):
		self._server: Optional[uvicorn.Server] = None
		self._thread: Optional[threading.Thread] = None
		self._app = None
		self._host: Optional[str] = None
		self._port: Optional[int] = None
		self._config_path: Optional[str] = None

	@property
	def is_running(self) -> bool:
		if not self._server:
			return False
		if getattr(self._server, "should_exit", False):
			return False
		started = getattr(self._server, "started", None)
		if started is None:
			# Fallback: thread alive indicates running
			return bool(self._thread and self._thread.is_alive())
		# started may be an Event or a bool
		if hasattr(started, "is_set"):
			return started.is_set()
		return bool(started)

	def start(self, config_path: str) -> bool:
		"""주어진 설정(JSON)으로 A2A 서버 시작.

		Args:
			config_path: config/a2a/*.json 같은 서버 설정 파일 경로

		Returns:
			bool: 성공 여부
		"""
		if self.is_running:
			print("⚠️ 서버가 이미 실행 중입니다.")
			return True

		if not os.path.isfile(config_path):
			print(f"❌ 설정 파일을 찾을 수 없습니다: {config_path}")
			return False

		try:
			server_config, app = build_server_from_config(config_path)
			host = server_config.get("host", "127.0.0.1")
			port = int(server_config.get("port", 8000))

			config = uvicorn.Config(app, host=host, port=port, log_level="info")
			server = uvicorn.Server(config)

			def _run():
				server.run()

			th = threading.Thread(target=_run, daemon=True)
			th.start()

			self._server = server
			self._thread = th
			self._app = app
			self._host = host
			self._port = port
			self._config_path = config_path

			print(f"🚀 A2A 서버 시작: http://{host}:{port} (config: {os.path.basename(config_path)})")
			return True
		except Exception as e:
			print(f"❌ 서버 시작 실패: {e}")
			return False

	def start_by_name(self, name: str, config_dir: str) -> bool:
		"""설정 디렉터리에서 name이 일치하는 JSON을 찾아 서버 실행.

		name은 설정 파일의 "name" 필드를 의미합니다.
		"""
		if not os.path.isdir(config_dir):
			print(f"❌ 디렉터리를 찾을 수 없습니다: {config_dir}")
			return False

		for fname in os.listdir(config_dir):
			if not fname.endswith(".json"):
				continue
			fpath = os.path.join(config_dir, fname)
			try:
				cfg = load_a2a_config(fpath)
				if cfg.get("name") == name:
					return self.start(fpath)
			except Exception as e:
				print(f"⚠️ 설정 로드 실패({fname}): {e}")

		print(f"❌ name='{name}' 설정을 찾지 못했습니다. ({config_dir})")
		return False

	def stop(self) -> None:
		"""서버 중지"""
		if not self._server:
			print("ℹ️ 실행 중인 서버가 없습니다.")
			return

		try:
			self._server.should_exit = True
			if self._thread and self._thread.is_alive():
				self._thread.join(timeout=5)
			print("🛑 A2A 서버 중지 완료")
		finally:
			self._server = None
			self._thread = None
			self._app = None
			self._host = None
			self._port = None
			self._config_path = None

	def attach_client_agent(self, client_agent) -> None:
		"""A2AServerAgentExecutor가 사용하는 글로벌 클라이언트를 주입.

		Args:
			client_agent: a2a_core.a2a_client.A2AClientAgent 인스턴스
		"""
		_server_executor_mod.a2a_client = client_agent
		print("🔗 서버에 A2A 클라이언트 에이전트가 연결되었습니다.")

# 편의 함수
def run_server(config_path: str) -> A2AServerModule:
	mod = A2AServerModule()
	ok = mod.start(config_path)
	if not ok:
		raise RuntimeError("A2A 서버 실행 실패")
	return mod

