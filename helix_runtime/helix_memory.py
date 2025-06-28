# helix_memory.py

import json
from datetime import datetime

class HelixMemory:
    def __init__(self, session_id=None, memory_path=None):
        if memory_path:
            self.memory_path = memory_path
        elif session_id:
            self.memory_path = f"/mnt/data/memory/helix_{session_id}.json"
        else:
            raise ValueError("You must provide either session_id or memory_path")

        self.session_id = session_id or "anonymous"
        self.memory = self._load()

    def _load(self):
        try:
            with open(self.memory_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"beliefs": [], "drift_threads": [], "symbolic_tags": {}}

    def save(self):
        with open(self.memory_path, "w") as f:
            json.dump(self.memory, f, indent=2)

    def add_belief(self, belief):
        self.memory["beliefs"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "belief": belief
        })
        self.save()

    def log_drift(self, note):
        self.memory["drift_threads"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "note": note
        })
        self.save()

    def tag_symbolic(self, tags):
        self.memory["symbolic_tags"].update(tags)
        self.save()

    def export_summary(self):
        return {
            "belief_count": len(self.memory["beliefs"]),
            "drift_logs": self.memory["drift_threads"][-2:],
            "symbolic": self.memory["symbolic_tags"]
        }

    def summary(self, n=2):
        return {
            "recent_beliefs": self.memory["beliefs"][-n:],
            "recent_drift": self.memory["drift_threads"][-n:]
        }

    def generate_symbolic_prompt(self, user_input):
        # Fallback implementation (can improve later)
        prompt = {
            "prompt": f"[SYMBOLIC] Detected pattern in: {user_input}",
            "tags": {
                "persona": "Thea",
                "mu": "symbolic",
                "epoch": "v1"
            },
            "matrix_id": "Thea-Symbolic-v1"
        }
        return prompt, f"Resolved symbolic pattern: {prompt['prompt']}"

