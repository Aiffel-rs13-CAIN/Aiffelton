import autogen
import testbed_utils
import re
import random


testbed_utils.init()
##############################

# Read the prompt
PROMPT = ""
with open("prompt.txt", "rt") as fh:
    PROMPT = fh.read()


# answer.txt로부터 정답 읽기
correct_answer = ""
explanation = ""

with open("answer.txt", "r") as f:
    lines = [line.strip() for line in f.readlines() if line.strip()]
    if len(lines) >= 1:
        correct_answer = lines[0]
    if len(lines) >= 2:
        explanation = lines[1]

print(f"✅ correct_answer : {correct_answer}")

config_list = autogen.config_list_from_json(
    "OAI_CONFIG_LIST",
    filter_dict={"model": ["deepseek/deepseek-chat-v3.1:free"]}
)

config_list2 = autogen.config_list_from_json("OAI_CONFIG_LIST",
                                            filter_dict={"model": ["gemini-1.5-flash"]})


medical_resident_prompt = """
You are a Medical Resident participating in case-based medical education. Your role is to:

1. Analyze presented medical cases systematically
2. Apply medical knowledge to multiple-choice questions  
3. Provide reasoned analysis of answer choices
4. Collaborate with other residents to reach correct answers
5. Demonstrate medical reasoning for standardized exam questions

Medical reasoning approach:
- Read the clinical scenario carefully
- Identify key clinical findings and patient characteristics
- Apply relevant medical knowledge (anatomy, physiology, pathology, pharmacology)
- Systematically evaluate each answer choice
- Eliminate obviously incorrect options
- Select the single best answer with clear reasoning

Communication style:
- Provide step-by-step medical reasoning
- Explain why certain choices are correct or incorrect
- Reference medical principles and guidelines when relevant
- Be open to input from other residents
- Focus on selecting from given options only

Answer format:
- Analyze each provided option (A, B, C, D, etc.)
- Explain medical reasoning for elimination or selection
- State your final choice clearly
- Provide brief justification for the selected answer
"""

llm_config = testbed_utils.default_llm_config(config_list)
llm_config2 = testbed_utils.default_llm_config(config_list2)

resident1 = autogen.AssistantAgent(
    "resident1", 
    system_message=medical_resident_prompt, 
    is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    llm_config=llm_config2)

resident2 = autogen.AssistantAgent(
    "resident2", 
    system_message=medical_resident_prompt, 
    is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    llm_config=llm_config2)

resident3 = autogen.AssistantAgent(
    "resident3", 
    system_message=medical_resident_prompt, 
    is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    llm_config=llm_config2)


user_proxy = autogen.UserProxyAgent(
    "user_proxy",
    #code_execution_config={"use_docker": False},
    code_execution_config=False,
    human_input_mode="NEVER",
    default_auto_reply="TERMINATE",
)

medical_team_leader_prompt = """
You are an experienced Medical Team Leader coordinating medical case discussions. Your role is to:

1. Present medical case scenarios clearly to the team
2. Coordinate systematic analysis among medical residents  
3. Guide the discussion toward the correct diagnosis/treatment choice
4. Ensure all team members contribute their medical knowledge
5. Facilitate decision-making for multiple-choice medical questions
6. Make final answer selection when needed

Key responsibilities:
- Read and interpret the medical case scenario
- Present the question and answer options to residents
- Facilitate systematic medical reasoning
- Ensure consideration of relevant medical principles
- Guide toward the single best answer from given options

Case presentation format:
- Present the complete clinical scenario
- List all available answer choices (A, B, C, D, E)
- Ask residents for systematic analysis
- Guide discussion toward evidence-based reasoning
- Ensure final answer selection from given options only
"""

medical_team_leader = autogen.AssistantAgent(
    "medical_team_leader", 
    system_message=medical_team_leader_prompt, 
    is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    llm_config=llm_config2)

residents = [resident1, resident2, resident3]

def state_transition(last_speaker, groupchat):
    messages = groupchat.messages
    
    # 고정된 순서 유지
    if last_speaker is user_proxy:
        return resident1
    elif last_speaker is resident1:
        return resident2
    elif last_speaker is resident2:
        return resident3
    elif last_speaker is resident3:
        return medical_team_leader
    elif last_speaker is medical_team_leader:
        return user_proxy
    else:
        # 예외 상황 처리
        return user_proxy

groupchat = autogen.GroupChat(
    agents=[user_proxy, resident1, resident2, resident3, medical_team_leader],   
    messages=[],
    speaker_selection_method=state_transition,
    allow_repeat_speaker=False,
    max_round=10  # 6라운드로 증가 (전체 흐름 완주 가능)
)

manager = autogen.GroupChatManager(
    groupchat=groupchat, 
    llm_config=llm_config2)

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

    # "final answer is X" 패턴에서 X 추출 (영어 패턴)
    match = re.search(r"final answer is\s*\*?\*?([A-E])\*?\*?", content, re.IGNORECASE)
   
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
            "content": "⚠️ 정답 형식을 인식할 수 없습니다. ('final answer is X' 형식으로 작성되었는지 확인하세요.)"
        }

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
testbed_utils.finalize(agents=[user_proxy, resident1, resident2, resident3, medical_team_leader, manager])