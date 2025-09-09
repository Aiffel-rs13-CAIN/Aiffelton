# -*- coding: utf-8 -*-
"""
Scenario 1: Baseline — Single LLM solves MedQA alone.
- Reads prompt.txt, answer.txt
- Produces metrics.json (essential + study-core compatible fields).
"""
import os, re, json, time, sys
import autogen
import testbed_utils

_SELECTION_METHOD = "__SELECTION_METHOD__"
MODEL_SOLO = "gemini-2.0-flash-lite"

# Regular expressions for parsing
LETTER_RE = re.compile(r"\b([A-D])\b", re.IGNORECASE)
HDR_PROPOSAL_RE = re.compile(r"^\s*Answer:\s*([A-D])\s*$", re.IGNORECASE | re.MULTILINE)
CONF_RE = re.compile(r"^\s*Confidence\s*:\s*([0-1](?:\.\d+)?)\s*$", re.IGNORECASE | re.MULTILINE)

def now_s(): 
    return time.time()

def elapsed_s(t0): 
    return max(0.0, time.time()-t0)
# Read problem and ground truth
with open("prompt.txt","r",encoding="utf-8") as f:
    PROBLEM = f.read().strip()
with open("answer.txt","r",encoding="utf-8") as f:
    GT = (LETTER_RE.search((f.read() or "").upper()) or [None,""])[1]

def _parse_conf(text: str):
    """Parse confidence from text."""
    if not text:
        return None
    m = CONF_RE.search(text)
    if not m: 
        return None
    try:
        v = float(m.group(1))
        if 0.0 <= v <= 1.0: 
            return v
    except (ValueError, AttributeError): 
        pass
    return None

def parse_first_line_and_conf(text: str):
    """Parse answer choice and confidence from response text."""
    if not text: 
        return None, None
    
    # First try to find structured answer format
    m = HDR_PROPOSAL_RE.search(text)
    if m: 
        return m.group(1).upper(), _parse_conf(text)
    
    # Fallback to any letter match
    m = LETTER_RE.search(text)
    return (m.group(1).upper(), _parse_conf(text)) if m else (None, _parse_conf(text))

def extract_usage_from_agent(agent):
    """Extract token usage and cost from agent."""
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "cost": 0.0}
    try:
        # 1. agent.client._client_usage 딕셔너리에서 직접 사용량 정보 가져오기
        if hasattr(agent, 'client') and hasattr(agent.client, '_client_usage'):
            for model_name, usage_data in agent.client._client_usage.items():
                if isinstance(usage_data, dict):
                    usage['prompt_tokens'] += usage_data.get('prompt_tokens', 0)
                    usage['completion_tokens'] += usage_data.get('completion_tokens', 0)
                    usage['total_tokens'] += usage_data.get('total_tokens', 0)
                    usage['cost'] += usage_data.get('cost', 0.0)
            if usage['total_tokens'] > 0:
                return usage

        # 2. (fallback) agent._oai_messages에서 usage 필드 탐색
        if hasattr(agent, '_oai_messages'):
            for message in agent._oai_messages:
                if 'usage' in message:
                    msg_usage = message['usage']
                    return {
                        "prompt_tokens": msg_usage.get('prompt_tokens', 0),
                        "completion_tokens": msg_usage.get('completion_tokens', 0),
                        "total_tokens": msg_usage.get('total_tokens', 0),
                        "cost": msg_usage.get('total_cost', 0.0)
                    }
    except Exception as e:
        print(f"Warning: Could not extract usage from agent: {e}")
    return usage

# System message 
SOLO_DOCTOR_PROMPT = """
You are an experienced Generalist Physician. Your task is to independently analyze the following medical case and determine the most likely answer.

Analyze the case comprehensively. Apply your medical knowledge to systematically evaluate each answer choice. Provide a definitive, evidence-based conclusion.

**CRITICAL: RESPONSE FORMAT**
Your entire response must strictly follow this format:
The FIRST line MUST be: `Answer: <A/B/C/D>`
The SECOND line MUST be: `Confidence: <0~1>`
The rest of your response is your concise rationale (2-4 sentences).
"""

# Initialize testbed utilities
testbed_utils.init()

