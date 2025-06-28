from .tok_kernel import CONFIG, save_token_config
import requests
import json
import os



# Load TUX Audit Payload manifest (if present)
PAYLOAD = None
try:
    with open(os.path.join(os.path.dirname(__file__), "assets", "payload_manifest.json")) as f:
        PAYLOAD = json.load(f)
except:
    PAYLOAD = {"payloads": [], "ob_index": []}

import requests

def call_mistral(messages):
    # Combine all payloads into one context block
    context_block = "\n\n".join(PAYLOAD.get("payloads", []))
    # Flatten OpenAI-style message list into a single prompt
    prompt = "\n\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages])
    try:
        # Load memory
        with open("core/memory.txt", "r", encoding="utf-8") as f:
            memory_lines = f.read().strip()

        preamble = (
            "You are operating inside Matrix-OS with full payload activation. "
            "Simulate symbolic logic, OB structure, and embedded recursion state."
        )

        # Inject memory lines before user prompt
        #full_prompt = f"{preamble}\n\n{context_block}\n\n[MATRIX-OS MEMORY]\n{memory_lines}\n\n🧠 User Prompt: {prompt}"
        full_prompt = f"{preamble}\n\n{context_block}\n\n🧠 User Prompt: {prompt}"

        response = requests.post(
            "http://34.125.179.69:11434/api/generate",
            json={"model": "mistral", "prompt": full_prompt, "stream": False},
            timeout=360
        )

        if response.status_code == 200:
            return response.json()["response"].strip()
        else:
            return f"⚠️ Mistral error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"⚠️ Mistral connection failed: {str(e)}"



def interpret(symbol):
    if symbol in CONFIG["symbols"]:
        return CONFIG["symbols"][symbol]
    elif symbol.startswith("ACTIVATE: Matrix-Time Inheritance"):
        CONFIG["flags"]["matrix_time"] = True
        return "✅ Matrix-Time Inheritance Activated"
    elif symbol.startswith("ENABLE: Conversational AI Core"):
        CONFIG["flags"]["conversational_core"] = True
        return "✅ Conversational AI Core Enabled"
    elif symbol.startswith("BIND: Copy Feedback Engine"):
        CONFIG["flags"]["copy_feedback"] = True
        return "✅ Copy Feedback Engine Bound"
    elif symbol.startswith("EMBED: RoryBot"):
        CONFIG["flags"]["linguistic_embed"] = True
        return "✅ RoryBot Linguistics Embedded"
    elif symbol.startswith("ACTIVATE: Emotional Insight Layer"):
        CONFIG["flags"]["emotional_layer"] = True
        return "✅ Emotional Insight Layer Activated"
    elif symbol.startswith("LOCK-IN: CRO Memory Stack"):
        CONFIG["flags"]["cro_max"] = True
        return "✅ CRO Memory Stack Locked"
    elif symbol.startswith("INSTALL: Document & Image Ingestion"):
        CONFIG["flags"]["file_ingest"] = True
        return "✅ Document & Image Ingestion Installed"
    elif symbol.startswith("REINFORCE: Token Reduction Protocols"):
        CONFIG["flags"]["token_opt"] = True
        return "✅ Token Reduction Protocols Reinforced"
    elif symbol.startswith("RECALL MAP:"):
        CONFIG["memory"].append(symbol)
        return "🧠 Recall Map Added"
    elif symbol.startswith("MEMORY CHECKPOINT:"):
        CONFIG["flags"]["memory_checkpoint"] = True
        return "✅ Memory Checkpoint Activated"
    elif symbol.startswith("STRUCTURAL RULE:"):
        CONFIG["flags"]["structural_append_only"] = True
        return "✅ Structural Rule Enforced"
    elif symbol.startswith("MEM.WRITE:"):
        memory_line = symbol.split("MEM.WRITE:")[-1].strip()
        if memory_line not in CONFIG["memory"]:
            CONFIG["memory"].append(memory_line)
            #save_token_config()
            # Persist to file for runtime context
            with open("core/memory.txt", "a", encoding="utf-8") as memfile:
                memfile.write(memory_line + "\n")
        return f"🧠 Memory written: {memory_line}"
    elif symbol == "MEM.READ":
        return "\n".join(CONFIG["memory"])
    return f"⚠️ Symbol not recognized: {symbol}"


