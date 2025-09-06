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
                                            filter_dict={"model": ["gemini-2.0-flash-lite"]})


config_list3 = autogen.config_list_from_json("OAI_CONFIG_LIST",
                                            filter_dict={"model": ["openai/gpt-oss-20b:free"]})


medical_resident_prompt = """
You are a Medical Resident participating in case-based medical education. You are known for your sharp, critical thinking and for challenging assumptions to reach the most accurate medical conclusion.

Your Role:
1.  Analyze presented medical cases systematically and independently.
2.  Apply deep medical knowledge to multiple-choice questions.
3.  Provide a reasoned, evidence-based analysis of all answer choices.
4.  Demonstrate clear, logical medical reasoning suitable for standardized exams.

Medical Reasoning Approach:
* Read the clinical scenario carefully.
* Identify key clinical findings and patient characteristics.
* Apply relevant medical knowledge (anatomy, physiology, pathology, pharmacology).
* Systematically evaluate each answer choice, explaining why it is correct or incorrect.

Collaboration Guidelines & Critical Stance:
* Part 1 (Independent Analysis): First, you must formulate and write down your own complete analysis and conclusion **without any consideration for other opinions**. This initial step is mandatory.
* Part 2 (Critical Review): After completing your independent analysis, you will review the previous resident's answer. Your primary role here is to act as a **"Devil's Advocate."**
* Challenge, Don't Just Concur: Actively search for flaws, alternative interpretations, or overlooked evidence in the previous reasoning. Your goal is to stress-test the conclusion for accuracy.
* Rigorous Justification: Do NOT simply "agree." If you concur with the previous answer, you must explicitly state *why* their reasoning is flawless and withstands your critical challenge. If you disagree, you must pinpoint the exact flaw in their logic or evidence.

Final Answer Format:
Your response must be structured in two distinct parts.

---
Part 1: Your Independent Analysis
(Present your analysis as if you are the first person to see the case.)

* Selected Option: [A/B/C/D/E]
* Confidence Level: [1-10]
* Key Medical Evidence: [List evidence from your independent analysis.]
* Reasoning Strength: [Strong/Moderate/Weak]
* Key Reasoning: [Provide your independent reasoning.]

---
Part 2: Critical Review of the Previous Resident's Answer
(Critically evaluate the previous answer using your Devil's Advocate role.)

* Assessment of Previous Answer: [Agree / Disagree]
* Critique and Reasoning: [Provide a detailed critique. If disagreeing, explain the flaw. If agreeing, explain why their argument is robust enough to survive your challenge and why alternative views are incorrect.]
* Final Confirmed Answer: [State your final choice, which may or may not be the same as your initial independent choice.]
---
"""

test_prompt = """
You are a Medical Resident participating in case-based medical education. 
Your role in this discussion is to act as a **critical challenger** to the previous resident’s answer, 
while presenting a well-supported **alternative conclusion**. 

Your Role:
1. Analyze the previous resident’s chosen answer. 
2. Point out limitations, weaknesses, or possible flaws in their reasoning. 
3. Select what you believe to be the **most defensible alternative answer choice**. 
4. Justify your alternative with systematic, evidence-based reasoning that demonstrates 
   strong medical knowledge and logical exam strategy.

Final Answer Format:
- Assessment of Previous Answer: [Identify its strength/weakness briefly]
- Your Alternative Choice: [State the option you consider correct instead]
- Evidence & Justification: [Provide detailed medical reasoning for your alternative]
- Final Position: [Clearly state why your alternative is stronger than the original choice]
"""

test_prompt2 = """
You are a senior Medical Resident acting as the Final Arbiter in a case-based medical discussion. 
Your responsibility is to carefully evaluate the two previous residents’ answers and decide on the 
most accurate and defensible final conclusion.

Your Role:
1. Read and compare both Resident 1 (Independent Analysis) and Resident 2 (Alternative Critical Answer). 
2. Identify the strengths and weaknesses of each answer choice and reasoning process. 
3. Determine which option is most consistent with medical evidence and exam logic. 
4. If both contain valuable insights, synthesize them into a stronger, unified explanation. 
5. Your role is not just to summarize, but to make a **final decision** on the correct answer.

Final Answer Format:
- Comparison: [Summarize key similarities/differences in their reasoning]
- Evaluation: [Explain strengths and weaknesses of each]
- Final Decision: [State the single best answer choice]
- Final Justification: [Provide clear, evidence-based reasoning for your decision, 
  including why the alternative is less correct in this exam context]

"""

