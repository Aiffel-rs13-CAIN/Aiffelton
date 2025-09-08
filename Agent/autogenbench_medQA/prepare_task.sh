#!/bin/bash

# 스크립트가 위치한 디렉토리로 이동하여 경로 기준을 맞춥니다.
cd "$(dirname "$0")"

# --- 메인 로직 ---

# 1. 인자 없이 실행하는 경우
if [ $# -eq 0 ]; then
    echo "인자 없이 실행: Scripts/init_tasks.py 를 수행합니다."
    python3 Scripts/init_tasks.py
    exit 0
fi

# 2. --template 인자와 함께 실행하는 경우
if [ "$1" == "--template" ] && [ -n "$2" ]; then
    TEMPLATE_NAME="$2"
    SOURCE_FILE="Tasks/medqa_single_llm.jsonl"
    OUTPUT_FILE="Tasks/medqa_${TEMPLATE_NAME}.jsonl"

    # 원본 템플릿 파일이 없으면 init_tasks.py를 실행하여 생성
    if [ ! -f "$SOURCE_FILE" ]; then
        echo "원본 템플릿 파일(${SOURCE_FILE})이 없습니다. Scripts/init_tasks.py를 먼저 실행합니다."
        python3 Scripts/init_tasks.py
        
        # 실행 후에도 파일이 없으면 오류
        if [ ! -f "$SOURCE_fILE" ]; then
            echo "오류: init_tasks.py 실행 후에도 ${SOURCE_FILE}을 찾을 수 없습니다."
            exit 1
        fi
    fi

    # sed를 사용하여 템플릿 경로를 치환하고 새 파일 생성
    echo "${SOURCE_FILE}을 복사하여 ${OUTPUT_FILE}을 생성합니다..."

    # sed 명령어에서 사용할 안전한 템플릿 이름 생성 (경로 구분자 / 이스케이프)
    SAFE_TEMPLATE_NAME=$(echo "$TEMPLATE_NAME" | sed 's/\//\\\//g')

    sed "s|../Templates/single_llm|../Templates/${SAFE_TEMPLATE_NAME}|g" "$SOURCE_FILE" > "$OUTPUT_FILE"

    echo "완료: ${OUTPUT_FILE} 파일이 생성되었고, 템플릿 경로가 수정되었습니다."
    exit 0
fi

# 3. 그 외 잘못된 사용법
echo "잘못된 사용법입니다."
_self=$(basename "$0")
echo "사용법 1: ${_self}"
echo "사용법 2: ${_self} --template <템플릿이름>"
exit 1
