import os
import json
from datetime import datetime
from pathlib import Path

# === Memory Paths ===
MEMORY_DIR = Path("/tmp")  # Runtime-safe dir for Cloud Run etc.
FALLBACK_DIR = Path("core/memory")  # Fallback for local/dev
AUDIT_PATH = FALLBACK_DIR / "audit_log.json"

# === User Memory Handling ===
def get_memory_path(username):
    return MEMORY_DIR / f"{username}.json"

def load_user_memory(username):
    path = get_memory_path(username)
    if not path.exists():
        return {
            "username": username,
            "activated_modules": [],
            "last_trigger": None,
            "batch": None,
            "role": None,
            "log": []
        }
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_user_memory(username, memory):
    path = get_memory_path(username)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2)

def log_to_memory(username, event):
    memory = load_user_memory(username)
    memory["log"].append({"time": datetime.utcnow().isoformat(), "event": event})
    save_user_memory(username, memory)

def update_module_state(username, module_name):
    memory = load_user_memory(username)
    if module_name not in memory["activated_modules"]:
        memory["activated_modules"].append(module_name)
    memory["last_trigger"] = module_name
    log_to_memory(username, f"Triggered module: {module_name}")
    save_user_memory(username, memory)

# === Generic Shard Writer ===
def write_to_shard(name, data):
    tmp_path = Path(f"/tmp/{name}.json")
    fallback_path = FALLBACK_DIR / f"{name}.json"

    try:
        log = json.loads(tmp_path.read_text()) if tmp_path.exists() else []
        log.append(data)
        tmp_path.write_text(json.dumps(log, indent=2))
        return
    except Exception as e:
        print(f"⚠️ Failed to write to /tmp shard: {e}")

    try:
        FALLBACK_DIR.mkdir(parents=True, exist_ok=True)
        log = json.loads(fallback_path.read_text()) if fallback_path.exists() else []
        log.append(data)
        fallback_path.write_text(json.dumps(log, indent=2))
    except Exception as e:
        print(f"❌ Failed to write to fallback shard: {e}")

# === Audit Log ===
def store_audit_log(entry):
    try:
        FALLBACK_DIR.mkdir(parents=True, exist_ok=True)

        if not AUDIT_PATH.exists():
            with open(AUDIT_PATH, "w") as f:
                json.dump([], f)

        with open(AUDIT_PATH, "r") as f:
            logs = json.load(f)

        logs.append({
            "timestamp": datetime.utcnow().isoformat(),
            "entry": entry
        })

        with open(AUDIT_PATH, "w") as f:
            json.dump(logs, f, indent=2)

    except Exception as e:
        print(f"⚠️ Failed to store audit log: {e}")


def write_drift_memory(symbolic_data):
    path = "/tmp/working_memory.json"
    
    # Load existing memory or start fresh
    memory = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                memory = json.load(f)
        except Exception as e:
            print(f"[write_drift_memory] Error loading memory: {e}")
            memory = {}

    # Append symbolic data
    memory.setdefault("drift_threads", []).append(symbolic_data)

    # Save updated memory
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(memory, f, indent=2)
    except Exception as e:
        print(f"[write_drift_memory] Error writing memory: {e}")


