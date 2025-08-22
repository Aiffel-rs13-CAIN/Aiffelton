import os
import asyncio
import json
from datetime import datetime
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.utils import (
    new_agent_text_message,
    new_task,
)
from a2a.types import (
    AgentCard,
    JSONRPCErrorResponse,
    Message,
    MessageSendParams,
    MessageSendConfiguration,
    SendMessageRequest,
    SendStreamingMessageRequest,
    Task,
    TaskState,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
    DataPart,
    Part,
    TextPart,
)
import uuid
from uuid import uuid4

from .a2a_client import A2AClientAgent
from .a2a_client import A2AServerEntry
from dataclasses import dataclass
from typing import TypedDict, Optional

# Agent LLM Handler 임포트
try:
    from ..agent_llm_handler import get_agent_llm_handler
    LLM_AVAILABLE = True
except ImportError:
    print("⚠️ Agent LLM Handler를 사용할 수 없습니다. 기본 응답을 사용합니다.")
    LLM_AVAILABLE = False

a2a_client : Optional[A2AClientAgent] = None 

@dataclass
class LLMResponse:
    response: str
    is_complete: bool
    error_occur: bool
    error_message: Optional[str] = None
class SimpleStateManager:
    ''' Context 단위로 State를 관리한다 '''
    def __init__(self):
        self.states = {}
    
    def get_state(self, context_id: str):           
        return self.states.get(context_id, {})
    
    def update_state(self, context_id: str, data: dict):  
        if context_id not in self.states:
            self.states[context_id] = {}
        self.states[context_id].update(data)
    
    def set_response(self, context_id: str, response: str):  
        self.update_state(context_id, {"response": response})


class A2AServerAgentExecutor(AgentExecutor):

    def __init__(self, remote_agent_entries: list[A2AServerEntry], agent_name: str = None, **kwargs):
        # 에이전트 이름 저장
        self.agent_name = agent_name or "Unknown Agent"
        self.remote_agent_entries = remote_agent_entries
        # BEGIN - 2025.08.22 task state 관리 {
        self.state_manager = SimpleStateManager() 
        # END - 2025.08.22 task state관리 }
        print(f"🤖 {self.agent_name} 실행기 초기화 완료")

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:

        rcvRequest = context._params
        print("Request :", rcvRequest.model_dump(mode='json', exclude_none=False))
        print()
        
        # 1. 사용자 입력 메시지 받기
        text = context.get_user_input()
        task = context.current_task
        print(f"📨 수신된 메시지: {text}")
        
        # 2. 에이전트 이름 확인
        agent_name = self.agent_name
        print(f"🤖 에이전트: {agent_name}")

        # BEGIN - 2025.08.20 task 관리 {
        if not task : 
            task = new_task(context.message)            
            await event_queue.enqueue_event(task)  # task 전송       
        
        updater = TaskUpdater(event_queue, task.id, task.context_id)
        # END - 2025.08.20 task 관리 }

        # BEGIN - 2025.08.22 task state 관리 {
        current_state = self.state_manager.get_state(task.id)
        # 별도 state 관리를 하려면, 사용
        # if not current_state 
        # END - 2025.08.22 task state관리 }

        
        # 3. LLM으로 응답 생성
        result = await self._generate_llm_response(agent_name, text)
        if not result.error_occur : 
            response_text = result.response

            self.state_manager.set_response(task.id, response_text)
    
            # 4. 특별한 처리 (에이전트별 로직)
            await self._handle_agent_specific_logic(agent_name, text, response_text)

            if result.is_complete : 
                # 성공적으로 완료된 경우 - artifact로 결과 전송
                part = TextPart(text=response_text)
                await updater.add_artifact(
                    parts = [Part(root=part)],
                    name = f'{agent_name}-result'
                )
                await updater.complete()
                print(f"📤 응답 전송 완료: {response_text[:100]}...")

            else : 
                # 부분 완료 - working 상태로 중간 결과 전송
                await updater.update_status(
                    TaskState.working,
                    new_agent_text_message(
                        response_text,
                        task.context_id,
                        task.id,
                    ),
                )
                print(f"📤 중간 응답 전송: {response_text[:100]}...")
        else :
            # 에러 발생 - TaskState.failed로 실패 처리
            error_text = result.error_message or "알 수 없는 오류가 발생했습니다."
            await updater.update_status(
                    TaskState.failed,
                    new_agent_text_message(
                        error_text,
                        task.context_id,
                        task.id,
                    ),
                    final = True,
                )
            print(f"📤 실패 응답 전송: {response_text[:100]}...")

        
    
    def _get_agent_name_from_context(self, context: RequestContext) -> str:
        """컨텍스트에서 에이전트 이름 추출 (더 이상 사용하지 않음)"""
        return self.agent_name
    
    async def _generate_llm_response(self, agent_name: str, user_message: str) -> LLMResponse:
        """LLM을 사용하여 응답 생성"""
        if not LLM_AVAILABLE:
            return LLMResponse(
                response=f"[{agent_name}] 기본 응답: {user_message}을(를) 받았습니다.",
                is_complete=True,
                error_occur=False
            )
        
        try:
            # 에이전트별 LLM 핸들러 가져오기
            llm_handler = get_agent_llm_handler(agent_name)
            
            # LLM으로 응답 생성
            response = await llm_handler.process_message(user_message)
            
            return LLMResponse(
                response=response,
                is_complete=True,
                error_occur=False
            )
            
        except Exception as e:
            print(f"❌ {agent_name} LLM 응답 생성 실패: {e}")
            return LLMResponse(
                response=f"[{agent_name}] 죄송합니다. 현재 응답을 생성할 수 없습니다.",
                is_complete=False,
                error_occur=True,
                error_message=str(e)
            )
    
    async def _handle_agent_specific_logic(self, agent_name: str, user_message: str, response: str):
        """에이전트별 특별한 로직 처리"""
        try:
            if "Recorder" in agent_name:
                # Recorder Agent: 데이터 저장
                await self._save_to_database(user_message, response)
                
            elif "Summarize" in agent_name:
                # Summarize Agent: 요약 결과를 Recorder Agent에게 전송
                if a2a_client:
                    forward_message = f"요약 결과: {response}"
                    await self.send_to_other("Recorder Agent", forward_message)
                    
        except Exception as e:
            print(f"⚠️ {agent_name} 특별 로직 처리 실패: {e}")
    
    async def _save_to_database(self, input_text: str, response: str):
        """데이터베이스에 저장 (Recorder Agent용)"""
        try:
            # 데이터 저장 로직
            timestamp = datetime.now().isoformat()
            record = {
                "timestamp": timestamp,
                "input": input_text,
                "response": response,
                "agent": "Recorder Agent"
            }
            
            # 파일로 저장 (임시)
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            save_dir = os.path.join(base_dir, "data", "recorder_memory")
            os.makedirs(save_dir, exist_ok=True)
            
            filename = f"record_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(save_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
            
            print(f"💾 데이터 저장 완료: {filepath}")
            
        except Exception as e:
            print(f"❌ 데이터 저장 실패: {e}")
    
    async def send_to_other(agent_name:str, user_text:str) -> None:
        if a2a_client is None:
            raise RuntimeError("A2AClientAgent is not initialized.")

        if agent_name not in a2a_client.remote_agent_connections:
            print(f"❌ 에이전트 '{agent_name}' 을 찾을 수 없습니다.")
            return

    
        response = await a2a_client.send_message(agent_name,user_text, task_id=None, context_id=None)
        print("Response:")
        if response : 
            for i, item in enumerate(response):
                print(f"  Part {i + 1}:")
                print(item)
        else : 
            print("⚠️ 응답이 없습니다 (response is None).")
            print()


    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise Exception('cancel not supported')