# Get configuration from autogenbench environment - proper way
def get_env_or_default(env_keys, default_value):
    """Get environment variable with multiple possible keys."""
    for key in env_keys:
        value = os.environ.get(key)
        if value is not None:
            return value
    return default_value

# 환경 변수가 없을 경우 폴더 구조에서 정보를 추출하는 함수
def get_info_from_path():
    path_parts = os.getcwd().split(os.path.sep)
    try:
        results_index = path_parts.index("results") # 소문자 'results'
        experiment = path_parts[results_index + 1]
        task = path_parts[results_index + 2]
        instance = path_parts[results_index + 3]
        repetition = int(path_parts[results_index + 4])
        return experiment, task, instance, repetition
    except (ValueError, IndexError):
        return None, None, None, None

path_exp_id, path_task_id, path_instance_id, path_repetition = get_info_from_path()

# Get autogenbench metadata - standard environment variables
experiment_id = get_env_or_default(["AUTOGENBENCH_EXPERIMENT_ID", "EXP_ID"], path_exp_id or "unknown")
task_id = get_env_or_default(["AUTOGENBENCH_TASK_ID", "TASK_ID"], path_task_id or "unknown")
instance_id = get_env_or_default(["AUTOGENBENCH_TESTBED_INSTANCE_ID", "QUESTION_ID", "INSTANCE_ID"], path_instance_id or "unknown_instance")
repetition = int(get_env_or_default(["AUTOGENBENCH_REPETITION", "REPETITION"], path_repetition or 0))

scenario_id = int(get_env_or_default([
    "AUTOGEN_TESTBED_SCENARIO_ID",
    "AUTOGENBENCH_SCENARIO_ID", 
    "SCENARIO_ID"
], "1"))

dataset_name = get_env_or_default([
    "AUTOGEN_TESTBED_DATASET",
    "AUTOGENBENCH_DATASET",
    "DATASET"
], "Unknown")

# Load model configuration
try:
    config_list_solo = autogen.config_list_from_json("OAI_CONFIG_LIST", filter_dict={"model":[MODEL_SOLO]})
        
except Exception as e:
    print(f"Error loading model configuration: {e}")
    print("Please ensure OAI_CONFIG_LIST file exists and contains valid model configurations")
    sys.exit(1)

# Get LLM config using testbed utilities
llm_config_solo = testbed_utils.default_llm_config(config_list_solo)

# Create agents
solo = autogen.AssistantAgent(
    name="Doctor_Solo",
    system_message=SOLO_DOCTOR_PROMPT,
    llm_config=llm_config_solo,
)

user = autogen.UserProxyAgent(
    name="user",
    human_input_mode="NEVER",
    is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    max_consecutive_auto_reply=10,
    default_auto_reply="TERMINATE",
    code_execution_config=False
)

# Prepare problem message
problem_msg = f"MedQA Item:\n{PROBLEM}\n\nProvide your final answer in the specified format."

# Execute scenario
t0 = now_s()

try:
    chat_result = user.initiate_chat(solo, message=problem_msg)
    success = True
    
except Exception as e:
    print(f"Error during chat: {e}")
    chat_result = None
    success = False

elapsed_time = elapsed_s(t0)

# Extract final response from chat history
final_choice = None
conf = None
final_msg = ""
correct = 0

if success and chat_result:
    # 대화 기록(chat_history)을 역순으로 탐색하여 Doctor_Solo의 마지막 응답을 찾습니다.
    final_msg = ""
    for message in reversed(chat_result.chat_history):
        if message.get("name") == "Doctor_Solo":
            final_msg = message.get("content", "")
            break

    # 최종 메시지가 발견되면 파싱을 진행합니다.
    if final_msg:
        final_choice, conf = parse_first_line_and_conf(final_msg)
        correct = int(bool(final_choice and GT and final_choice == GT))
    else:
        print("Warning: Doctor_Solo's final message was not found in chat history.")

# Extract usage information
usage_info = extract_usage_from_agent(solo)

# Estimate rationale tokens
rationale_tokens = len(final_msg.split()) if final_msg else None

