# Aiffelton 프로젝트

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

### 6️⃣ API 키 설정 (.env 파일 생성)

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
