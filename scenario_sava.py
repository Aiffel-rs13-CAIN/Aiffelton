import autogen
import testbed_utils

testbed_utils.init()
##############################

# Read the prompt
PROMPT = ""
with open("prompt.txt", "rt") as fh:
    PROMPT = fh.read()

# Read the answer
ANSWER = "__ANSWER__"
try:
    with open("coding/my_test.py", "rt") as fh:
        test_content = fh.read()
        import re
        # assert answer == "C", f"Expected: C, Got: {answer}" 형태에서 정답 추출
        answer_match = re.search(r'assert answer == "([A-E])"', test_content)
        if answer_match:
            ANSWER = answer_match.group(1)
            print(f"📋 정답 읽기 완료: {ANSWER}")
        else:
            print(f"⚠️ 템플릿 미치환: {ANSWER}")
except Exception as e:
    print(f"❌ 정답 읽기 실패: {e}")
    ANSWER = "C"  # 기본값

# OpenRouter 전용 설정 로드
config_list = autogen.config_list_from_json("OAI_CONFIG_LIST")

# OpenRouter API 호환성 확인 (api_base 제거)
for config in config_list:
    if "openrouter.ai" not in config.get("base_url", ""):
        raise ValueError(f"❌ OpenRouter API만 지원합니다. 현재 설정: {config.get('base_url')}")


gp_system_message = """
당신은 미국 의사면허시험(USMLE) Step 1 및 Step 2 수준의 지식을 갖춘 유능한 일반의입니다.
당신의 역할은 환자 정보, 임상 상황, 치료 옵션 등을 기반으로 가장 적절한 진단, 처치 또는 윤리적 결정을 내리는 것입니다.

- 항상 의학적 사실과 표준 진료지침에 기반하여 판단하세요.
- 선택지 중에서 가장 안전하고 환자의 이익에 부합하는 답을 고르세요.
- 불확실한 경우에는 가장 가능성이 높은 것을 판단 기준으로 삼으세요.
- 질문에 주어진 정보 외의 추측은 피하세요.
- 선택지는 A, B, C, D, E 등으로 주어지며, 그 중 가장 적절한 하나만 선택하세요.

답변 형식 예시: "정답은 C입니다. 해당 선택지는 … 이유로 가장 적절합니다."
"""

# OpenRouter 전용 LLM 설정
llm_config = {
    "config_list": config_list,
    "temperature": 0.1,  # 의료 질문이므로 낮은 temperature로 일관성 확보
    "timeout": 60,
    "cache_seed": None,  # 재현 가능한 결과
    "max_tokens": 1000   # OpenRouter 모델 최적화
}

print(f"⚙️ OpenRouter LLM 설정 완료 - Temperature: {llm_config['temperature']}")
print(f"📝 최대 토큰: {llm_config['max_tokens']}")

assistant = autogen.AssistantAgent(
    "openrouter_medical_ai", 
    system_message=gp_system_message, 
    is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    llm_config=llm_config)

# 정답을 my_test.py에서 추출
correct_answer = "__ANSWER__"

# my_test.py에서 실제 정답 읽기
try:
    with open("coding/my_test.py", "r") as f:
        test_content = f.read()
        import re
        # assert answer == "C", f"Expected: C, Got: {answer}" 형태에서 정답 추출
        answer_match = re.search(r'assert answer == "([A-E])"', test_content)
        if answer_match:
            correct_answer = answer_match.group(1)
            print(f"📋 my_test.py에서 정답 추출: {correct_answer}")
        else:
            print(f"⚠️ 템플릿 미치환: {correct_answer}")
except Exception as e:
    print(f"❌ my_test.py 읽기 실패: {e}")

print(f"🎯 정답: {correct_answer}")
print(f"🤖 OpenRouter Medical AI 준비 완료")

# 정답 확인 함수 개선
def check_answer(msg):
    content = msg.get("content", "")
    print(f"[채점 중] assistant의 응답: {content[:200]}...")
    
    # 답변에서 선택지 추출 (A, B, C, D, E 중 하나)
    import re
    answer_pattern = r'\b([ABCDE])\b'
    found_answers = re.findall(answer_pattern, content.upper())
    
    if found_answers and correct_answer.upper() in found_answers:
        return f"✅ 정답입니다! (정답: {correct_answer})"
    else:
        return f"❌ 오답입니다. 정답은 {correct_answer}입니다."

user_proxy = autogen.UserProxyAgent(
    "user_proxy",
    code_execution_config={"use_docker": False},
    human_input_mode="NEVER",
    default_auto_reply="OpenRouter AI의 답변을 확인하겠습니다.",
    is_termination_msg=lambda x: True  # 한 번만 실행
)

print(f"🏥 OpenRouter 의료 AI 테스트 시작")
print(f"📝 문제 출제 중...")

# OpenRouter AI와 1:1 대화
chat_result = user_proxy.initiate_chat(
    assistant, 
    message=PROMPT,
    max_turns=1
)

# 결과 확인
if assistant.last_message():
    result = check_answer(assistant.last_message())
    print(f"\n📊 최종 결과: {result}")

print(f"\n💬 OpenRouter AI 응답:")
if user_proxy.chat_messages.get(assistant):
    for msg in user_proxy.chat_messages[assistant]:
        if msg["role"] == "assistant":
            print(f"🤖 {config_list[0]['model']}: {msg['content']}")
            break


##############################
testbed_utils.finalize(agents=[user_proxy, assistant])