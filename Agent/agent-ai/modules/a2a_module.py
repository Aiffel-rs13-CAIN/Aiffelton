"""
A2A 통신 모듈
기존 a2a_core를 활용한 간단한 A2A 노드 + 서버 실행 기능
"""
import asyncio
import httpx
import json
import threading
import time
from typing import Dict, Any, List, Optional
from uuid import uuid4
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import socket

from .a2a_core.a2a_client import A2AClientAgent
from .a2a_core.config_loader import get_server_list


class SimpleA2AServer:
    """간단한 A2A 서버 구현"""
    
    def __init__(self, name: str, port: int, personality: str = ""):
        self.name = name
        self.port = port
        self.personality = personality
        self.server = None
        self.server_thread = None
        self.is_running = False
        self.messages_received = []
        
        # 에이전트 카드 정보
        self.agent_card = {
            "name": name,
            "description": f"{name} - {personality}",
            "version": "1.0.0",
            "capabilities": [
                {
                    "name": "chat",
                    "description": "Chat with the agent",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string"}
                        },
                        "required": ["message"]
                    }
                }
            ],
            "endpoints": {
                "chat": f"http://localhost:{port}/chat"
            },
            "protocols": ["a2a-v1"],
            "transport": "http"
        }
    
    def create_request_handler(self):
        """HTTP 요청 핸들러 생성"""
        server_instance = self
        
        class A2ARequestHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                # 로그 출력 억제
                pass
            
            def do_GET(self):
                """GET 요청 처리"""
                try:
                    parsed_path = urlparse(self.path)
                    
                    if parsed_path.path == "/.well-known/agent-card.json":
                        # 에이전트 카드 반환
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json; charset=utf-8')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.send_header('Cache-Control', 'no-cache')
                        self.end_headers()
                        
                        agent_card_json = json.dumps(server_instance.agent_card, indent=2, ensure_ascii=False)
                        self.wfile.write(agent_card_json.encode('utf-8'))
                        
                        print(f"📋 [{server_instance.name}] 에이전트 카드 전송됨")
                    
                    elif parsed_path.path == "/health":
                        # 헬스 체크
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json; charset=utf-8')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        
                        health_data = {
                            "status": "healthy",
                            "agent": server_instance.name,
                            "port": server_instance.port,
                            "timestamp": time.time()
                        }
                        self.wfile.write(json.dumps(health_data).encode('utf-8'))
                    
                    elif parsed_path.path == "/":
                        # 루트 경로 - 간단한 정보 페이지
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/html; charset=utf-8')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        
                        html_content = f"""
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <title>{server_instance.name} A2A Server</title>
                            <meta charset="utf-8">
                        </head>
                        <body>
                            <h1>{server_instance.name}</h1>
                            <p>A2A 프로토콜 서버가 실행 중입니다.</p>
                            <h2>사용 가능한 엔드포인트:</h2>
                            <ul>
                                <li><a href="/health">Health Check</a></li>
                                <li><a href="/.well-known/agent-card.json">Agent Card</a></li>
                                <li>POST /chat - 채팅 메시지</li>
                            </ul>
                            <p><strong>성격:</strong> {server_instance.personality}</p>
                            <p><strong>수신 메시지:</strong> {len(server_instance.messages_received)}개</p>
                        </body>
                        </html>
                        """
                        self.wfile.write(html_content.encode('utf-8'))
                    
                    else:
                        self.send_response(404)
                        self.send_header('Content-Type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        error_data = {"error": "Not found", "path": self.path}
                        self.wfile.write(json.dumps(error_data).encode())
                        
                except Exception as e:
                    print(f"❌ GET 요청 처리 오류: {e}")
                    self.send_response(500)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    error_data = {"error": f"서버 오류: {str(e)}"}
                    self.wfile.write(json.dumps(error_data).encode())
            
            def do_POST(self):
                """POST 요청 처리 (A2A 메시지)"""
                parsed_path = urlparse(self.path)
                
                if parsed_path.path == "/chat":
                    # 채팅 엔드포인트 (A2A 표준)
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    
                    try:
                        message_data = json.loads(post_data.decode())
                        response = server_instance.process_chat_message(message_data)
                        
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps(response).encode())
                        
                    except Exception as e:
                        print(f"❌ 채팅 메시지 처리 오류: {e}")
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        error_response = {"error": str(e)}
                        self.wfile.write(json.dumps(error_response).encode())
                        
                elif parsed_path.path.startswith("/a2a/"):
                    # A2A 메시지 처리
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    
                    try:
                        message_data = json.loads(post_data.decode())
                        response = server_instance.process_a2a_message(message_data)
                        
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps(response).encode())
                        
                    except Exception as e:
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        error_response = {"error": str(e)}
                        self.wfile.write(json.dumps(error_response).encode())
                
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def do_OPTIONS(self):
                """CORS preflight 처리"""
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()
        
        return A2ARequestHandler
    
    def process_chat_message(self, message_data: dict) -> dict:
        """채팅 메시지 처리 (A2A 표준 엔드포인트)"""
        try:
            message = message_data.get("message", "")
            sender = message_data.get("sender", "Unknown")
            
            print(f"💬 [{self.name}] 채팅 메시지 수신: '{message}' (발신자: {sender})")
            
            # 메시지 저장
            self.messages_received.append({
                "sender": sender,
                "message": message,
                "timestamp": time.time(),
                "type": "chat"
            })
            
            # 간단한 응답 생성
            if "안녕" in message or "hello" in message.lower():
                response_text = f"안녕하세요! 저는 {self.name}입니다. {self.personality}"
            elif "창의" in message or "creative" in message.lower():
                response_text = f"{self.personality} 관점에서 창의성에 대해 말씀드리면, 저는 이것이 매우 흥미로운 주제라고 생각합니다."
            elif "AI" in message or "인공지능" in message:
                response_text = f"AI에 대한 질문이군요! {self.personality}으로서 이에 대해 깊이 생각해볼 가치가 있다고 봅니다."
            else:
                response_text = f"흥미로운 말씀이네요. {self.personality}으로서 이에 대해 더 자세히 알고 싶습니다."
            
            return {
                "message": response_text,
                "sender": self.name,
                "timestamp": time.time()
            }
            
        except Exception as e:
            print(f"❌ 채팅 메시지 처리 오류: {e}")
            return {
                "error": f"메시지 처리 실패: {str(e)}",
                "sender": self.name
            }

    def process_a2a_message(self, message_data: dict) -> dict:
        """A2A 메시지 처리"""
        try:
            message = message_data.get("message", "")
            sender = message_data.get("sender", "Unknown")
            
            print(f"📥 {self.name}이 메시지 수신: {message[:50]}...")
            
            # 메시지 저장
            self.messages_received.append({
                "sender": sender,
                "message": message,
                "timestamp": time.time()
            })
            
            # 간단한 응답 생성 (실제로는 LLM 사용)
            if "안녕" in message or "hello" in message.lower():
                response_text = f"안녕하세요! 저는 {self.name}입니다. {self.personality}"
            elif "창의" in message or "creative" in message.lower():
                response_text = f"{self.personality} 관점에서 창의성에 대해 말씀드리면, 저는 이것이 매우 흥미로운 주제라고 생각합니다."
            elif "AI" in message or "인공지능" in message:
                response_text = f"AI에 대한 질문이군요! {self.personality}으로서 이에 대해 깊이 생각해볼 가치가 있다고 봅니다."
            else:
                response_text = f"흥미로운 말씀이네요. {self.personality}으로서 이에 대해 더 자세히 알고 싶습니다."
            
            return {
                "response": response_text,
                "agent": self.name,
                "timestamp": time.time(),
                "message_id": str(uuid4())
            }
            
        except Exception as e:
            return {
                "error": f"메시지 처리 실패: {str(e)}",
                "agent": self.name
            }
    
    def start_server(self):
        """서버 시작"""
        try:
            handler_class = self.create_request_handler()
            self.server = HTTPServer(('localhost', self.port), handler_class)
            
            print(f"🚀 {self.name} 서버 시작: http://localhost:{self.port}")
            
            self.is_running = True
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            
            return True
            
        except Exception as e:
            print(f"❌ {self.name} 서버 시작 실패: {e}")
            return False
    
    def stop_server(self):
        """서버 중지"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.is_running = False
            print(f"🛑 {self.name} 서버 중지됨")
    
    def get_stats(self):
        """서버 통계"""
        return {
            "name": self.name,
            "port": self.port,
            "running": self.is_running,
            "messages_received": len(self.messages_received),
            "last_message": self.messages_received[-1] if self.messages_received else None
        }


class A2AServerManager:
    """A2A 서버들을 관리하는 클래스"""
    
    def __init__(self):
        self.servers = {}
    
    def create_server(self, name: str, port: int, personality: str = "") -> SimpleA2AServer:
        """새 A2A 서버 생성"""
        server = SimpleA2AServer(name, port, personality)
        self.servers[name] = server
        return server
    
    def start_all_servers(self):
        success_count = 0
        for name, server in self.servers.items():
            if server.start_server():
                success_count += 1
        
        print(f"✅ {success_count}/{len(self.servers)}개 서버 시작 완료")
        return success_count == len(self.servers)
    
    def stop_all_servers(self):
        for server in self.servers.values():
            server.stop_server()
        print("🛑 모든 A2A 서버 중지됨")
    
    def get_all_stats(self):
        return {name: server.get_stats() for name, server in self.servers.items()}
    
    def is_port_available(self, port: int) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return True
        except OSError:
            return False


class A2ANode:
    def __init__(self, config: Dict[str, Any] = None):
        """
        A2A 노드 초기화
        
        Args:
            config: A2A 설정 딕셔너리
        """
        # A2A 설정
        self.a2a_config_dir = "config/a2a"
        self.httpx_client = None
        self.a2a_client = None
        self.remote_agents = {}
        self.initialized = False
        
        # 서버 관리
        self.server_manager = A2AServerManager()
        self.auto_start_servers = config.get("auto_start_servers", False) if config else False
        
        print("🤖 A2A 노드 생성됨 (서버 관리 기능 포함)")
    
    async def initialize(self, start_local_servers: bool = False):
        """
        A2A 클라이언트 초기화
        
        Args:
            start_local_servers: 로컬 A2A 서버들을 자동으로 시작할지 여부
        """
        try:
            print("🔧 A2A 통신 모듈 초기화 시작...")
            
            # 로컬 서버 시작 (요청된 경우)
            if start_local_servers or self.auto_start_servers:
                await self.start_local_servers()
                # 서버 시작 후 충분히 대기
                print("⏳ 서버 준비 대기 중...")
                await asyncio.sleep(5)
            
            # HTTP 클라이언트 생성
            self.httpx_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
            
            # A2A 서버 목록 로드
            a2a_server_entries = get_server_list(self.a2a_config_dir)
            
            if not a2a_server_entries:
                print("⚠️ A2A 서버 목록이 비어있습니다.")
                # 로컬 서버가 있다면 그것만 사용
                if self.server_manager.servers:
                    print("✅ 로컬 서버만 사용하여 초기화 완료")
                    self.initialized = True
                    return
                else:
                    print("❌ 사용 가능한 서버가 없습니다.")
                    return
            
            try:
                # A2A 클라이언트 에이전트 초기화
                self.a2a_client = A2AClientAgent(
                    a2a_server_entries, 
                    self.httpx_client, 
                    None
                )
                
                # 원격 에이전트 연결 시도 - 예외 처리 추가
                try:
                    # 원격 에이전트 연결 완료 대기
                    await asyncio.sleep(2)
                    
                    # 사용 가능한 에이전트 목록 저장
                    self.remote_agents = {
                        agent["name"]: agent 
                        for agent in self.a2a_client.list_remote_agents()
                    }
                    
                    print(f"✅ 원격 A2A 에이전트 연결 완료: {len(self.remote_agents)}개")
                    
                except Exception as remote_error:
                    print(f"⚠️ 원격 에이전트 연결 실패: {remote_error}")
                    print("📝 로컬 서버만 사용합니다.")
                    self.remote_agents = {}
                
            except Exception as client_error:
                print(f"⚠️ A2A 클라이언트 초기화 실패: {client_error}")
                print("📝 로컬 서버만 사용합니다.")
                self.a2a_client = None
                self.remote_agents = {}
            
            self.initialized = True
            total_agents = len(self.remote_agents) + len(self.server_manager.servers)
            print(f"✅ A2A 통신 모듈 초기화 완료. 총 에이전트: {total_agents}개")
            
            # 서버 목록 출력
            if self.server_manager.servers:
                print("✅ 서버 목록:")
                for name, server in self.server_manager.servers.items():
                    if server.is_running:
                        print(f"A2A Server {name} : http://localhost:{server.port}/")
            
        except Exception as e:
            print(f"❌ A2A 통신 모듈 초기화 실패: {e}")
            import traceback
            traceback.print_exc()
            self.initialized = False
    
    async def start_local_servers(self):
        """로컬 A2A 서버들 시작"""
        print("🚀 로컬 A2A 서버들 시작 중...")
        
        # 기본 A2A 서버들 생성
        servers_config = [
            {
                "name": "Summarize Agent",
                "port": 10000,
                "personality": "간결하고 명확한 요약을 제공하는 AI입니다"
            },
            {
                "name": "Recorder Agent", 
                "port": 10001,
                "personality": "대화와 정보를 체계적으로 기록하는 AI입니다"
            }
        ]
        
        for server_config in servers_config:
            # 포트 사용 가능 여부 확인
            if not self.server_manager.is_port_available(server_config["port"]):
                print(f"⚠️ 포트 {server_config['port']}가 이미 사용 중입니다. {server_config['name']} 건너뜀")
                continue
            
            # 서버 생성
            server = self.server_manager.create_server(
                server_config["name"],
                server_config["port"], 
                server_config["personality"]
            )
        
        # 모든 서버 시작
        success = self.server_manager.start_all_servers()
        
        if success:
            print("✅ 모든 로컬 A2A 서버 시작 완료")
        else:
            print("⚠️ 일부 A2A 서버 시작 실패")
        
        return success
    
    async def cleanup(self):
        """리소스 정리"""
        # HTTP 클라이언트 정리
        if self.httpx_client:
            await self.httpx_client.aclose()
        
        # 로컬 서버들 중지
        self.server_manager.stop_all_servers()
        
        print("🧹 A2A 통신 모듈 정리 완료")
    
    def get_server_stats(self):
        """서버 통계 조회"""
        return self.server_manager.get_all_stats()
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        A2A 통신 처리
        
        Args:
            state: 워크플로우 상태
            
        Returns:
            Dict[str, Any]: 업데이트된 상태
        """
        if not self.initialized:
            print("⚠️ A2A 모듈이 초기화되지 않았습니다.")
            return state
        
        # A2A 통신이 필요한 경우 처리
        a2a_request = state.get("a2a_request")
        
        if a2a_request:
            print(f"🤖 A2A 요청 처리: {a2a_request.get('agent_name')}")
            
            # 여기서는 동기 함수이므로 실제 전송은 하지 않고 상태만 업데이트
            agent_name = a2a_request.get("agent_name")
            message = a2a_request.get("message")
            
            if agent_name in self.remote_agents:
                # 실제로는 여기서 비동기 전송을 해야 하지만, 
                # process는 동기 함수이므로 간단히 상태만 업데이트
                state["a2a_response"] = [f"A2A 요청이 {agent_name}에게 전송됨: {message[:50]}..."]
                print(f"✅ A2A 요청 상태 업데이트 완료")
            else:
                print(f"❌ 에이전트를 찾을 수 없음: {agent_name}")
                state["a2a_response"] = [f"에이전트 '{agent_name}'을 찾을 수 없습니다."]
        
        return state
    
    async def send_message(self, agent_name: str, message: str) -> Optional[List[str]]:
        """
        실제 A2A 메시지 전송 (비동기) - 원격 및 로컬 서버 지원
        
        Args:
            agent_name: 대상 에이전트 이름 (로컬 서버는 "Agent Name (Local)" 형식)
            message: 전송할 메시지
            
        Returns:
            Optional[List[str]]: 응답 메시지 리스트
        """
        if not self.initialized:
            print("❌ A2A 모듈이 초기화되지 않았습니다.")
            return None
        
        try:
            # 로컬 서버인지 확인
            if agent_name.endswith(" (Local)"):
                # 로컬 서버 처리
                local_name = agent_name.replace(" (Local)", "")
                
                if local_name in self.server_manager.servers:
                    server = self.server_manager.servers[local_name]
                    
                    if server.is_running:
                        print(f"📤 로컬 서버 {local_name}에게 메시지 전송: {message[:50]}...")
                        
                        # 로컬 서버에 직접 메시지 전송
                        message_data = {
                            "message": message,
                            "sender": "A2A_Client"
                        }
                        
                        response = server.process_chat_message(message_data)
                        
                        if response and "message" in response:
                            print(f"✅ 로컬 서버 응답 수신: {local_name}")
                            return [response["message"]]
                        else:
                            print(f"⚠️ 로컬 서버 응답 없음: {local_name}")
                            return None
                    else:
                        print(f"❌ 로컬 서버가 실행되지 않음: {local_name}")
                        return None
                else:
                    print(f"❌ 로컬 서버를 찾을 수 없음: {local_name}")
                    return None
            
            else:
                # 원격 A2A 에이전트 처리
                if agent_name not in self.remote_agents:
                    print(f"❌ 원격 에이전트 '{agent_name}'을 찾을 수 없습니다.")
                    return None
                
                if not self.a2a_client:
                    print("❌ A2A 클라이언트가 초기화되지 않았습니다.")
                    return None
                
                # 실제 A2A 메시지 전송
                response = await self.a2a_client.send_message(
                    agent_name, 
                    message, 
                    task_id=str(uuid4()), 
                    context_id=str(uuid4())
                )
                
                if response:
                    print(f"✅ A2A 메시지 전송 성공: {agent_name}")
                    return response
                else:
                    print(f"⚠️ A2A 응답이 없습니다: {agent_name}")
                    return None
                
        except Exception as e:
            print(f"❌ 메시지 전송 실패: {e}")
            return None
    
    def get_available_agents(self) -> List[str]:
        """사용 가능한 원격 에이전트 및 로컬 서버 목록 반환"""
        agents = []
        
        # 원격 A2A 에이전트 추가
        if self.remote_agents:
            agents.extend(list(self.remote_agents.keys()))
        
        # 로컬 서버 추가
        if self.server_manager.servers:
            for name, server in self.server_manager.servers.items():
                if server.is_running:
                    agents.append(f"{name} (Local)")
        
        return agents
    
    def is_ready(self) -> bool:
        """A2A 모듈 준비 상태 확인"""
        return self.initialized
