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

---

### 7️⃣ 프로젝트 실행

환경설정과 API 키 입력이 완료되면, 아래 명령어로 프로젝트를 실행할 수 있습니다.

```bash
# main.py 실행
python main.py
```

프로그램 실행 시 콘솔에 다음과 같은 메시지가 출력되면 정상 동작 중입니다.

```bash
'Aiffelton Agent' 에이전트가 준비되었습니다. 질문을 입력하세요. (종료하려면 'exit' 입력)
```
