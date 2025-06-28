import os
import json
import re

BELIEF_DIR = "/tmp/beliefs"

# Ensure beliefs folder exists
os.makedirs(BELIEF_DIR, exist_ok=True)

# Detect belief statements using varied phrasing
BELIEF_PATTERNS = [
    r"(?:remember|save|store|log|keep|note)\s+(?:this|that)?[:\-–>\s]*([\w\"'].+)",
    r"(?:save|remember|log).*?to memory[:\-–>\s]*([\w\"'].+)",
    r"save_belief::\s*(.+)"
]

def extract_belief(text):
    for pattern in BELIEF_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None

def persist_user_belief(user_id, belief_text):
    if not belief_text:
        return
    belief_file = os.path.join(BELIEF_DIR, f"{user_id}_beliefs.json")
    if os.path.exists(belief_file):
        with open(belief_file, "r") as f:
            beliefs = json.load(f)
    else:
        beliefs = []

    if belief_text not in beliefs:
        beliefs.append(belief_text)
        with open(belief_file, "w") as f:
            json.dump(beliefs, f, indent=2)

def load_user_beliefs(user_id):
    belief_file = os.path.join(BELIEF_DIR, f"{user_id}_beliefs.json")
    if os.path.exists(belief_file):
        with open(belief_file, "r") as f:
            return json.load(f)
    return []
