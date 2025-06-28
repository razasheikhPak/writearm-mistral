# matrixbot_main.py
from helix_runtime.router import MatrixRouter
from flask import session,  has_request_context
from helix_runtime.helix_memory import HelixMemory
import yaml
from core.matrixos_parser import interpret_input, parse_input
from core.conversation_engine import route_conversation
#from core.runtime_memory import update_memory
#from helix_runtime.redis_memory import save_session, load_session
#from helix_runtime.pg_memory import save_session, load_session
#from main import db, Message, call_mistral
from core.mistral_engine import call_mistral
from core.models import db, Message

db.init_app(app)
migrate = Migrate(app, db)

with app.app_context():
    db.create_all()


session_id = session.get("username", "anonymous") if has_request_context() else "anonymous"
session_memory = load_session(session_id)
drift_count = 0
user_memory = {}

#def load_session(session_id):
#    messages = Message.query.filter_by(username=session_id).order_by(Message.timestamp).all()
#    return [{"user": m.content} if m.role == "user" else {"bot": m.content} for m in messages]

#def save_session(session_id, session_memory):
#    Message.query.filter_by(username=session_id).delete()
#    for msg in session_memory:
#        if "user" in msg:
#            db.session.add(Message(username=session_id, role="user", content=msg["user"]))
#        elif "bot" in msg:
#            db.session.add(Message(username=session_id, role="assistant", content=msg["bot"]))
#    db.session.commit()

# Load config from YAML
def load_config():
    with open("config.yaml", "r") as file:
        return yaml.safe_load(file)

config = load_config()
TOKEN_ID = config["helix_token"]
redis_url = config["redis_url"]
gcs_bucket = config["gcs_bucket"]

# Initialize memory + router
memory = HelixMemory(token_id=TOKEN_ID, redis_url=redis_url, gcs_bucket=gcs_bucket)
router = MatrixRouter(memory=memory)

def respond_to_user(prompt):
    return router.route(prompt)

def handle_input(user_input):
    response = process_user_input(user_input)
    save_session(session_id, session_memory)
    return response

# PHASE 1: TheaGate-v1 — Symbolic Trigger Modulation
def is_conversational(input_text):
    common_inputs = ["hi", "hello", "hey", "yo", "sup", "ok", "yes", "no", "cool"]
    return input_text.lower() in common_inputs or len(input_text.split()) < 3

# PHASE 2: Conversational Intent + Tone State Engine
def classify_intent(input_text):
    if "how do I" in input_text or "what should I do" in input_text:
        return "instructional"
    elif "show me" in input_text or "run" in input_text:
        return "directive"
    elif "tell me about" in input_text or "explain" in input_text:
        return "informational"
    else:
        return "conversational"


TONE_STATE = {
    "instructional": "calm",
    "directive": "strategic",
    "informational": "explanatory",
    "conversational": "warm"
}


def apply_conversational_tone(message, tone):
    if tone == "calm":
        return f"Sure — here's how to approach it step by step. {message}"
    elif tone == "strategic":
        return f"Let's move. {message}"
    elif tone == "warm":
        return f"Glad you’re here. {message}"
    elif tone == "explanatory":
        return f"Here’s a clear breakdown. {message}"
    else:
        return message


# PHASE 3: Dialogue Memory + Contextual Reentry
def update_dialogue_memory(user_input, bot_reply):
    session_memory.append({"user": user_input, "bot": bot_reply})
    if len(session_memory) > 20:
        session_memory.pop(0)


def rethread_conversation():
    last_turns = session_memory[-3:]
    return f"Previously you asked about: {last_turns[0]['user']}. Shall we continue?"


# MATRIXTIME KERNEL v1
MATRIX_GRAPH = {
    "MAX": {
        "functions": ["run_behavior_logic", "evaluate_loyalty", "score_emotion"],
        "dependencies": ["Impulse Model", "Loyalty Engine", "Decision Stack"],
        "triggers": ["behavioral_input", "drift_detection", "user_profile_shift"]
    },
    "Conversion-OS": {
        "functions": ["tone_modulate", "funnel_layer", "emotional_style_engine"],
        "dependencies": ["LXB10k", "MAX"],
        "triggers": ["response_generation", "insight_drop", "email_nudge"]
    },
    "Matrix-ControlPanel": {
        "functions": ["route_OS_module", "load_sequence", "activate_tile"],
        "dependencies": ["Prompt Engine", "Persona Router"],
        "triggers": ["session_start", "user_command"]
    }
}


def route_matrix_intelligence(user_input):
    if "audit" in user_input:
        return "run_matrix_audit"
    elif "run" in user_input and "MAX" in user_input:
        return "run_behavior_logic"
    elif "CHRT" in user_input or "onboarding" in user_input:
        return "load_sequence::CHRT_OS"
    elif "create" in user_input and "campaign" in user_input:
        return "build_campaign_framework"
    else:
        return "dynamic_mistral_call"  # New fallback route




def run_matrix_module(module_name, **kwargs):
    if module_name == "run_behavior_logic":
        return call_mistral(kwargs.get("input"))
    elif module_name == "run_matrix_audit":
        return audit_matrix_os()
    elif module_name.startswith("load_sequence"):
        return f"[ControlPanel]: Loaded {module_name.split('::')[-1]}"
    elif module_name == "dynamic_mistral_call":
        return call_mistral(kwargs.get("input"))  # <== this lets ANY prompt run through LLM
    else:
        return "[MatrixOS]: Module not yet mapped. Request expansion."




def audit_matrix_os():
    unused_modules = []
    for module in MATRIX_GRAPH:
        if module not in [m['module'] for m in session_memory if 'module' in m]:
            unused_modules.append(module)
    return f"AUDIT: The following Matrix-OS modules have not been triggered recently: {unused_modules}"



def process_user_input(user_input):
    if is_conversational(user_input):
        if user_memory.get('last_prompt_type') == 'symbolic':
            return "Switching from symbolic mode. Want to continue a normal chat?"
        return "Hi. You’re in MatrixOS. Want symbolic, strategic, or conversational mode?"

    global drift_count
    if drift_count > 3:
        return "Symbolic loop limit reached. Switching to dialogue mode."

    intent = classify_intent(user_input)
    tone = TONE_STATE[intent]
    parsed = parse_input(user_input)
    
    core_reply = process_matrix_logic(user_input, parsed)
    response = apply_conversational_tone(core_reply, tone)

    update_dialogue_memory(user_input, response)
    save_session(session_id, session_memory)
    return response


def process_matrix_logic(input_text, parsed):
    if parsed['type'] == 'symbolic':
        return f"[Symbolic]: Triggered symbolic module {parsed['route']}"
    elif parsed['type'] == 'funnel':
        return f"[Funnel]: Detected funnel stage: {parsed['stage']}"
    else:
        return process_user_input_logic(input_text)

def process_user_input_logic(input_text):
    routed = route_matrix_intelligence(input_text)
    return run_matrix_module(routed, input=input_text)


if __name__ == "__main__":
    while True:
        user_input = input("You: ")
        reply = process_user_input(user_input)
        print("MatrixBot:", reply)

# Optional for direct CLI test
#if __name__ == "__main__":
#    while True:
#        user_input = input("You: ")
#        print("Matrix-Bot:", respond_to_user(user_input))
