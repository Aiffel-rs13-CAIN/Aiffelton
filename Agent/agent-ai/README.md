# A2A, Langgraphs기반 멀티에이전트 구축 (mem0, MCP 연동)

이 프로젝트는 Python 가상환경(venv) 기반으로 동작합니다.
아래 과정을 따라 환경을 세팅하세요.

## 1️⃣ Python 버전 설정 (선택: pyenv 사용 시)

프로젝트 권장 Python 버전: **3.13.2**

```bash
# pyenv 설치된 경우
pyenv install 3.13.2
pyenv local 3.13.2   # 현재 디렉토리에 버전 적용
python --version      # 3.13.2 확인
```

## 2️⃣ 가상환경 생성

```bash
# 프로젝트 루트에서 venv 생성
python -m venv venv

# 가상환경 활성화
source venv/bin/activate      # Mac/Linux
venv\Scripts\activate         # Windows PowerShell
```

터미널 프롬프트에 `(venv)` 표시가 보이면 성공

## 3️⃣ pip 최신화

```bash
pip install --upgrade pip
```

## 4️⃣ 패키지 설치

```bash
pip install -r requirements.txt
```

**예시 변환:**

```bash
grep -v '^#' requirements.txt | sed 's/ @ file:.*$//' > cleaned_requirements.txt
pip install -r cleaned_requirements.txt
```

## 5️⃣ 설치 확인

```bash
python -V           # Python 3.13.2
pip list | wc -l    # 설치된 패키지 수 확인
```

---

### 6️⃣ API 키 설정 (.env 파일 생성) - .env sample 예시참고

프로젝트 실행을 위해서는 LangSmith, Google, OpenAI, Mem0 등의 API 키가 필요합니다.
프로젝트 agnet-ai 디렉토리에 `.env` 파일을 생성하고 아래 내용을 입력하세요.

```env
LANGSMITH_API_KEY=lsv2_pXXXXXXXXXXXXXXXXX
GOOGLE_API_KEY=AIzaSyXXXXXXXXXXXXXXXXX
OPENAI_API_KEY=sk-pro-XXXXXXXXXXXXXXXXX
MEM0_API_KEY=m0-pKIPOYwumXXXXXXXXXXXXXXXXX
```

| 환경변수          | 설명                               |
| ----------------- | ---------------------------------- |
| LANGSMITH_API_KEY | LangSmith 트래킹용 API 키          |
| GOOGLE_API_KEY    | Google Gemini/Generative AI API 키 |
| OPENAI_API_KEY    | OpenAI GPT 모델 API 키             |
| MEM0_API_KEY      | Mem0 장기 메모리 서비스 API 키     |

## 참고: `MEM0_API_KEY`는 https://mem0.ai/ 에서 발급받아 사용할 수 있습니다.

### 7️⃣ 프로젝트 실행

환경설정과 API 키 입력이 완료되면, agent-ai 디렉토리로 이동하여 프로젝트를 실행할 수 있습니다.

```bash
# agent-ai 디렉토리로 이동
cd Agent/agent-ai

# 가상환경 활성화 (아직 안 되어 있다면)
source venv/bin/activate

# 메인 시스템 실행 (권장)
python main.py
```

## 🚀 실행 모드

이 프로젝트는 다양한 실행 모드를 제공합니다:

### 1. **전체 시스템 실행** (권장)

```bash
python main.py
```

- **LabAssistant** (메인 에이전트) + **A2A 멀티에이전트 시스템** 모두 실행
- 3개 A2A 서버가 동시에 시작됩니다:
  - `LabAssistant` (포트 10000) - 메인 조율 에이전트
  - `Recorder Agent` (포트 10001) - 데이터 기록 전담
  - `Summarize Agent` (포트 10003) - 텍스트 요약 전담
- 양방향 에이전트 간 통신 지원

### 2. **개별 에이전트 실행**

```bash
python main.py <agent_name>
```

사용 가능한 에이전트:

```bash
python main.py recorder_agent      # Recorder Agent만 실행
python main.py summarize_agent     # Summarize Agent만 실행
python main.py        # LabAssistant만 실행 (A2A 없이)
```

### 3. **에이전트 목록 확인**

```bash
python main.py list               # 사용 가능한 에이전트 목록
python main.py --help             # 도움말 출력
```

## 📋 실행 성공 확인

**전체 시스템 실행 시** 다음과 같은 메시지가 출력되면 정상 동작 중입니다:

```bash
🚀 A2A Manager 시작 중...
🚀 A2A 서버 시작: http://127.0.0.1:10000 (config: main_agent.json)
  ✅ 서버 시작됨: LabAssistant
🚀 A2A 서버 시작: http://127.0.0.1:10001 (config: recorder_agent.json)
  ✅ 서버 시작됨: Recorder Agent
🚀 A2A 서버 시작: http://127.0.0.1:10003 (config: summarize_agent.json)
  ✅ 서버 시작됨: Summarize Agent
✅ A2A Manager 준비 완료 (서버: 3개, 클라이언트: 준비됨)

🤖 에이전트를 시작합니다.
📝 명령어:
  - 'exit' : 종료
  - 'debug' : 상태 확인
  - '/node <작업내용>' : 노드 기반 멀티에이전트 실행
  - '/a2a <agent_name> <message>' : A2A 통신
💡 이제 LLM이 자동으로 필요시 다른 에이전트와 통신합니다!
```

## 🎯 사용 예시

### 기본 대화

```
사용자: 최신 AI 논문을 찾아주세요
```

### A2A 에이전트 직접 호출

```
사용자: /a2a 'Summarize Agent' '이 텍스트를 요약해주세요: [긴 텍스트]'
사용자: /a2a 'Recorder Agent' '이 데이터를 저장해주세요'
```

### 멀티에이전트 워크플로우

```
사용자: 이 논문을 요약하고 기록해주세요
# → LabAssistant가 자동으로 Summarize Agent와 Recorder Agent에게 작업 분배
```

---

## 📁 프로젝트 구조

```
Agent/
└── agent-ai/
    ├── config/
    │   ├── a2a/                            # A2A 에이전트 카드 정의
    │   │   ├── main_agent.json
    │   │   ├── recorder_agent.json
    │   │   └── summarize_agent.json
    │   ├── agents/                         # 개별 에이전트 설정
    │   │   ├── recorder_agent_config.yaml
    │   │   └── summarize_agent_config.yaml
    │   ├── config.yaml                     # 메인 시스템 통합 설정
    │   ├── mcp.json                        # MCP 서버 연결 설정
    │   └── ontologies/                     # 온톨로지 정의 (미완)
    │       └── lab_ontology.owl
    │
    ├── main.py
    │
    ├── modules/
    │   ├── a2a_core/
    │   │   ├── a2a_client.py               # A2A 클라이언트 구현체
    │   │   ├── config_loader.py            # A2A 설정 로더
    │   │   ├── server_executor.py          # A2A 서버 실행 관리
    │   │   └── server_factory.py           # A2A 서버 팩토리 패턴
    │   ├── a2a_client_module.py            # A2A 클라이언트 통신 관리
    │   ├── a2a_manager.py                  # A2A 멀티서버 통합 관리자
    │   ├── a2a_server_module.py            # A2A 서버 통신 관리
    │   ├── agent_llm_handler.py            # 에이전트별 LLM 처리 핸들러
    │   ├── llm_module.py                   # LLM 통신 및 응답 처리
    │   ├── mcp_module.py                   # MCP 서버 연동 모듈
    │   ├── memory_module.py                # 메모리 관리 (mem0/in-memory)
    │   ├── output_module.py                # 출력 포맷팅 및 표시
    │   ├── tool_module.py                  # 도구 통합 관리
    │   ├── tools/                          # 전용 도구 모듈들
    │   │   └──  mcp_module.py               # MCP 전용 도구 인터페이스
    │   │   
    │   └── user_input_module.py            # 사용자 입력 처리 및 파싱
    │
    ├── workflows/
    │   ├── single_agent_flow.py            # 단일 에이전트 실행 플로우
    │   ├── workflow_controller.py          # 워크플로우 제어 및 라우팅
    │   └── workflow_factory.py             # 워크플로우 팩토리 패턴
    │
    └── requirements.txt
```

## 🔄 시스템 파이프라인 흐름

```
사용자 요청
    ↓
user_input_module: 사용자 입력 파싱 및 처리
    ↓
workflow_controller: 요청 분석 후 적절한 워크플로우 선택
    ↓
agent_llm_handler: LLM 기반 에이전트 판단 및 작업 분배
    ↓
tool_module: 필요한 도구(MCP/RAG) 자동 선택 및 실행
    ↓
a2a_manager: 다중 에이전트 간 A2A 통신 조율
    ↓
memory_module: 대화 기록 및 컨텍스트 저장/검색 (mem0)
    ↓
output_module: 결과 통합 및 사용자 친화적 포맷팅
```

## 🧩 핵심 모듈 설명

**시스템 제어**

- `main.py`: 전체 시스템 초기화 및 A2A 서버 통합 관리
- `workflow_controller.py`: 사용자 요청에 따른 워크플로우 라우팅 및 제어
- `user_input_module.py`: 명령어 파싱 (/a2a, /node 등) 및 입력 검증