class A2ACombinedAgentExecutor(AgentExecutor):

    def __init__(self, remote_agent_entries: list[A2AServerEntry], agent_name: str = None, **kwargs):
        # 에이전트 이름 저장
        self.agent_name = agent_name or "Unknown Agent"
        self.client_agent = A2AClientAgent(remote_agent_entries)
        print(f"🤖 {self.agent_name} Combined 실행기 초기화 완료")
        
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:

        rcvRequest = context._params
        print("Request :", rcvRequest.model_dump(mode='json', exclude_none=False))
        print()
        
        # 1. 사용자 입력 메시지 받기
        text = context.get_user_input()
        task = context.current_task
        print(f"📨 수신된 메시지: {text}")
        
        # 2. 에이전트 이름 확인
        agent_name = self.agent_name
        print(f"🤖 에이전트: {agent_name}")
        
        # 3. LLM으로 응답 생성
        response_text = await self._generate_llm_response(agent_name, text)
        
        # 4. 특별한 처리 (에이전트별 로직)
        await self._handle_agent_specific_logic(agent_name, text, response_text)
        
        # 5. 응답 전송
        await event_queue.enqueue_event(new_agent_text_message(response_text))
        print(f"📤 응답 전송 완료: {response_text[:100]}...")
    
    async def _generate_llm_response(self, agent_name: str, user_message: str) -> str:
        """LLM을 사용하여 응답 생성"""
        if not LLM_AVAILABLE:
            return f"[{agent_name}] 기본 응답: {user_message}을(를) 받았습니다."
        
        try:
            # 에이전트별 LLM 핸들러 가져오기
            llm_handler = get_agent_llm_handler(agent_name)
            
            # LLM으로 응답 생성
            response = await llm_handler.process_message(user_message)
            
            return response
            
        except Exception as e:
            print(f"❌ {agent_name} LLM 응답 생성 실패: {e}")
            return f"[{agent_name}] 죄송합니다. 현재 응답을 생성할 수 없습니다."
    
    async def _handle_agent_specific_logic(self, agent_name: str, user_message: str, response: str):
        """에이전트별 특별한 로직 처리"""
        try:
            if "Summarize" in agent_name:
                # Summarize Agent: 요약 결과를 Recorder Agent에게 전송
                if self.client_agent:
                    forward_message = f"요약 결과: {response}"
                    await self.send_to_other("Recorder Agent", forward_message)
                    
        except Exception as e:
            print(f"⚠️ {agent_name} 특별 로직 처리 실패: {e}")
    
    
    async def send_to_other(self, agent_name:str, user_text:str) -> None:
        
        if agent_name not in self.client_agent.remote_agent_connections:
            print(f"❌ 에이전트 '{agent_name}' 을 찾을 수 없습니다.")
            
            # remote_server_enties에서 agent_name을 찾아서, 연결한다. 
            try:
                # remote_agent_entries에서 name으로 등록 시도
                await self.client_agent.retrieve_card_by_name(agent_name)
            except ValueError as e:
                print(f"❌ 에이전트 연결 실패: {e}")
                return
            
            # TODO : 바로 연결 돠니??

            # 연결 성공 여부 재확인
            if agent_name not in self.client_agent.remote_agent_connections:
                print(f"❌ 에이전트 '{agent_name}' 연결 실패 (등록 후에도 연결 없음).")
                return
            else:
                print(f"✅ 에이전트 '{agent_name}' 연결 완료.")

           
        response = await self.client_agent.send_message(agent_name, user_text, task_id=None, context_id=None)
        print("Response:")
        if response : 
            for i, item in enumerate(response):
                print(f"  Part {i + 1}:")
                print(item)
        else : 
            print("⚠️ 응답이 없습니다 (response is None).")
            print()


    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise Exception('cancel not supported')