# File: core/payload_loader.py
# Purpose: Load and interpret MatrixOS_TransferPayload_v2_FULL.docx line-by-line

from docx import Document
from core.cml_interpreter import interpret
import os
from pathlib import Path
import json
import yaml

MEMORY_FILE = "core/memory.txt"
PROMPT_LIBRARY = []


def load_payload_lines(docx_path):
    doc = Document(docx_path)
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]


def already_in_memory(symbol):
    if not os.path.exists(MEMORY_FILE):
        return False
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return symbol in f.read()


def append_to_memory(symbol):
    with open(MEMORY_FILE, "a", encoding="utf-8") as f:
        f.write(symbol + "\n")


def execute_payload(docx_path):
    lines = load_payload_lines(docx_path)
    for line in lines:
        if not already_in_memory(line):
            print(f"Executing: {line}")
            interpret(line)
            append_to_memory(line)

def load_prompt_library():
    global PROMPT_LIBRARY
    try:
        path = Path("MatrixOS-Core/prompts.jsonl")
        with open(path, "r") as f:
            PROMPT_LIBRARY = [json.loads(line) for line in f.readlines()]
        print(f"[✅] Loaded {len(PROMPT_LIBRARY)} prompts from prompts.jsonl")
    except Exception as e:
        print(f"[⚠️] Failed to load prompts: {e}")

HELIX_RUNTIME_PATH = "./MatrixOS-Core/helixmind_runtime.symbolic"

def load_helixmind_runtime():
    """
    Loads HelixMind symbolic control structure from file.
    """
    try:
        with open(HELIX_RUNTIME_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data or {}
    except FileNotFoundError:
        print("[load_helixmind_runtime] Runtime file missing.")
        return {}
    except yaml.YAMLError as e:
        print(f"[load_helixmind_runtime] YAML load error: {e}")
        return {}


# Optional CLI usage
if __name__ == "__main__":
    execute_payload("MatrixOS_TransferPayload_v2_FULL.docx")
