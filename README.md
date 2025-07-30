# Aiffelton 프로젝트

이 프로젝트는 Python 가상환경(venv) 기반으로 동작합니다.
아래 과정을 따라 환경을 세팅하세요.

## 1️⃣ Python 버전 설정 (선택: pyenv 사용 시)

프로젝트 권장 Python 버전: **3.11.13**

```bash
# pyenv 설치된 경우
pyenv install 3.11.13
pyenv local 3.11.13   # 현재 디렉토리에 버전 적용
python --version      # 3.11.13 확인
```

## 2️⃣ 가상환경 생성

```bash
# 프로젝트 루트에서 venv 생성
python -m venv venv

# 가상환경 활성화
source venv/bin/activate      # Mac/Linux
venv\Scripts\activate         # Windows PowerShell
```

✅ 터미널 프롬프트에 `(venv)` 표시가 보이면 성공

## 3️⃣ pip 최신화

```bash
pip install --upgrade pip
```

## 4️⃣ 패키지 설치

```bash
pip install -r requirements.txt
```

⚠️ 만약 conda 환경에서 추출된 requirements.txt라면 `@ file:///...` 경로를 제거하고 일반 패키지명만 남겨주세요.

**예시 변환:**

```bash
grep -v '^#' requirements.txt | sed 's/ @ file:.*$//' > cleaned_requirements.txt
pip install -r cleaned_requirements.txt
```

## 5️⃣ 설치 확인

```bash
python -V           # Python 3.11.13
pip list | wc -l    # 설치된 패키지 수 확인
```

## 🤖 프로젝트 구조

```
Aiffelton/
├── README.md
├── .gitignore
├── .python-version
└── Agent/
    ├── .envsample              # 환경변수 템플릿
    └── agent-ai/
        ├── main.py             # 메인 실행 파일
        ├── requirements.txt    # 패키지 의존성
        ├── config/
        │   ├── config.yaml     # 설정 파일
        │   ├── langgraph/      # LangGraph 워크플로우
        │   └── ontologies/     # 도메인 온톨로지
        └── modules/
            ├── agent_core.py   # 핵심 에이전트 로직
            ├── llm_module.py   # LLM 통합
            ├── memory_module.py # 메모리 관리
            └── tools/          # 도구 모듈들
```

## 🚀 실행 방법

1. 가상환경 활성화 후 Agent 디렉토리로 이동:

```bash
cd Agent/agent-ai
```

2. 환경변수 설정:

```bash
cp ../.envsample .env
# .env 파일을 편집하여 API 키 등을 설정
```

3. 애플리케이션 실행:

```bash
python main.py
```