# Build metrics following autogenbench standard format
metrics = {
    "meta": {
        "experiment_id": experiment_id,
        "task_id": task_id,
        "scenario_id": scenario_id,
        "scenario_desc": "Baseline single LLM",
        "dataset": dataset_name,
        "instance_id": instance_id,
        "repetition": repetition,
        "order_permutation": None,
        "conflict_injection": {
            "level": "none",
            "agents": [],
            "seed": None
        },
        "manager_policy": "solo",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "autogenbench_version": get_env_or_default(["AUTOGENBENCH_VERSION"], "0.0.3"),
        "pyautogen_version": get_env_or_default(["PYAUTOGEN_VERSION"], "0.2.35"),
        "success": success
    },

    "models": {
        "Doctor_Solo": {
            "role": "generalist",
            "model": MODEL_SOLO,
            "config": {
                "temperature": llm_config_solo.get("temperature"),
                "max_tokens": llm_config_solo.get("max_tokens"),
                "cache_seed": llm_config_solo.get("cache_seed")
            }
		}
	},
	"scenario_params": {
	    "selection_method": os.environ.get("SELECTION_METHOD", "single_agent"),
	    "max_turns": 1,
	    "termination_condition": "single_response"
    },
    
    "per_agent": {
        "Doctor_Solo": {
            "initial": {
                "choice": final_choice,
                "confidence": conf,
                "rationale_tokens": rationale_tokens,
                "response_text": final_msg
            },
            "final": {
                "choice": final_choice,
                "confidence": conf
            },
            "changed_answer": False,
            "turns_spoken": 1 if success else 0,
            "persuaded_by": [],
            "disagreement_edges": []
        }
    },
    "manager": {
        "decision_rule": "solo",
        "final_decision": final_choice,
        "final_confidence": conf,
        "overrode_majority": False,
        "consensus_reached": True if final_choice else False,
        "consensus_turn": 1 if final_choice else None,
    },
    "ground_truth": GT,
    "evaluation": {
        "correct": correct,
        "per_agent_correct": {
            "Doctor_Solo": correct
        },
        "initial_group_disagreement": 0,
        "total_disagreement_events": 0,
        "num_answer_flips": 0,
        "helpful_persuasion": 0,
        "harmful_persuasion": 0,
        "first_speaker_influence": {
            "aligned_with_final": True if final_choice else False,
            "alignment_agent": "Doctor_Solo",
            "alignment_mode": "direct"
        },
        "order_bias_probe": {
            "first_turn_weight_proxy": 1.0,
            "speak_order_rank_of_winner": 1
        }
    },
    "efficiency": {
		"wall_time_s": {"Doctor_Solo": elapsed_time, "total": elapsed_time},
        "token_usage": {
            "prompt_tokens": usage_info["prompt_tokens"] if usage_info["prompt_tokens"] > 0 else None,
            "completion_tokens": usage_info["completion_tokens"] if usage_info["completion_tokens"] > 0 else None,
            "total_tokens": usage_info["total_tokens"] if usage_info["total_tokens"] > 0 else None
        },
		"tokens_in":  {"Doctor_Solo": None, "total": None},
        "tokens_out": {"Doctor_Solo": None, "total": None},
		"cost_usd":   {"Doctor_Solo": usage_info["cost"] if usage_info["cost"] > 0 else None, 
						"total": usage_info["cost"] if usage_info["cost"] > 0 else None}
    },
    "debug": {
        "environment_snapshot": {
            k: v for k, v in os.environ.items() 
            if k.startswith(('AUTOGEN', 'OPENAI', 'MODEL', 'LLM'))
        },
        "parsing_results": {
            "choice_extracted": final_choice is not None,
            "confidence_extracted": conf is not None,
            "response_length": len(final_msg),
            "gt_available": GT is not None
        },
        "execution_status": {
            "chat_successful": success,
            "final_message_retrieved": bool(final_msg),
            "usage_extracted": any(v > 0 for v in usage_info.values())
        }
    }
}

# Write metrics to file
with open("metrics.json", "w", encoding="utf-8") as f:
    json.dump(metrics, f, default=str, ensure_ascii=False, indent=2)

# Standard autogenbench result reporting
if not success:
    print("EXECUTION_FAILED !#!#")
elif correct:
    print("ALL TESTS PASSED !#!#")
else:
    print(f"INCORRECT_ANSWER !#!# (final={final_choice or 'None'}, gt={GT})")

# Cleanup
try:
    testbed_utils.finalize(agents=[user, solo])
except Exception as e:
    print(f"Warning: Error during finalize: {e}")

print(f"=== END DEBUG ===")
