import autogen
import testbed_utils

testbed_utils.init()
##############################

# Read the prompt
PROMPT = ""
with open("prompt.txt", "rt") as fh:
    PROMPT = fh.read()


config_list = autogen.config_list_from_json(
    "OAI_CONFIG_LIST"
)

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

llm_config = testbed_utils.default_llm_config(config_list)

assistant = autogen.AssistantAgent(
    "assistant", 
    system_message=gp_system_message, 
    is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    llm_config=llm_config)


# 정답 지정
correct_answer = "C"

# 정답 확인 함수
def check_answer(msg):
    print(f"[채점 중] assistant의 응답: {msg['content']}")
    if correct_answer in msg["content"]:
        return "✅ 정답입니다!"
    else:
        return f"❌ 오답입니다. 정답은 {correct_answer}입니다."

user_proxy = autogen.UserProxyAgent(
    "user_proxy",
    code_execution_config={"use_docker": False},
    human_input_mode="NEVER",
    default_auto_reply="정답을 확인하겠습니다."
)

groupchat = autogen.GroupChat(
    agents=[user_proxy, assistant],
    messages=[],
    max_round=3
)

manager = autogen.GroupChatManager(
    groupchat=groupchat, 
    llm_config=llm_config)

# 대화 시작
user_proxy.initiate_chat(
    manager, 
    message=PROMPT)

print(assistant.chat_messages)


##############################
testbed_utils.finalize(agents=[user_proxy, assistant, manager])