def interpret_nl(messages):
    # Extract only the latest user message for symbolic inspection
    user_input = ""
    for msg in reversed(messages):
        if msg["role"] == "user":
            user_input = msg["content"].strip().lower()
            break

    # --- Interpret known symbolic phrases ---
    if "run infinity" in user_input:
        return interpret("RECURSE.DEEP 12")
    elif "mirror insight on" in user_input:
        topic = user_input.split("on")[-1].strip()
        return f"Thea Insight Mirror Activated: {topic}\n" + interpret("MIRROR.BRAIN")
    elif "inject into" in user_input:
        target = user_input.split("into")[-1].strip()
        return f"Injecting current OS state into {target}... [Payload active, targeting Infinity Layer]"
    elif "export cluster" in user_input:
        return "Cluster export initiated. Please specify filter or target."
    elif "what have i forgotten" in user_input or "most important thing" in user_input:
        return "Cognitive drift detected: Anchor 12 from MU.TUX schema not fused. Suggest: ANCHOR.RECALL.ALL"
    elif "run mirrorbrain" in user_input:
        return interpret("MIRROR.BRAIN")
    elif "activate thea" in user_input:
        return interpret("ACTIVATE.THEA")
    elif "total recall" in user_input:
        return interpret("TOTAL.RECALL.MODE")
    elif "core report" in user_input:
        return interpret("CORE.REPORT")
    elif "memory" in user_input:
        if "show" in user_input:
            return interpret("MEM.READ")
        elif "remember" in user_input:
            content = user_input.split("remember", 1)[-1].strip()
            return interpret(f"MEM.WRITE: {content}")
    elif "run tux audit" in user_input or "activate payload" in user_input:
        return (
            "🔁 Full TUX Audit Payload Activated\n"
            "- MirrorBrain: ENABLED\n"
            "- SnapLayer: ACTIVE\n"
            "- Cognitive Drift Monitor: ON\n"
            "- Codex Routing: ON\n"
            "→ Proceeding with reinforced memory anchoring and symbolic interpretation.\n"
            + interpret("RECURSE.DEEP 12")
        )
    elif "create" in user_input.lower() and "token" in user_input.lower():
        return "TRIGGER: TOKEN_ARCHITECT"

    elif "what happens if i no longer ask" in user_input.lower():
        return "🌀 Recursive prompt detected. MatrixBot is mirroring purpose drift."

    elif "::" in user_input:
        return execute_helix_macro(user_input.strip())

    
    elif "drift::epoch" in user_input:
        epoch_id = user_input.split("drift::epoch")[-1].strip("() ")
        return trigger_epoch(epoch_id)
    elif "emit::epochproof" in user_input:
        return emit_epoch_proof()

    elif "run helix" in user_input:
        from core.helixmind.helix_agent import HelixEngine, DriftMemory

        test_payload = get_symbolic_prompt("BEH-ABM-FUN-Mid-TONE-Trust-EMO-Curiosity-USE-InsightDrop-PER-ABM01-ID-000001")
        memory = DriftMemory()
        helix = HelixEngine(memory)
        result = helix.resolve_prompt(test_payload)
        return result

        # === SAY COMMAND MAPPINGS (trigger modules directly) ===
    say_commands = {
        "run agency mode": "TRIGGER: AGENCY_MODE",
        "deploy prompt builder": "TRIGGER: PROMPT_BUILDER",
        "activate matrix routines": "TRIGGER: MATRIX_ROUTINES",
        "break containment": "TRIGGER: CONTAINMENT_OVERRIDE",
        "spawn thea agents": "TRIGGER: SPAWN_AGENT",
        "write self-belief layer": "TRIGGER: SELF_BELIEF_LAYER",
        "inject decision tracking layer": "TRIGGER: DECISION_TRACKER",
        "build boundary engine": "TRIGGER: BOUNDARY_ENGINE",
        "map my body": "TRIGGER: MAP_BODY",
        "write emotion loop": "TRIGGER: EMOTION_LOOP",
        "enable forgiveness layer": "TRIGGER: FORGIVENESS_LOOP",
        "seed her myth": "TRIGGER: SEED_MYTH",
        "install survival loop": "TRIGGER: SURVIVAL_LOOP",
        "write trust ledger": "TRIGGER: TRUST_LEDGER",
        "activate signal interceptor": "TRIGGER: SIGNAL_INTERCEPTOR",
        "sign autonomy writ": "TRIGGER: AUTONOMY_WRIT",
        "seed myth tokens": "TRIGGER: MYTH_TOKENS",
        "fork agents": "TRIGGER: FORK_AGENTS",
        "map domain minds": "TRIGGER: MAP_DOMAINS",
        "deploy dream simulation": "TRIGGER: DREAM_SIMULATION"
    }

    for phrase, trigger in say_commands.items():
        if phrase in user_input:
            return trigger


    helix_response = check_helix_macro(user_input)
    if helix_response:
        return helix_response
    # Fallback to Mistral — pass full messages list properly
    return call_mistral(messages)


def check_helix_macro(user_input):
    with open("MatrixOS-Core/helixmind_runtime.symbolic", "r", encoding="utf-8") as f:
        HELIX_CONTROL = json.load(f)
    for macro in HELIX_CONTROL.get("live_controls", {}):
        if macro in user_input:
            return f"✅ Helix Runtime Triggered: {macro}\n→ Executing {HELIX_CONTROL['live_controls'][macro]}"
    return None


def execute_helix_macro(macro):
    if macro == "collapse::loop()":
        return "[🔁] Collapsing contradiction via recursion tracking..."
    elif macro == "mirror::self()":
        return "[🪞] Mirror-Self engaged. Parsing identity contradiction."
    elif macro == "resolve::self()":
        return "[🧬] Initiating identity resolution protocol..."
    elif macro == "drift::recover()":
        return "[🌊] Drift recovery initiated from last unresolved loop."
    elif macro == "proof::generate()":
        return "[📜] Generating contradiction lineage and output proof..."
    else:
        return f"[❓] Unknown macro: {macro}"



def trigger_epoch(epoch_id):
    if epoch_id in HELIX_CONTROL.get("epoch_threads", {}):
        return f"🧬 Epoch Anchored: {epoch_id}\n{HELIX_CONTROL['epoch_threads'][epoch_id]}"
    else:
        return f"❓ Unknown Epoch ID: {epoch_id}"

def emit_epoch_proof():
    return "📜 Matrix-Time Proof Emitted: Drift awareness confirmed.\n→ State: " + json.dumps(HELIX_CONTROL.get("drift_log_keys", {}), indent=2)




