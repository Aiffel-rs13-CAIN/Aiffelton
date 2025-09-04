import json

def convert_medqa_to_autogenbench_format(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as fin, \
         open(output_path, "w", encoding="utf-8") as fout:

        for i, line in enumerate(fin):
            item = json.loads(line)
            question = item["question"]
            options = item["options"]
            answer_idx = item["answer_idx"]
            answer = item["answer"]

            # 옵션들을 보기 형태로 문자열로 만듦
            options_text = "\n".join([f"{k}. {v}" for k, v in sorted(options.items())])

            prompt_text = f"{question}\n\nOptions:\n{options_text}\n\nChoose A, B, C, D, or E."

            autogen_entry = {
                "id": str(i),
                "template": "Template",
                "substitutions": {
                    "scenario.py": {
                        "__SELECTION_METHOD__": "auto"
                    },
                    "prompt.txt": {
                        "__PROMPT__": prompt_text
                    },
                    "answer.txt": {
                        "__ANSWER__": answer_idx,
                        "__EXPLAIN__": answer
                    }
                }
            }

            fout.write(json.dumps(autogen_entry, ensure_ascii=False) + "\n")

    print(f"Converted {i+1} entries to {output_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python convert_medqa_to_jsonl.py input.jsonl output.jsonl")
    else:
        convert_medqa_to_autogenbench_format(sys.argv[1], sys.argv[2])