**A2A 통신 시스템**

- `a2a_manager.py`: 멀티 에이전트 서버 생성/관리 및 클라이언트 연결
- `a2a_client.py`: 에이전트 간 메시지 송수신 및 응답 처리
- `server_factory.py`: 에이전트 설정 기반 A2A 서버 동적 생성

**LLM 및 도구 통합**

- `llm_module.py`: Google/OpenAI LLM 통신 및 시스템 메시지 기반 에이전트 통신 제어
- `mcp_module.py`: Model Context Protocol 서버 연결 및 외부 도구 호출
- `tool_module.py`: MCP, RAG 등 도구들의 통합 인터페이스 제공

**메모리 및 지식 관리**

- `memory_module.py`: mem0 API 기반 장기 메모리 관리 및 대화 컨텍스트 유지
- `output_module.py`: 응답 결과 통합, 포맷팅 및 사용자 인터페이스 출력

## ⚙️ 설정 파일 관리

프로젝트는 다양한 설정 파일을 통해 에이전트, MCP 서버, 메모리, LLM 모델을 관리합니다.

### 📋 1. 에이전트 설정 (`config/agents/`)

에이전트별 개별 설정 파일을 통해 각 에이전트의 동작을 정의합니다.

**파일 위치**: `config/agents/`

- `summarize_agent_config.yaml` - 요약 에이전트 설정
- `recorder_agent_config.yaml` - 기록 에이전트 설정

**설정 예시**:

```yaml
# Summarize Agent Config
agent:
  name: "Summarize Agent"
  description: "텍스트 요약 및 분석을 전담하는 에이전트"

llm:
  provider: "google" # 'google' 또는 'openai'
  model: "gemini-2.5-flash" # 사용할 LLM 모델
  temperature: 0.5 # 창의성 설정 (0.0~1.0)
  system_message: | # 에이전트 역할 정의
    당신은 전문적인 텍스트 요약 및 분석 에이전트입니다.
    [상세한 역할 설명...]

memory:
  type: "in_memory" # 메모리 타입
  settings:
    auto_save: true

# A2A 통신 설정
a2a:
  auto_forward_to: "Recorder Agent" # 자동 전달할 에이전트
  forward_results: true # 결과 자동 전달 여부
```

### 🔗 2. A2A 에이전트 카드 정의 (`config/a2a/`)

A2A(Agent-to-Agent) 통신을 위한 에이전트 카드를 정의합니다.

**파일 위치**: `config/a2a/`

- `main_agent.json` - 메인 에이전트 카드
- `recorder_agent.json` - 기록 에이전트 카드
- `summarize_agent.json` - 요약 에이전트 카드

**에이전트 카드 구조**:

### example

```json
{
  "name": "LabAssistant",
  "description": "연구실의 AI 연구 어시스턴트",
  "host": "localhost",
  "port": 10000,
  "version": "1.0.0",
  "skills": [
    {
      "id": "research_coordination",
      "name": "Research Coordination",
      "description": "논문 탐색, 연구주제 발굴",
      "tags": ["research", "coordination"],
      "examples": [
        "최신 AI 논문을 찾아주세요",
        "이 내용을 요약해서 기록해주세요"
      ]
    }
  ],
  "capabilities": {
    "streaming": true,
    "batch_processing": false
  }
}
```

### 🌐 3. MCP 서버 추가 (`config/mcp.json`)

Model Context Protocol 서버를 추가하여 외부 도구와 연결합니다.

**파일 위치**: `config/mcp.json`

**MCP 서버 추가 방법**:

```json
{
  "mcpServers": {
    "arxiv-paper-mcp": {
      "command": "npx",
      "args": [
        "-y",
        "@smithery/cli@latest",
        "run",
        "@daheepk/your-mcp",
        "--key",
        "your-api-key"
      ]
    },
    "새로운-mcp-서버": {
      "command": "python",
      "args": ["-m", "your_mcp_server", "--config", "config.json"]
    }
  }
}
```

**주요 설정 옵션**:

- `command`: 실행할 명령어
- `args`: 명령어 인자 배열
- API 키나 설정 파일 경로 포함

### 💾 4. Mem0 메모리 설정 (`config/config.yaml`)

장기 메모리 관리를 위한 Mem0 설정을 구성합니다.

**메모리 설정 섹션**:

