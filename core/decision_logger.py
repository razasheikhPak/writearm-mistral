import json
import os
from datetime import datetime
from hashlib import sha1

DECISION_FILE = "memory/decision_journal.json"

def log_decision(input_text, module, tone, follow_up):
    if not os.path.exists(DECISION_FILE):
        data = {"decisions": []}
    else:
        with open(DECISION_FILE, "r") as f:
            data = json.load(f)
    
    decision_id = sha1(f"{input_text}{datetime.utcnow()}".encode()).hexdigest()[:8]
    entry = {
        "id": decision_id,
        "timestamp": datetime.utcnow().isoformat(),
        "input": input_text,
        "module": module,
        "tone": tone,
        "follow_up": follow_up,
        "pattern_hash": sha1(input_text.encode()).hexdigest()[:6]
    }

    data["decisions"].append(entry)

    with open(DECISION_FILE, "w") as f:
        json.dump(data, f, indent=2)
