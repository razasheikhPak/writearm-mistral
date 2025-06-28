import json
from datetime import datetime
from pathlib import Path

FORGIVENESS_LOG_PATH = "core/memory/forgiveness_log.json"

def log_friction_event(user_input, reason):
    log = []
    path = Path(FORGIVENESS_LOG_PATH)
    if path.exists():
        log = json.loads(path.read_text())
    log.append({
        "timestamp": datetime.utcnow().isoformat(),
        "user_input": user_input,
        "reason": reason
    })
    path.write_text(json.dumps(log, indent=2))

def run_forgiveness_cycle():
    path = Path(FORGIVENESS_LOG_PATH)
    if not path.exists():
        return None
    log = json.loads(path.read_text())
    cleared = []
    for entry in log:
        cleared.append({
            "released": entry["user_input"],
            "learning": "Clarity gained from emotional residue.",
            "timestamp": datetime.utcnow().isoformat()
        })
    path.write_text(json.dumps([], indent=2))  # Clear old entries
    return cleared