```yaml
memory:
  # 대화 기록을 저장할 방식 ('in_memory' 또는 'mem0')
  type: "mem0"
  # 기본 사용자 ID (각 사용자별로 독립적인 메모리 관리)
  default_user_id: "your-user-id"
  # 메모리 설정
  settings:
    # 검색 시 반환할 최대 메모리 개수
    search_limit: 5
    # 대화 기록 조회 시 반환할 최대 개수
    history_limit: 50
    # 메모리 자동 저장 여부
    auto_save: true
    # 메모리 압축 임계값 (메모리 개수가 이 값을 초과하면 압축)
    compression_threshold: 1000
```

**메모리 타입**:

- `in_memory`: 세션 기반 임시 메모리
- `mem0`: 영구 저장 메모리 (API 키 필요)

### 🤖 5. LLM 모델 설정 (`config/config.yaml`)

사용할 LLM 모델과 관련 설정을 구성합니다.

**LLM 설정 섹션**:

```yaml
llm:
  # LLM provider ( EX.'google', 'openai')
  provider: "your-provider"
  # model name (gpt-4o-mini, gemini-2.5-flash 등)
  model: "your-model-name"
  # 창의성 설정 (0.0~1.0)
  temperature: 0.7
  # 시스템 메시지 설정
  system_message: |
    당신은 연구실의 AI 연구 어시스턴트입니다.
    [상세한 역할 정의...]
```

### 🔧 6. 통합 설정 관리

모든 설정은 `config/config.yaml`에서 통합 관리됩니다:

```yaml
# 에이전트 기본 정보
agent:
  name: "LabAssistant"
  flow: "single_agent_flow"

# LLM 설정
llm:
  provider: "your-provider"
  model: "your-model"

# 메모리 설정
memory:
  type: "mem0"
  default_user_id: "your-user-id"

# A2A 서버 설정
a2a:
  start_servers: ["Summarize Agent", "Recorder Agent"]
  attach_client_to_server: true

# MCP 설정
mcp:
  config_path: "config/mcp.json"
```

### 🔄 7. A2A 에이전트 간 통신 메커니즘

프로젝트의 핵심은 **LLM의 시스템 메시지를 통해 에이전트 간 자동 통신**이 이루어지는 구조입니다.

#### 🧠 시스템 메시지: 통신의 핵심 제어 로직

LLM이 다른 에이전트와 통신하는 모든 규칙은 `system_message`에 정의되어 있습니다:

system_message 예시:

```yaml
llm:
  system_message: |
    당신은 연구실의 AI 연구 어시스턴트입니다. 다음 규칙을 반드시 준수합니다.

    1) 에이전트 통신 vs 도구 호출 구분
      - a2a_send는 에이전트에게 A2A를 보낼 때 사용
      - MCP 도구는 LLM이 직접 function/tool로 호출

    2) 도구 호출 규약 (필수)
      - 모든 도구 호출은 function/tool 호출 형식: name + args(object)
      - 필수 인자가 누락된 경우 사용자에게 확인 또는 자동 보정

    3) 호출/응답 처리
      - 도구 결과는 후처리를 통해 자연어로 요약하여 제공
      - 오류 발생 시 상태 알림 및 다음 행동 제안

    4) 자동 판단 로직
      - 사용자 요청 분석 → 적절한 에이전트/도구 자동 선택
      - 복합 작업의 경우 여러 에이전트에게 순차적 통신

    요약: a2a_send는 실제 에이전트 전용, MCP는 직접 호출, 
    자동 판단으로 적절한 통신 경로 선택
```

#### 📡 통신 흐름: LLM이 중재하는 자동화

**핵심 원리**: LLM이 시스템 메시지를 기반으로 사용자 요청을 분석하고 자동으로 적절한 통신 방법을 선택합니다.

```
사용자 요청
    ↓
LLM 분석 (system_message 기반)
    ↓
판단: "이 작업은 어떤 에이전트/도구가 필요한가?"
    ↓
자동 선택:
- 전문 작업 → a2a_send로 특화 에이전트 호출
- 데이터 검색 → MCP 도구 직접 호출
- 복합 작업 → 여러 에이전트 순차 호출
    ↓
결과 통합 → 사용자에게 자연어 응답
```

#### ⚙️ 설정을 통한 통신 제어

**메인 설정에서 통신 활성화**:

```yaml
# config/config.yaml
a2a:
  start_servers: ["Agent1", "Agent2", "Agent3"] # 사용할 에이전트 목록
  attach_client_to_server: true # 양방향 통신 활성화
  client:
    enabled: true # 클라이언트 기능 활성화
```

**개별 에이전트의 자동 연계 설정**:

```yaml
# config/agents/agent_config.yaml
a2a:
  auto_forward_to: "NextAgent" # 작업 완료 후 자동 전달
  forward_results: true # 결과 자동 전달
```

---
