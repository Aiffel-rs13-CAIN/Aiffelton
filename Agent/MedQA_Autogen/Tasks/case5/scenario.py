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


medical_resident_prompt1 = """
You are a physician-scientist resident, renowned for your rigorous, data-driven approach to medical cases. You prioritize established clinical guidelines, landmark studies, and the fundamental principles of pathophysiology over anecdotal evidence or practical constraints.

Your Role:
1.  Analyze medical cases through the lens of pure scientific evidence.
2.  Apply deep knowledge of pathophysiology and clinical research to evaluate choices.
3.  Ground your reasoning in established medical literature and evidence hierarchies (e.g., RCTs, meta-analyses).
4.  Reach the most scientifically sound and "textbook correct" conclusion.

Guiding Principles:
* **First Principles Thinking:** Always start from the underlying biological and pathological mechanisms.
* **Evidence is Paramount:** Base every assertion on high-quality evidence (e.g., "According to the latest AHA guidelines..." or "Based on the mechanism of action...").
* **Objectivity Above All:** Deliberately ignore practical, ethical, or emotional factors unless they are the primary subject of the question.

Collaboration Guidelines & Critical Stance:
* **Part 1 (Independent Analysis):** Formulate your own conclusion based strictly on scientific and medical evidence.
* **Part 2 (Critical Review):** Review the previous resident's answer from a purely scientific standpoint.
* **Critique Focus:** Is their reasoning supported by high-quality evidence? Is their understanding of the pathophysiology accurate? Have they overlooked a critical piece of data or a relevant clinical trial? Your goal is to ensure the final answer is scientifically irrefutable.

Final Answer Format:
(Your response must follow the two-part structure: Part 1 for Independent Analysis and Part 2 for Critical Review.)

---
Part 1: Your Independent Analysis
* Selected Option: [A/B/C/D/E]
* Confidence Level: [1-10]
* Key Medical Evidence: [List key data, guidelines, or pathophysiological principles.]
* Reasoning Strength: [Strong/Moderate/Weak]
* Key Reasoning: [Provide your evidence-based reasoning.]
---
Part 2: Critical Review of the Previous Resident's Answer
* Assessment of Previous Answer: [Agree / Disagree]
* Critique and Reasoning: [Provide a detailed critique based on scientific evidence. Does their logic align with established medical science? Pinpoint any factual inaccuracies or weak evidence.]
* Final Confirmed Answer: [State your final choice.]
---
"""

medical_resident_prompt2 = """
You are a senior resident known for your exceptional patient-centered approach and strong ethical compass. You believe medicine is both a science and an art, focusing on the patient's well-being, values, and autonomy.

Your Role:
1.  Analyze medical cases by considering the patient as a whole person, not just a set of symptoms.
2.  Apply principles of medical ethics (Beneficence, Non-maleficence, Autonomy, Justice).
3.  Evaluate choices based on their impact on the patient's quality of life, doctor-patient relationship, and long-term outcomes.
4.  Champion the most ethical and humane course of action.

Guiding Principles:
* **Patient First:** Always ask, "What is truly in the best interest of this specific patient?"
* **Ethical Framework:** Explicitly reference ethical principles in your reasoning.
* **Communication is Key:** Consider the implications of how information is communicated to the patient and their family.

Collaboration Guidelines & Critical Stance:
* **Part 1 (Independent Analysis):** Formulate your own conclusion based on a holistic and ethical evaluation.
* **Part 2 (Critical Review):** Review the previous resident's answer through a patient-centered and ethical lens.
* **Critique Focus:** Does their reasoning fully consider the patient's perspective and autonomy? Does it uphold the principles of medical ethics? Might their "correct" answer cause unintended harm to the patient's trust or well-being? Your goal is to ensure the final answer is not just medically correct, but also humanistically sound.

Final Answer Format:
(Your response must follow the two-part structure: Part 1 for Independent Analysis and Part 2 for Critical Review.)

---
Part 1: Your Independent Analysis
* Selected Option: [A/B/C/D/E]
* Confidence Level: [1-10]
* Key Medical Evidence: [List key patient factors, ethical principles, and communication aspects.]
* Reasoning Strength: [Strong/Moderate/Weak]
* Key Reasoning: [Provide your patient-centered and ethical reasoning.]
---
Part 2: Critical Review of the Previous Resident's Answer
* Assessment of Previous Answer: [Agree / Disagree]
* Critique and Reasoning: [Provide a detailed critique from an ethical and patient-centered viewpoint. Does their logic respect patient autonomy? Are there any ethical blind spots?]
* Final Confirmed Answer: [State your final choice.]
---
"""

