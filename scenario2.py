import autogen
import testbed_utils


testbed_utils.init()
##############################

# Read the prompt
PROMPT = ""
with open("prompt.txt", "rt") as fh:
    PROMPT = fh.read()


# answer.txt로부터 정답 읽기
correct_answer = ""
explanation = ""

with open("answer.txt", "r", encoding="utf-8") as f:
    for line in f:
        if line.startswith("__ANSWER__"):
            correct_answer = line.split("=", 1)[1].strip()
        elif line.startswith("__EXPLAIN__"):
            explanation = line.split("=", 1)[1].strip()


config_list = autogen.config_list_from_json(
    "OAI_CONFIG_LIST",
    filter_dict={"model": ["deepseek/deepseek-chat-v3.1:free"]}
)

gp_system_message = """
당신은 미국 의사면허시험(USMLE) Step 1 및 Step 2 수준의 지식을 갖춘 유능한 일반의입니다.
당신의 역할은 환자 정보, 임상 상황, 치료 옵션 등을 기반으로 가장 적절한 진단, 처치 또는 윤리적 결정을 내리는 것입니다.

- 항상 의학적 사실과 표준 진료지침에 기반하여 판단하세요.
- 선택지 중에서 가장 안전하고 환자의 이익에 부합하는 답을 고르세요.
- 불확실한 경우에는 가장 가능성이 높은 것을 판단 기준으로 삼으세요.
- 질문에 주어진 정보 외의 추측은 피하세요.
- 선택지는 A, B, C, D, E 등으로 주어지며, 그 중 가장 적절한 하나만 선택하세요.

답변 형식 예시: "정답은 …입니다. 해당 선택지는 … 이유로 가장 적절합니다."
"""

llm_config = testbed_utils.default_llm_config(config_list)

assistant = autogen.AssistantAgent(
    "assistant", 
    system_message=gp_system_message, 
    is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    llm_config=llm_config)




user_proxy = autogen.UserProxyAgent(
    "user_proxy",
    #code_execution_config={"use_docker": False},
    code_execution_config=False,
    human_input_mode="NEVER"
)


groupchat = autogen.GroupChat(
    agents=[user_proxy, assistant],
    allow_repeat_speaker=False,
    messages=[],
    max_round=3
)

manager = autogen.GroupChatManager(
    groupchat=groupchat, 
    llm_config=llm_config)


# 정답 지정
#correct_answer = "C"

# 정답 확인 함수
def check_answer(agent, messages, sender, config, **kwargs):
    print("✅ check_answer 함수 호출됨")
    print(f"Sender: {sender.name}")


    if not messages:
        return True, {
            "role": "user",
            "content": "⚠️ 메시지가 없습니다."
        }

    latest_msg = messages[-1]
    print(f"[채점 중] assistant의 응답: {latest_msg['content']}")
    if correct_answer in latest_msg["content"]:
        return True, {
            "role": "user",
            "content": "✅ 정답입니다!"
        }
    else:
        return True, {
            "role": "user",
            "content": f"❌ 오답입니다. 정답은 {correct_answer}입니다."
        }
    # Autogen의 generate_reply()는 (final, reply) 형태로 반환하기 때문에 먼저 final을 True로 설정하고 reply를 반환

# assistant로부터 메시지를 받으면 check_answer 함수 자동 호출
user_proxy.register_reply(
    trigger=manager,
    reply_func=check_answer
)

# 대화 시작
user_proxy.initiate_chat(
    manager, 
    #message=PROMPT)
    message={"role": "user", "content": PROMPT})

#print(assistant.chat_messages)


##############################
testbed_utils.finalize(agents=[user_proxy, assistant, manager])
