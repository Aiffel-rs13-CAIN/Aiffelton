#!/usr/bin/env python3
import os
import sys
import json
import zipfile
import pathlib

# Setup paths
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_DIR = ROOT / "Data"
TASKS_DIR = ROOT / "Tasks"

def log(m):
    print(f"[init_tasks] {m}")

def prep_data_source():
    """Checks for data, and unzips if necessary. Returns the path to the source file or None."""
    zip_path = DATA_DIR / "medqa_raw.zip"
    unzipped_dir = DATA_DIR / "data_clean"
    source_file = unzipped_dir / "questions" / "US" / "4_options" / "phrases_no_exclude_test.jsonl"

    if source_file.exists():
        log(f"Source file found: {source_file}")
        return source_file

    if not unzipped_dir.exists():
        log(f"Unzipped data directory not found at {unzipped_dir}.")
        if zip_path.exists():
            log(f"Found zip file at {zip_path}. Unzipping...")
            try:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(DATA_DIR)
                log(f"Successfully unzipped to {DATA_DIR}")
            except Exception as e:
                log(f"ERROR: Failed to unzip {zip_path}. Error: {e}")
                return None
        else:
            log(f"ERROR: Raw data zip not found at {zip_path}.")
            log("Please download it from Google Drive (https://drive.google.com/file/d/1ImYUSLk9JbgHXOemfvyiDiirluZHPeQw/view) and save it.")
            return None

    if source_file.exists():
        log(f"Source file now available: {source_file}")
        return source_file
    else:
        log(f"ERROR: Source file not found even after unzipping: {source_file}")
        return None

def convert_to_autogenbench(source_file, output_file):
    """Converts the source jsonl file to the autogenbench format, filtering by step."""
    log(f"Converting {source_file} to {output_file} with step filtering...")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    count = 0
    filtered_out = 0
    with open(source_file, "r", encoding="utf-8") as fin, \
         open(output_file, "w", encoding="utf-8") as fout:
        for i, line in enumerate(fin):
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                log(f"Warning: Skipping malformed JSON on line {i+1}")
                continue

            meta_info = item.get("meta_info")
            if meta_info not in ["step2", "step3", "step2&3"]:
                filtered_out += 1
                continue

            question = item.get("question")
            options = item.get("options")
            answer_idx = item.get("answer_idx")

            if not all([question, options, answer_idx]):
                log(f"Warning: Skipping incomplete record on line {i+1}")
                continue

            options_text = "\n".join([f"{k}. {v}" for k, v in sorted(options.items())])
            prompt_text = f"{question}\n\nOptions:\n{options_text}\n\nChoose A, B, C, or D."

            autogen_entry = {
                "id": item.get("id", f"medqa_{i}"),
                "template": "../Templates/single_llm",
                "substitutions": {
                    "scenario.py": {
                        "__SELECTION_METHOD__": "auto"
                    },
                    "prompt.txt": {
                        "__PROMPT__": prompt_text
                    },
                    "answer.txt": {
                        "__ANSWER__": answer_idx,
                    }
                }
            }

            fout.write(json.dumps(autogen_entry, ensure_ascii=False) + "\n")
            count += 1
    log(f"Successfully converted {count} records. (Filtered out {filtered_out} records)")

def main():
    """Main execution flow."""
    log("Starting task initialization...")
    
    source_file_path = prep_data_source()
    
    if not source_file_path:
        log("Could not prepare data source. Exiting.")
        return

    output_task_file = TASKS_DIR / "medqa_single_llm.jsonl"
    convert_to_autogenbench(source_file_path, output_task_file)
    
    log("Script finished.")

if __name__ == "__main__":
    main()
