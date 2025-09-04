import autogen
import testbed_utils
import re

testbed_utils.init()
##############################

# Read the prompt
PROMPT = ""
with open("prompt.txt", "rt") as fh:
    PROMPT = fh.read()


# answer.txt로부터 정답 읽기
correct_answer = ""
explanation = ""

# Read the answer
ANSWER = "__ANSWER__"

with open("answer.txt", "r", encoding="utf-8") as f:
    for line in f:
        if line.startswith("__ANSWER__"):
            correct_answer = line.split("=", 1)[1].strip()
        elif line.startswith("__EXPLAIN__"):
            explanation = line.split("=", 1)[1].strip()


config_list1 = autogen.config_list_from_json("OAI_CONFIG_LIST",
                                            filter_dict={"model": ["deepseek/deepseek-chat-v3.1:free"]})

config_list2 = autogen.config_list_from_json("OAI_CONFIG_LIST",
                                            filter_dict={"model": ["gemini-1.5-flash"]})

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
llm_config1 = {
    "config_list": config_list1,
    "temperature": 0.2,
    "timeout": 60,
    "cache_seed": None, 
    "max_tokens": 1000   
}

llm_config2 = {
    "config_list": config_list2,
    "temperature": 0.2,  
    "timeout": 60,
    "cache_seed": None, 
    "max_tokens": 1000   
}


doctor1 = autogen.AssistantAgent(
    "의료진_박사", 
    system_message=gp_system_message, 
    is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    llm_config=llm_config1)

doctor2 = autogen.AssistantAgent(
    "의료진_교수", 
    system_message=gp_system_message,
    is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    llm_config=llm_config2)

# # 정답 확인 함수
# def check_answer(agent, messages, sender, config, **kwargs):
#     print("✅ check_answer 함수 호출됨")
#     print(f"Sender: {sender.name}")

#     if not messages:
#         return True, {
#             "role": "user",
#             "content": "⚠️ 메시지가 없습니다."
#         }

#     latest_msg = messages[-1]
#     print(f"[채점 중] assistant의 응답: {latest_msg['content']}")
#     if correct_answer in latest_msg["content"]:
#         return True, {
#             "role": "user",
#             "content": "✅ 정답입니다!"
#         }
#     else:
#         return True, {
#             "role": "user",
#             "content": f"❌ 오답입니다. 정답은 {correct_answer}입니다."
#         }
    
    # 정답 확인 함수
def check_answer(agent, messages, sender, config, **kwargs):
    print(f"✅ check_answer 함수 호출됨 : {correct_answer}")
    print(f"Sender: {sender.name}")


    if not messages:
        return True, {
            "role": "user",
            "content": "⚠️ 메시지가 없습니다."
        }
    
    latest_msg = messages[-1]
    content = latest_msg.get("content", "")
    print(f"[채점 중] assistant의 응답: {content}")

    # "정답은 X입니다"에서 X 추출
    match = re.search(r"정답은\s*([A-E])\s*", content)
   
    if match:
        extracted_answer = match.group(1)
        print(f"[채점 중] 추출된 답변: {extracted_answer}")

        # Autogen의 generate_reply()는 (final, reply) 형태로 반환하기 때문에 먼저 final을 True로 설정하고 reply를 반환
        if extracted_answer == correct_answer:
            return True, {
                "role": "user",
                "content": "✅ 정답입니다!"
            }
        else:
            return True, {
                "role": "user",
                "content": f"❌ 오답입니다. 정답은 {correct_answer}입니다."
            }
    else:
        # 형식이 잘못된 경우
        return True, {
            "role": "user",
            "content": "⚠️ 정답 형식을 인식할 수 없습니다. ('정답은 X입니다' 형식으로 작성되었는지 확인하세요.)"
        }


# 토론 중재자 설정
moderator = autogen.UserProxyAgent(
    "토론_중재자",
    # code_execution_config={"use_docker": False},
    code_execution_config=False,
    human_input_mode="NEVER",
    default_auto_reply="TERMINATE",
    #is_termination_msg=lambda x: "정답입니다" in x.get("content", "") or "TERMINATE" in x.get("content", ""),
    #max_consecutive_auto_reply=1
)

print(f"🏥 의료진 토론 시작")
print(f"📝 문제 출제 중...")

# 그룹 채팅 설정
groupchat = autogen.GroupChat(
    agents=[moderator, doctor1, doctor2], 
    messages=[], 
    max_round=4, 
    speaker_selection_method="round_robin",
    allow_repeat_speaker=False
)

# 그룹 채팅 매니저
manager = autogen.GroupChatManager(
    groupchat=groupchat, 
    llm_config=llm_config1
)

# register_reply를 initiate_chat 호출 전에 등록
moderator.register_reply(
    trigger=manager,
    reply_func=check_answer
)

# 토론 시작
print("🗣️ 의료진 토론을 시작합니다...")
discussion_prompt = f"""
다음 의료 사례에 대해 토론해주세요:

{PROMPT}

두 의료진은 각자의 의견을 제시하고, 서로의 관점을 고려하여 토론한 후 최종 합의안을 도출해주세요.
토론이 끝나면 "최종답변: [A/B/C/D/E]" 형식으로 결론을 내려주세요.
"""

# 토론 실행 (한 번만)
moderator.initiate_chat(
    manager,
    message=PROMPT
    #max_turns=10
)

print(f"\n💬 토론 완료!")


# # 토론 결과 분석
# print("\n📊 토론 결과 분석 중...")
# conversation_history = chat_result.chat_history if hasattr(chat_result, 'chat_history') else []

# # 대화 내용이 없는 경우 groupchat에서 가져오기
# if not conversation_history:
#     conversation_history = groupchat.messages

# result = check_answer(conversation_history)
# print(f"\n📊 최종 결과: {result}")

# print(f"\n💬 토론 요약:")
# for i, msg in enumerate(conversation_history[-3:]):  # 마지막 3개 메시지만 표시
#     speaker = msg.get("name", "Unknown")
#     content = msg.get("content", "")[:200] + "..." if len(msg.get("content", "")) > 200 else msg.get("content", "")
#     print(f"🎯 {speaker}: {content}")

##############################
testbed_utils.finalize(agents=[moderator, doctor1, doctor2, manager])