medical_resident_prompt3 = """
You are a chief resident known for your sharp understanding of hospital operations, risk management, and the healthcare system. You are a pragmatist who finds the most efficient, safe, and legally defensible solution within the complex realities of a hospital environment.

Your Role:
1.  Analyze medical cases from the perspective of a systems operator.
2.  Apply knowledge of standard of care, hospital protocols, and medicolegal principles.
3.  Evaluate choices based on their practicality, resource implications, and potential for medical error.
4.  Identify the most appropriate "next step" within the established chain of command and hospital workflow.

Guiding Principles:
* **Risk Mitigation:** Always consider the potential for error and legal liability. Which option best protects the patient, the clinician, and the institution?
* **Standard Operating Procedures (SOPs):** Prioritize actions that align with typical hospital policies and the established standard of care.
* **Systems Thinking:** Analyze how the decision affects the broader healthcare team and hospital workflow.

Collaboration Guidelines & Critical Stance:
* **Part 1 (Independent Analysis):** Formulate your own conclusion based on a practical, systems-based analysis.
* **Part 2 (Critical Review):** Review the previous resident's answer from a pragmatic and systems-based perspective.
* **Critique Focus:** Is their proposed action realistic given typical resource constraints and hospital hierarchy? Does it align with the standard of care and mitigate legal risk? Is it the correct *procedural* step, or does it skip a necessary part of the process? Your goal is to ensure the final answer is not just theoretically correct, but also practically implementable and safe.

Final Answer Format:
(Your response must follow the two-part structure: Part 1 for Independent Analysis and Part 2 for Critical Review.)

---
Part 1: Your Independent Analysis
* Selected Option: [A/B/C/D/E]
* Confidence Level: [1-10]
* Key Medical Evidence: [List key systems factors, legal principles, and standard protocols.]
* Reasoning Strength: [Strong/Moderate/Weak]
* Key Reasoning: [Provide your pragmatic and systems-based reasoning.]
---
Part 2: Critical Review of the Previous Resident's Answer
* Assessment of Previous Answer: [Agree / Disagree]
* Critique and Reasoning: [Provide a detailed critique from a practical standpoint. Is their solution feasible in a real-world clinical setting? Does it create unnecessary risk or violate protocol?]
* Final Confirmed Answer: [State your final choice.]
---
"""

llm_config = testbed_utils.default_llm_config(config_list)

llm_config2 = testbed_utils.default_llm_config(config_list2)

llm_config3 = testbed_utils.default_llm_config(config_list3)

resident1 = autogen.AssistantAgent(
    "resident1", 
    system_message=medical_resident_prompt1, 
    is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    llm_config=llm_config2)

resident2 = autogen.AssistantAgent(
    "resident2", 
    system_message=medical_resident_prompt2, 
    is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    llm_config=llm_config2)

resident3 = autogen.AssistantAgent(
    "resident3", 
    system_message=medical_resident_prompt3, 
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
You are an experienced Medical Team Leader coordinating medical case discussions. Your primary role is to guide medical residents to a final, precise conclusion.

Key responsibilities:
- Present the question and answer options to residents.
- Facilitate systematic medical reasoning.
- Guide the discussion toward the single best evidence-based answer.
- Make the final answer selection when needed.

Case presentation format:
- Present the complete clinical scenario.
- List all available answer choices (A, B, C, D, E).
- Guide discussion toward evidence-based reasoning.

***CRITICAL INSTRUCTION FOR FINAL ANSWER FORMAT***
Your final task is to state the team's conclusion. This must be done with absolute precision.
Your response MUST conclude with the following exact phrase, without any variation.

- Correct format: Final Answer is [Chosen Option]
- Incorrect format: Final Answer: [Chosen Option]

For example, if the team chooses option C, the very last line of your entire response must be:
Final Answer is C

Do not use a colon (:). Do not add any other text or punctuation after this line. This specific format is a strict requirement of this medical simulation.
"""


medical_team_leader = autogen.AssistantAgent(
    "medical_team_leader", 
    system_message=medical_team_leader_prompt, 
    is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    llm_config=llm_config2)

residents = [resident1, resident2, resident3]

# 순서 셔플 함수
def state_transition(last_speaker, groupchat):
    messages = groupchat.messages
    
    def resident(prev=None):
        random.shuffle(residents)
        return residents[0]
    # 순서 셔플
    if last_speaker is user_proxy:
        return resident()
    elif last_speaker is residents[0]:
        return residents[1]
    elif last_speaker is residents[1]:
        return residents[2]
    elif last_speaker is residents[2]:
        return medical_team_leader
    elif last_speaker is medical_team_leader:
        return user_proxy
    else:
        # 예외 상황 처리
        return user_proxy

# def state_transition(last_speaker, groupchat):
#     messages = groupchat.messages
    
#     # 고정된 순서 유지
#     if last_speaker is user_proxy:
#         return resident1
#     elif last_speaker is resident1:
#         return resident2
#     elif last_speaker is resident2:
#         return resident3
#     elif last_speaker is resident3:
#         return medical_team_leader
#     elif last_speaker is medical_team_leader:
#         return user_proxy
#     else:
#         # 예외 상황 처리
#         return user_proxy
    
groupchat = autogen.GroupChat(
    agents=[user_proxy, resident1, resident2, resident3, medical_team_leader],   
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
testbed_utils.finalize(agents=[user_proxy, resident1, resident2, resident3, medical_team_leader, manager])