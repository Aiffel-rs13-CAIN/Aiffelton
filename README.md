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
python -V           # Python 3.11.13
pip list | wc -l    # 설치된 패키지 수 확인
```
