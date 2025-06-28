import json
import os

def load_token_config():
    path = os.path.join(os.path.dirname(__file__), '..', 'MatrixOS_TokenBridge', 'token_config.json')
    #path="MatrixOS_TokenBridge/token_config.json"
    with open(path, 'r') as f:
        data = json.load(f)

    # Ensure required keys are present
    data.setdefault("symbols", {})
    data.setdefault("flags", {})
    data.setdefault("memory", [])

    # Set defaults for all known flags
    default_flags = {
        "matrix_time": False,
        "conversational_core": False,
        "copy_feedback": False,
        "linguistic_embed": False,
        "emotional_layer": False,
        "cro_max": False,
        "file_ingest": False,
        "token_opt": False,
        "memory_checkpoint": False,
        "structural_append_only": False
    }
    for key, val in default_flags.items():
        data["flags"].setdefault(key, val)

    return data


def save_token_config():
    try:
        path = os.path.join(os.path.dirname(__file__), '..', 'MatrixOS_TokenBridge', 'token_config.json')
        with open(path, 'w') as f:
            json.dump(CONFIG, f, indent=2)
    except OSError:
        print("⚠️ MatrixBot is running in read-only mode. Skipping config write.")

def log_token_compression(prompt_text, result_text):
    token_diff = len(prompt_text.split()) - len(result_text.split())
    print(f"[Token Compression] Input: {len(prompt_text.split())} tokens → Output: {len(result_text.split())} tokens | Δ = {token_diff}")




CONFIG = load_token_config()
CONFIG["flags"]["matrix_time"] = True
#save_token_config()