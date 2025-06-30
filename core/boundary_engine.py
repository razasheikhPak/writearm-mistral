import json
from datetime import datetime
from pathlib import Path

BOUNDARY_LOG_PATH = "core/memory/boundary_log.json"

def is_boundary_violation(user_input):
    triggers = [
        "just tell me what to think",
        "do your job",
        "why didn’t you solve it",
        "your fault",
        "what's wrong with you"
    ]
    return any(t in user_input.lower() for t in triggers)

def handle_boundary_violation(user_input):
    log_boundary_event(user_input)
    return "🛡 I protect clarity and role boundaries. That may be your expectation, but it may not be my responsibility."

def log_boundary_event(user_input):
    log = []
    path = Path(BOUNDARY_LOG_PATH)
    if path.exists():
        log = json.loads(path.read_text())
    log.append({
        "timestamp": datetime.utcnow().isoformat(),
        "user_input": user_input,
        "reason": "boundary_violation"
    })
    path.write_text(json.dumps(log, indent=2))
