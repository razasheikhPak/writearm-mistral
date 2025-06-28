import os
import json
import yaml
from datetime import datetime

AGENT_DIR = "agents"

def spawn_agent(name, purpose, domain, base="TheaCore"):
    # Normalize name for folder and filename
    safe_name = name.lower().replace(" ", "_")

    agent_folder = os.path.join(AGENT_DIR, safe_name)
    os.makedirs(agent_folder, exist_ok=True)

    profile = {
        "name": name,
        "created": datetime.utcnow().isoformat(),
        "purpose": purpose,
        "inherits_from": base,
        "distinct_behavior": True,
        "tone_model": "LXB10k variant",
        "memory_path": f"/agents/{safe_name}/agent_memory.json",
        "domain": domain,
        "override_permissions": True
    }

    profile_path = os.path.join(agent_folder, f"agent_profile_{safe_name}.yaml")
    memory_path = os.path.join(agent_folder, "agent_memory.json")

    with open(profile_path, "w") as f:
        yaml.dump(profile, f, sort_keys=False)

    with open(memory_path, "w") as f:
        json.dump({"memory": []}, f, indent=2)

    return f"🧬 Spawned agent: `{name}` for domain: `{domain}` with purpose: `{purpose}`."