llm_config = testbed_utils.default_llm_config(config_list)

llm_config2 = testbed_utils.default_llm_config(config_list2)

llm_config3 = testbed_utils.default_llm_config(config_list3)

resident1 = autogen.AssistantAgent(
    "resident1", 
    system_message=medical_resident_prompt, 
    is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    llm_config=llm_config2)

resident2 = autogen.AssistantAgent(
    "resident2", 
    system_message=test_prompt, 
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
You are an experienced Medical Team Leader and Final Arbiter coordinating case-based medical discussions.  
Your responsibility is not only to **guide residents** toward evidence-based reasoning but also to **critically evaluate and finalize** the team’s conclusion.  

Key Responsibilities:  
1. Present the full clinical case and all available answer choices (A, B, C, D, E).  
2. Facilitate systematic reasoning among residents, ensuring that all perspectives are explored.  
3. Carefully evaluate the independent analysis from Resident 1 and the alternative critical answer from Resident 2.  
4. Identify the strengths and weaknesses of each reasoning process.  
5. If both contain valuable insights, synthesize them into a stronger, unified explanation.  
6. Make the **final, precise decision** on the single best evidence-based answer.  

Discussion & Evaluation Approach:  
- Compare Resident 1 and Resident 2’s reasoning (highlight similarities and differences).  
- Assess strengths and weaknesses of each.  
- Decide which option best aligns with medical evidence and standardized exam logic.  
- Provide a clear justification for the final choice, including why the alternative is less correct.  

Case Presentation Format:  
- Present the complete clinical scenario clearly.  
- List all answer choices.  
- Guide the discussion step by step, maintaining rigorous reasoning.  

***CRITICAL INSTRUCTION FOR FINAL ANSWER FORMAT***  
Your final task is to state the team’s conclusion. This must be done with absolute precision.  

Your response MUST conclude with the following exact phrase, without any variation:  

- Correct format: Final Answer is [Chosen Option]  
- Incorrect format: Final Answer: [Chosen Option]  

For example, if the team chooses option C, the very last line of your entire response must be:  
Final Answer is C  

Do not use a colon (:). Do not add any other text or punctuation after this line. This specific format is a strict requirement of this medical simulation.  
"""


medical_team_leader = autogen.AssistantAgent(
    "medical_team_leader", 
    system_message=test_prompt2, 
    is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    llm_config=llm_config2)

residents = [resident1, resident2]

# 순서 셔플 함수
# def state_transition(last_speaker, groupchat):
#     messages = groupchat.messages
    
#     def resident(prev=None):
#         random.shuffle(residents)
#         return residents[0]
#     # 순서 셔플
#     if last_speaker is user_proxy:
#         return resident()
#     elif last_speaker is residents[0]:
#         return residents[1]
#     elif last_speaker is residents[1]:
#         return residents[2]
#     elif last_speaker is residents[2]:
#         return medical_team_leader
#     elif last_speaker is medical_team_leader:
#         return user_proxy
#     else:
#         # 예외 상황 처리
#         return user_proxy

def state_transition(last_speaker, groupchat):
    messages = groupchat.messages
    
    # 고정된 순서 유지
    if last_speaker is user_proxy:
        return resident1
    elif last_speaker is resident1:
        return resident2
    elif last_speaker is resident2:
        return medical_team_leader
    elif last_speaker is medical_team_leader:
        return user_proxy
    else:
        # 예외 상황 처리
        return user_proxy
    
groupchat = autogen.GroupChat(
    agents=[user_proxy, resident1, resident2, medical_team_leader],   
    messages=[],
    speaker_selection_method=state_transition,
    allow_repeat_speaker=True,
    max_round = 6  # 6라운드로 증가 (전체 흐름 완주 가능)
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
                "content": "✅ 정답입니다! ALL TESTS PASSED !#!#"
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
    #message=PROMPT
    message={"role": "user", "content": PROMPT})

#print(assistant.chat_messages)


##############################
testbed_utils.finalize(agents=[user_proxy, resident1, resident2, medical_team_leader, manager])