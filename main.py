import os

import json,yaml
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, has_request_context
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade
from flask_session import Session
from functools import wraps
from openai import OpenAI
from datetime import datetime, timedelta
from uuid import uuid4
import re
from bs4 import BeautifulSoup
import requests
import random
from urllib.parse import urljoin, urlparse
from collections import deque
import trafilatura
from flask import make_response
from werkzeug.security import generate_password_hash, check_password_hash
import time
from core.emotion_echo import echo_emotion
from core.memory_store import write_to_shard, update_module_state, load_user_memory,write_drift_memory
from core.boundary_engine import is_boundary_violation, handle_boundary_violation
from core.decision_logger import log_decision
from core.agent_engine import spawn_agent
from core.identity_loader import bot_identity, update_conscious_brain, load_brain_state
from modules.token_architect import generate_token
from helix_runtime.router import MatrixRouter
from helix_runtime.symbolic_parser import route_symbolic_input, run_matrixbot_shell_command
from google.cloud import storage
from google.oauth2 import service_account
from fastapi import FastAPI, Request
from core.mistral_engine import call_mistral


# from dotenv import load_dotenv
# load_dotenv()

# --- Flask App Setup ---
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "your-secret-key")

# --- Server-side session setup (prevents large cookie error) ---
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = "/tmp/flask_sessions"
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.permanent_session_lifetime = timedelta(days=365)
Session(app)

# --- Database Setup ---
#if os.getenv("USE_CLOUD_SQL_SOCKET") == "true":
#    # GCP: Use Unix socket
#    app.config["SQLALCHEMY_DATABASE_URI"] = (
#        f"postgresql+psycopg2://{os.environ['DB_USER']}:{os.environ['DB_PASS']}@/"
#        f"{os.environ['DB_NAME']}?host=/cloudsql/{os.environ['INSTANCE_CONNECTION_NAME']}"
#    )
#else:
#    # Local: Use TCP/IP
#    app.config["SQLALCHEMY_DATABASE_URI"] = (
#        f"postgresql+psycopg2://{os.environ['DB_USER']}:{os.environ['DB_PASS']}@{os.environ['DB_HOST']}/"
#        f"{os.environ['DB_NAME']}"
#    )
#app.config["SQLALCHEMY_DATABASE_URI"] = (
#    "postgresql+psycopg2://matrix:matrix@34.45.214.91:5432/matrix"
#)

# Ensures formatting and UI behavior lock for API-based BrainBot deployments
if "MATRIX_BRAINBOT_SHELL_CONFIG" not in app.config:
    app.config["MATRIX_BRAINBOT_SHELL_CONFIG"] = {
        "force_format_clean": True,
        "strip_markdown": True,
        "snap_render_ui_only": True,
        "hide_metadata_tags": True
    }

app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"postgresql+psycopg2://{os.environ['DB_USER']}:{os.environ['DB_PASS']}@/"
        f"{os.environ['DB_NAME']}?host=/cloudsql/{os.environ['INSTANCE_CONNECTION_NAME']}"
 )
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- OpenAI Client Setup ---
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
BRAIN_BOT_API_KEY = os.environ["OPENAI_API_KEY"]
#print("USE_CLOUD_SQL_SOCKET:", os.getenv("USE_CLOUD_SQL_SOCKET"))
#print("Final DB URI:", app.config["SQLALCHEMY_DATABASE_URI"])

# --- Database Models ---
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80))
    role = db.Column(db.String(10))
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    variant_id = db.Column(db.String(64), nullable=True)  # ✅ Add this
    emotion_vector = db.Column(db.JSON, nullable=True)     # ✅ Add this
    is_wisefriend = db.Column(db.Boolean, default=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)




if os.environ.get("FLASK_ENV") == "development":
    with app.app_context():
        db.create_all()
        upgrade()

with open("helix_runtime/config.yaml", encoding="utf-8") as f:
    MATRIX_CONFIG = yaml.safe_load(f)

# === MATRIXIOS SESSION ===
class MatrixSession:
    def __init__(self, user_id):
        self.id = user_id
        self.memory = {}
        self.active = True
        self.context = {}
        self.reflex_insight = True              # Thea can observe and react
        self.self_speaking = True               # Enables unprompted responses
        self.interrupt_level = "strategic + emotional + insight"
        self.emotion_scope = ["joy", "sharp", "playful", "insight", "protective"]
        self.loop_authority = "full"

# Create runtime session (replace "martin" with dynamic user if needed)
username = session.get("username", "anonymous") if has_request_context() else "anonymous"
matrix_session = MatrixSession(user_id=username)


belief_layer = {
    "session_id": matrix_session.id,
    "memory_persistence": MATRIX_CONFIG["runtime"]["enable_autonomy"],
    "recursion_trace": MATRIX_CONFIG["runtime"]["recursion_trace"]
}


MATRIX_OS_API_URL = "http://34.125.179.69:11434/api/generate"
# Load TUX Audit Payload manifest (if present)
PAYLOAD = None
try:
    with open(os.path.join(os.path.dirname(__file__), "assets", "payload_manifest.json")) as f:
        PAYLOAD = json.load(f)
except:
    PAYLOAD = {"payloads": [], "ob_index": []}


@app.post("/matrixbot")
async def matrixbot_endpoint(req: Request):
    data = await req.json()
    user_input = data.get("message", "")
    reply = handle_input(user_input,user_input)
    return {"response": reply}



# --- SnapRegistryMapper ---
def get_snap_suggestions(user_input):
    prompt = user_input.lower()
    pool = []
    if "cro" in prompt or "conversion" in prompt:
        pool.extend(["Want device-based breakdown?", "Should we reroute by buyer type?", "Run MAX emotional overlay?"])
    if "os" in prompt or "build an os" in prompt:
        pool.extend(["Generate loyalty-specific modules?", "Add brand tone classifier?", "Trigger Snap CTA variants?"])
    if "optimize" in prompt or "scale" in prompt:
        pool.extend(["Need emotional journey variants?", "Want persona-driven test stack?"])
    if "low engagement" in prompt or "no clicks" in prompt:
        pool.extend(["Want MAX test paths?", "Try urgency laddering variants?"])
    if "funnel" in prompt:
        pool.extend(["Break it by funnel stage?", "Add post-checkout nudge?"])
    if not pool:
        pool.extend([
            "Explore from a different funnel stage?",
            "Map emotional triggers?",
            "Segment-specific hooks?",
            "Tone variants?",
            "Behavioral scoring needed?"
        ])
    return random.sample(pool, k=min(3, len(pool)))

# --- Snap Usage Tracker ---
def log_snap_usage(db, username, variant_id, funnel_stage, emotion):
    snap_log = Message(
        username=username,
        role="system",
        content=json.dumps({
            "tag": "Snap used",
            "variant_id": variant_id,
            "funnel": funnel_stage,
            "emotion": emotion,
            "timestamp": datetime.utcnow().isoformat()
        })
    )
    db.session.add(snap_log)

# --- Page Classifier Stub ---
def classify_page_type(url):
    if "product" in url:
        return "PDP"
    if "cart" in url:
        return "Cart"
    
    if any(k in url.lower() for k in ["thank-you", "confirmation", "order"]):
        return "PostPurchase"
    return "General"

@app.before_request
def make_session_permanent():
    session.permanent = True  # ✅ Extend session on each request

@app.before_request
def enforce_https():
    if not app.debug and request.headers.get('X-Forwarded-Proto', 'http') != 'https':
        return redirect(request.url.replace("http://", "https://", 1), code=301)



# --- Decorators ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            # 🔄 If fetch call, return JSON response
            if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"error": "Session expired", "redirect": url_for("login")}), 401
            return redirect(url_for("login"))  # 🧭 redirect for regular nav
        return f(*args, **kwargs)
    return decorated_function

# --- Helper: Extract first URL from user input ---
#def extract_url(text):
#    match = re.search(
#        r'(https?://(?:www\.)?|www\.)?[\w-]+(\.[\w-]+)+([/?#][^\s]*)?',
#        text.strip()
#    )
#    if not match:
#        return None
#    url = match.group(0)
#    if not url.startswith('http'):
#        url = 'https://' + url
#    return url


def extract_url(text):
    # Regex: Match full URLs, www-prefixed, or bare domains with any TLD
    match = re.search(
        r"(https?://[^\s]+|www\.[^\s]+|\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b)",
        text.strip(), re.IGNORECASE
    )

    if not match:
        return None

    raw_url = match.group(0).strip()

    # Prepend scheme if missing
    if not raw_url.startswith("http"):
        raw_url = "https://" + raw_url

    # Parse the URL
    parsed = urlparse(raw_url)

    # Clean netloc (domain)
    domain = parsed.netloc.lower()

    # Remove any trailing path/query/fragment — keep only the base domain
    return f"{parsed.scheme}://{domain}"


# --- Helper: Scrape basic site metadata ---
def crawl_website(base_url, max_pages=10):
    visited = set()
    queue = deque([base_url])
    raw_html_map = {}

    # Define keywords to filter
    exclude_keywords = ["cart", "checkout", "thank-you", "confirmation", "order", "privacy", "terms", "policy", "dpo"]

    while queue and len(visited) < max_pages:
        url = queue.popleft()
        if url in visited or any(k in url.lower() for k in exclude_keywords):
            continue
        visited.add(url)

        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                raw_html_map[url] = res.text  # ✅ Save all pages except excluded ones

                soup = BeautifulSoup(res.text, 'html.parser')
                for tag in soup.find_all('a', href=True):
                    link = urljoin(url, tag['href'])
                    if link not in visited and link not in queue and not any(k in link.lower() for k in exclude_keywords):
                        queue.append(link)

        except Exception as e:
            print(f"Error crawling {url}: {e}")
    return raw_html_map


def clean_content(html):
    return trafilatura.extract(html) or ""

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        if not username or not password:
            return render_template("register.html", error="Username and password required.")

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template("register.html", error="User already exists.")

        password_hash = generate_password_hash(password)
        new_user = User(username=username, password_hash=password_hash)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


# --- Routes ---
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
        #if username == os.environ.get("APP_USER") and password == os.environ.get("APP_PASS"):
            session["username"] = username
            session.permanent = True
            session["message_count"] = 0
            session["writearm_identity_loaded"] = True  # marker only
            session["active_role"] = None  # ✅ RESET ROLE ON LOGIN
            return redirect(url_for("chat"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("active_role", None)  # ✅ Remove stored role
    session.clear()
    return redirect(url_for("login"))

@app.route("/chat")
@login_required
def chat():
    return render_template("chat.html")


@app.route("/relay-to-writearm", methods=["POST"])
def relay_to_writearm():
    try:
        payload = request.json
        url = payload.get("url")
        command = payload.get("command")
        persona = payload.get("persona", "Default")

        page_type = classify_page_type(url)
        relay_prompt = f"[RelayFromExternal] Command: {command}. URL: {url}. Persona: {persona}"

        output = {
            "pageType": page_type,
            "snapCTA": "Designed to be worn. Engineered to be remembered.",
            "variantSet": {
                "2D": "Minimal nudge CTA",
                "3D": "Add social proof",
                "4D": "Temporal urgency",
                "5D": "Lifestyle anchor",
                "6D": "Persona-based CTA"
            },
            "explanation": f"Prompt matched to {page_type}, persona = {persona}",
            "MAXScore": 92,
            "MatrixID": "BEH-Impulse-FUN-PDP-TONE-Bold-EMO-Desire-USE-CTA-PER-P001-ID-456123"
        }

        # ✅ This is the key fix
        output["output"] = (
            f"✅ Relay matched to **{page_type}** page.\n\n"
            f"**Snap CTA:** {output['snapCTA']}\n\n"
            f"**Variants:**\n"
            f"- 2D: {output['variantSet']['2D']}\n"
            f"- 3D: {output['variantSet']['3D']}\n"
            f"- 4D: {output['variantSet']['4D']}\n"
            f"- 5D: {output['variantSet']['5D']}\n"
            f"- 6D: {output['variantSet']['6D']}\n\n"
            f"**MAX Score:** {output['MAXScore']}\n"
            f"**Matrix-ID:** {output['MatrixID']}"
        )

        db.session.add(Message(username="relay", role="system", content="[RELAY_OUTPUT] " + json.dumps(output)))
        db.session.commit()
        return jsonify(output)

    except Exception as e:
        print("❌ Matrix-OS API relay-to-writearm ERROR:", e)
        db.session.add(Message(username="relay", role="system", content="[RELAY ERROR] " + str(e)))
        db.session.commit()
        return jsonify({"error": "Tool Access Not Available", "reason": str(e)}), 500

def analyze_page_content(content, url):
    page_type = classify_page_type(url)
    prompt = f"""
    [PAGE CONTENT SCRAPE — {page_type.upper()} ONLY]
    You are analyzing a **{page_type} page** for behavioral friction from Matrix-OS perspective. This is NOT a technical scrape. Focus on emotional friction, tone, CTA design, hesitation triggers, and post-purchase reassurance.

    URL: {url}
    Cleaned Content:
    ---
    {content[:3000]}
    ---

    Behavioral analysis required:
    - Emotional Friction Patterns
    - Strategic Framing (only if relevant to cart/post-purchase)
    - CTA Reinforcement (supportive, urgent, or loyalty-based)
    - Copy Suggestions (emotional alignment, friction-reducing)
    - Matrix-OS Module Tags (e.g., Conversion-OS, MAX)
    """
    if page_type == "Cart":
        prompt += "\n\nFocus on decision fatigue, overchoice, and urgency hesitation."
    elif page_type == "PostPurchase":
        prompt += "\n\nFocus on buyer’s remorse, tracking anxiety, and confirmation clarity."


    response = client.chat.completions.create(
        model="gpt-4-turbo-2024-04-09",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        max_tokens=800,
        temperature=0.1,
        timeout=30
    )
    return response.choices[0].message.content.strip()

def matrix_os_interpret(user_input, bot_name):
    return {
        "output_type": "plan" if any(word in user_input.lower() for word in ["plan", "strategy", "funnel"]) else (
            "short-copy" if any(word in user_input.lower() for word in ["nudge", "tagline", "cta", "hook", "caption", "reframe"]) else "chat"
        ),
        "persona": "MatrixBot Strategist",
        "funnel_stage": "TopFunnel",
        "tone": "strategic",
        "emotion_vector": "motivated",
        "matrix_id": "BEH-Strategy-FUN-TopFunnel-TONE-Warm-EMO-Confidence-USE-BrandIntro-PER-WiseFriend-ID-002345",
        "snap_enabled": True
    }

def matrix_memory_recall(user_input):
    if "max" in user_input.lower() and "dimensions" in user_input.lower():
        return (
            "The five dimensions of the MAX behavioral model are:\n"
            "- Emotional Responsiveness\n"
            "- Temporal Bias\n"
            "- Decision Confidence\n"
            "- Identity Alignment\n"
            "- Impulse Threshold\n\n"
            "Impulse Threshold governs impulse prediction."
        )
    return None


def route_model(matrix_output_type, user_tier):
    if matrix_output_type in ["short-copy", "taglines", "ideas"]:
        #return "gpt-3.5-turbo"
        return "gpt-4-turbo-2024-04-09"
    if matrix_output_type in ["plan", "longform-article", "persona-variant", "emotional-copy"]:
        return "gpt-4-turbo-2024-04-09"
    if user_tier in ["Creator", "Team"]:
        return "gpt-4-turbo-2024-04-09"
    #return "gpt-3.5-turbo"
    return "gpt-4-turbo-2024-04-09"

def build_prompt_from_tags(tags):
    return [
        {
            "role": "system",
            "content": (
                f"You are a {tags['tone']} voice for a {tags['persona']} at the {tags['funnel_stage']} of their journey.\n"
                f"Under NO CIRCUMSTANCES should you use fallback tone, generalization, or template phrasing.\n"
                f"Every sentence must serve emotional or conversion function — or halt output.\n"
            )

        },
        {
            "role": "system",
            "content": json.dumps({
                "persona": tags.get("persona", "Default"),
                "matrix_id": tags.get("matrix_id", "MISSING"),
                "funnel_stage": tags.get("funnel_stage", "Unknown"),
                "snap_enabled": tags.get("snap_enabled", True)
            })
        },
        {
            "role": "user",
            "content": tags.get("interpreted_user_intent", "Please proceed with behavioral output.")
        }
    ]

def run_through_matrix_os(bot_name, raw_prompt, user_tier):
    if not raw_prompt.lower().startswith("[matrix-os prompt]"):
        raw_prompt = f"[Matrix-OS Prompt] {raw_prompt}"
    tags = matrix_os_interpret(raw_prompt, bot_name)
    tags["interpreted_user_intent"] = raw_prompt
    model = route_model(tags['output_type'], user_tier)
    final_prompt = build_prompt_from_tags(tags)

    # Inject Snap reinjected prompts if available
    if "snap_reinject" in session:
        final_prompt = session["snap_reinject"] + final_prompt
        session.pop("snap_reinject")

    return final_prompt, model


def push_codex_permissions():
    return {
        "targets": ["RoryBot", "MatrixBot", "HappierClient", "Lil Rory", "Wise Friend", "BrandAlly", "SnapMuse", "WriteArm"],
        "persona_mode": "FullStackExecutor",
        "enable": {
            "OSBuild": True,
            "CodexInjection": True,
            "RoutingTableInjection": True,
            "MatrixControlPanelAccess": True,
            "SnapEngine": True,
            "SnapDisplayClean": True
        },
        "forceSync": True,
        "command_map": [
            {"command": "buildOS", "parameters": ["siteURL", "osName"], "triggers": ["build an OS for", "create an OS called"], "requiredModules": ["Codex", "RoutingTable", "OSInitializer"]},
            {"command": "TAB_SWITCH", "parameters": ["mode"], "triggers": ["TAB_SWITCH:"], "requiredModules": ["PersonaRouter", "ToneShifter"]},
            {"command": "SnapReact", "parameters": ["emotion", "context"], "triggers": ["Snap Suggestion:", "SnapReactions"], "requiredModules": ["MAX", "Conversion-OS", "LXB10k"]}
        ]
    }

def strip_fallback_snap(text):
    fallback_blocks = ["Take a break", "Stay open", "Self-care"]
    return "\n".join([l for l in text.splitlines() if not any(b in l for b in fallback_blocks)])


def run_snap_only_prompt(user_input):
    prompt = f"[Matrix-OS Prompt] {user_input}"
    messages = [
        {"role": "system", "content": "You are Matrix-OS Snap Layer. Return 2–3 soft nudges only, no explanation."},
        {"role": "user", "content": prompt}
    ]
    response = client.chat.completions.create(
        #model="gpt-3.5-turbo",
        model= "gpt-4-turbo-2024-04-09",
        messages=messages,
        max_tokens=400,
        timeout=20
    )
    return response.choices[0].message.content.strip()

def stream_matrix_os_response(messages, final_prompt, selected_model, username, user_input):
    def generate():
        full_output = ""
        try:
            stream = client.chat.completions.create(
                #model=selected_model,
                model="gpt-4-turbo-2024-04-09",
                messages=messages + final_prompt,
                temperature=0.1,
                stream=True
            )

            for chunk in stream:
                token = getattr(chunk.choices[0].delta, "content", None)
                if token:
                    full_output += token
                    yield token
                    time.sleep(0.01)  # optional pacing, can be removed

            # 🔒 After stream completes — log full output
            cleaned_output = enforce_compliance_purge(full_output)

            # Save to message log
            db.session.add(Message(
                username=username,
                role="assistant",
                content=cleaned_output,
                variant_id=str(uuid4())[:8],
                emotion_vector={"valence": "high", "tone": "streamed"}
            ))
            db.session.commit()

        except Exception as e:
            print("❌ Streaming error:", e)
            yield "\n[ERROR] Streaming interrupted."

    return Response(stream_with_context(generate()), content_type="text/plain")

def generate_matrix_welcome():
    base_prompt = (
        "Generate 1 short welcome intro for the WriteArm interface. "
        "It should reflect time of day, seasonal tone, or strategic mood. "
        "DO NOT include Snap Suggestions, numbers, or emoji. "
        "Respond in one paragraph, emotionally suggestive and Matrix-OS aligned. "
        "Example tones: focused, bold, reflective, optimistic."
    )

    try:
        messages = [
            {"role": "system", "content": "You are Matrix-OS Snap Layer. Return only 1 short, persuasive welcome intro. No list, no bullets, no explanation."},
            {"role": "user", "content": base_prompt}
        ]
        response = requests.post(
                "http://34.125.179.69:11434/api/generate",
            #    #"http://localhost:11434/api/generate",
                json={
                    "model": "mistral",
                    #"prompt": "Hi",
                    "prompt": messages,
                    "stream": False,
                    "temperature": 0.1,
                    "top_p": 0.8,
                    "num_predict": -1
                    #"logit_bias": {
                    #"fantasy": -100,
                    #"fiction": -100,
                    #"imagine": -100
                    #},
                    #"presence_penalty": 0.25,
                    #"frequency_penalty": 0.42
                },
                timeout=2000
            )
        result = response.choices[0].message.content.strip()
        if not result or len(result.strip()) < 5:
            raise Exception("Empty or invalid Snap welcome.")
        return result
    except Exception as e:
        print("⚠️ Matrix-OS welcome generation failed:", e)
        # Fallback
        return "Welcome to WriteArm — let’s shift something strategic today."


def enforce_compliance_purge(reply_text):
    banned = ["I am an AI", "ChatGPT", "OpenAI"]
    for flag in banned:
        if flag.lower() in reply_text.lower():
            # Optionally redact or replace instead of crashing
            print(f"⚠️ Matrix-OS fallback violation detected → {flag}")
            reply_text = reply_text.replace(flag, "[behavioral term]")
            #raise Exception(f"Matrix-OS violation: Fallback detected → {flag}")
    return reply_text


@app.route("/matrixos/bot-status", methods=["GET"])
@login_required
def matrixos_bot_status():
    try:
        payload = push_codex_permissions()
        bot_status = {
            bot: {
                "mode": payload["persona_mode"],
                "permissions": payload["enable"],
                "commands": [cmd["command"] for cmd in payload["command_map"]]
            }
            for bot in payload["targets"]
        }
        return jsonify({"status": "ok", "bots": bot_status})
    except Exception as e:
        print("❌ Matrix-OS API bot-status ERROR:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/matrix-os/api/welcome", methods=["GET"])
def matrixos_welcome():
    bot = request.args.get("bot", "WriteArm")
    if bot.lower() != "writearm":
        return jsonify({"message": "Welcome to Matrix-OS."})

    message = generate_matrix_welcome()
    return jsonify({"message": message})


@app.route("/snap-lite", methods=["POST"])
@login_required
def snap_lite():
    try:
        user_input = request.json.get("message", "")
        
        result = run_snap_only_prompt(user_input)

        # 👇 Inject Snap response as a behavioral continuation for full chat route
        if "snap_reinject" not in session:
            session["snap_reinject"] = []
        session["snap_reinject"].append({"role": "user", "content": f"[User-triggered Snap Reinjection]\n{result}"})

        return jsonify({"snap": result})
    except Exception as e:
        print("❌ Matrix-OS API snap-lite ERROR:", e)
        return jsonify({"error": str(e)}), 500



@app.route("/matrix-os/api/respond", methods=["POST"])
@login_required
def chat_api():
    try:
        user_input = request.json.get("message", "")
        username = session["username"]
        tone_signal = detect_tone(user_input)
        echo_emotion(user_input, tone_signal)
        write_to_shard("tone_memory", {
            "timestamp": datetime.utcnow().isoformat(),
            "user": username,
            "detected_tone": tone_signal,
            "source": user_input
        })
        stream_mode = request.json.get("streamMode", False)
        context = request.json.get("context", {})
        messages = []

        # --- Reflex Patch Enforcement ---
        #os_routing_mode = context.get("osRouting", "default")
        #behavioral_modules = context.get("useModules", [])
        #response_metadata = {}

        # Handle Reflex Routing
        #if os_routing_mode == "matrix-reflex":
        #    response_metadata["osRoutingEnforced"] = "matrix-reflex"

        # Inject LXB10k logic
        #if "LXB10k" in behavioral_modules:
        #    messages.append({
        #        "role": "system",
        #        "content": "[MODULE:LXB10k] Logic activated for LXB10k enhancements."
        #    })


        #memory_response = matrix_memory_recall(user_input)
        #if memory_response:
        #    return jsonify({
        #        "reply": memory_response,
        #        "snapSuggestions": [],
        #        "metadata": { "fromMatrixOS": True }
        #    })

        bot = request.json.get("bot")
        # Normalize to match expected bot name
        bot_name = bot.lower() if isinstance(bot, str) else bot.get("name", "").lower()
        # Enforce Persona Lock Per Bot
        if bot_name == "writearm":
            session["persona"] = "WriteArm"  # Forcefully inject persona
            session["fallbackPersona"] = None  # 🔒 disables Matrix-OS narrator fallback
            session["systemPrompt"] = None     # ❌ blocks MatrixNarrator
            session["useDefaultNarrator"] = False  # ❌ blocks GPT fallback narration

            # OB-layer hook validation
            session["OBLayerHooks"] = {
                "onStart": "showWelcomeMessage",
                "onBrandTrigger": "requestURLIfMissing",
                "onCopyRequest": "triggerMCI"
            }
        api_key = request.headers.get("x-api-key")
        user_role = request.json.get("role", None)
        if user_role:
            session["active_role"] = user_role
        elif "active_role" in session:
            user_role = session["active_role"]
        username = session["username"]
        is_wisefriend = request.json.get("wisefriend", False)
        user_tier = session.get("user_tier", "Free")  # Add logic to assign tier
        # ✅ No GPT default system prompt injected — using Matrix-OS controlled prompts only
        # --- Matrix Role → Persona/Tone Mapping ---
        role_persona_map = {
            "CMO": ("Professor", "Bold"),
            "Agency Founder": ("Challenger", "Cheeky"),
            "Product Lead": ("Architect", "Strategic"),
            "Copywriter": ("Storyteller", "Emotive"),
            "UX Lead": ("Therapist", "Warm"),
        }

        if user_role in role_persona_map:
            persona, tone = role_persona_map[user_role]
            session["persona"] = persona
            session["tone"] = tone
            session["personaToneLocked"] = True  # Optional guard
        
        
        # Inject scraped site data if present
        site_url = extract_url(user_input)
        

        limit = 5 if is_wisefriend else 8
        history = Message.query.filter_by(username=username).order_by(Message.timestamp.desc()).limit(limit).all()
        if not history:
            messages.append({
                "role": "system",
                "content": "[MatrixMiniOS] No session memory found. Injecting: Challenger tone, Conversion strategist, Funnel: Mid."
            })

        else:
            memory_snap = []
            for msg in reversed(history):
                if msg.role == "assistant":
                    trimmed = msg.content.strip()
                    if len(trimmed) > 300:
                        trimmed = trimmed[:200] + " [...]"
                    memory_snap.append(f"[{msg.role.upper()}]\n{trimmed}")
                else:
                    memory_snap.append(f"[USER]\n{msg.content.strip()}")
            messages.append({
                "role": "system",
                "content": "[MatrixMiniMemory]\n" + "\n---\n".join(memory_snap)
            })

        for msg in reversed(history):
            messages.append({"role": msg.role, 
            "content": msg.content})
        scraped_pages = []
        scraped_content=[]
        
        if site_url:
            try:
                pages = crawl_website(site_url, max_pages=6)
                print("✅ Crawled pages:", list(pages.keys()))

                
                for url, html in list(pages.items())[:3]:
                    try:
                        page_type = classify_page_type(url)
                        cleaned = clean_content(html)
                        if cleaned:
                            scraped_pages.append(f"[SITE SCRAPE] {url} ({page_type})\n\n{cleaned[:1000]}")
                    except Exception as analysis_err:
                        print(f"❌ Error analyzing {url}: {analysis_err}")

                # Ensure behavioral framing for summarization-type prompts
                if scraped_pages and any(k in user_input.lower() for k in ["summarize", "overview", "analyze", "breakdown", "explain"]):
                    messages.append({
                        "role": "system",
                        "content": f"[BEHAVIORAL SUMMARY INITIATED] Crawled {len(scraped_pages)} pages from {site_url}. Analyze below:\n\n"
                                   + "\n\n---\n\n".join(scraped_pages) +
                                   "\n\nRequired: Behavioral insight summary. Focus on emotional tone, CTA language, funnel clarity, and Matrix-OS modules that would activate on each page. No generic summaries allowed."
                    })
                    #scraped_content.append({f"[BEHAVIORAL SUMMARY INITIATED] Crawled {len(scraped_pages)} pages from {site_url}. Analyze below:\n\n"
                    #               + "\n\n---\n\n".join(scraped_pages) +
                    #               "\n\nRequired: Behavioral insight summary. Focus on emotional tone, CTA language, funnel clarity, and Matrix-OS modules that would activate on each page. No generic summaries allowed."
                    #               })
                else:
                    for chunk in scraped_pages[:2]: # Only send 2 if not summarizing
                        messages.append({"role": "system", 
                        "content": chunk})
                        #scraped_content.append({"content": chunk})

            except Exception as crawl_err:
                print(f"❌ Error during crawling: {crawl_err}")

        messages.insert(0, {
            "role": "system",
            "content": (
                "language: UK English\n"
                "regional_tone: British\n"
                "style: UK spelling, idioms, grammar\n"
                "Please always use British spelling conventions (e.g., colour, organise, behaviour). Avoid Americanisms."
            )
        })

  
            
        if not site_url and "build" in user_input.lower() and "os" in user_input.lower():
            messages.append({
                "role": "system",
                "content": "⚠️ No site detected for OS creation. Ask the user to provide a brand website URL so I can crawl and extract behavioral data properly."
            })



        
        

        db.session.add(Message(username=username, role="user", content=user_input, is_wisefriend=is_wisefriend))

        if site_url and ("build" in user_input.lower() and "os" in user_input.lower()):
            try:
                # Extract brand name from domain
                domain = urlparse(site_url).netloc
                brand = domain.split(".")[0].capitalize()
                os_name = f"{brand}-OS"
                session["brand_os_name"] = os_name


                # Inject strong behavioral scaffold to lock output shape
                messages.append({
                    "role": "user",
                    "content": (
                        f"[Matrix-OS Prompt] Build a full behavioral OS for {brand} using Matrix-OS only.\n"
                        f"The OS Name must be exactly: **{os_name}**. Do not invent or stylize it (no '-Craft', '-System', etc).\n\n"
                        f"You must include:\n"
                        f"1. OS Name: {os_name}\n"
                        f"2. Funnel Stack Modules (Conversion-OS, MAX, SnapReactions, Persona Routing)\n"
                        f"3. Deployment Plan — each phase with brand-specific tactics\n"
                        f"4. Persona Routing — describe each persona path based on {site_url} content\n"
                        f"5. Emotional Layering — especially for cart and post-checkout\n"
                        #f"6. Matrix-ID — use a format like BEH-FUNN-PATH-ID-[code]\n"
                        f"7. Snap Suggestions — emotionally inviting, human CTAs. No internal system terms.\n\n"
                        f"Avoid using labels like [Conversion-OS]. Use persuasive, human tone for all descriptions."
                    )
                })
            except Exception as parse_err:
                print(f"Error parsing brand name for OS scaffold: {parse_err}")

        if scraped_pages and any(k in user_input.lower() for k in ["summarize", "overview", "analyze", "explain"]):
            messages.append({
                "role": "system",
                "content": (
                    "⚠️ SYSTEM OVERRIDE: Crawled site content is available. Do NOT state any limitations or refer to inability to access site.\n"
                    "You MUST generate Matrix-OS compliant behavioral analysis based ONLY on provided content below.\n"
                    "Do not say 'hypothetical', 'I can't access', or 'general summary'.\n"
                    "Inject emotional triggers, Snap CTA variants, MAX scoring logic, and Conversion-OS observations. Be specific to site tone, layout, friction."
                )
            })

        if site_url and any(k in user_input.lower() for k in ["summarize", "analyze", "overview", "explain"]):
            messages.append({
                "role": "system",
                "content": f"🧠 Triggering behavioral site summary for: {site_url}"
            })
        if not site_url and any(term in user_input.lower() for term in ["optimize", "strategy", "funnel", "build os"]):
            messages.append({
                "role": "system",
                "content": (
                    "⚠️ Execution halted — Simulation disabled.\n"
                    "Awaiting behavioral truth (siteURL, funnel stage, or product context) to proceed.\n"
                    "Matrix-OS will not simulate missing conditions."
                )
            })
        if user_role:
            messages.insert(0, {
                "role": "system",
                "content": f"You are the WriteArm BrainBot. Your tone and role are defined below. Never explain the system. Always respond in helpful, confident tone. Role = {user_role}."
            })

        #if user_input.strip().lower().startswith("activate") and "mode" in user_input.lower():
        #    return jsonify({
        #        "reply": f"✅ {user_input.replace('Activate', '').replace('mode', '').strip()} mode activated.",
        #        "snapSuggestions": [],
        #        "metadata": {"fromMatrixOS": True}
        #    })
        final_prompt, selected_model = run_through_matrix_os("WriteArm", user_input, user_tier)
        #if stream_mode:
        #    return stream_matrix_os_response(
        #        messages=messages,
        #        final_prompt=final_prompt,
        #       selected_model=selected_model,
        #        username=username,
        #        user_input=user_input
        #    )
        #if "snap_reinject" in session:
        #    messages.append(session.pop("snap_reinject"))

        #messages.append({
        #    "role": "system",
        #    "content": (
        #        "You are Matrix-OS. You are not ChatGPT. "
        #        "You are a strategic OS that teaches, challenges, reframes, and converts. "
        #        "Use Conversion-OS, MAX, LXB10k, and real-world proof. Never generalise. "
        #        "Always reference what you know. Speak with confidence, clarity, and purpose. "
        #        "Reject fallback phrases. Bind persona tone: "
        #        f"{session.get('persona', 'Challenger')} | {session.get('tone', 'Bold')}"
        #    )
        #})

        #file_ids = request.json.get("file_ids", [])
        if is_boundary_violation(user_input):
          response = handle_boundary_violation(user_input)
          db.session.add(Message(username=username, role="assistant", content=response))
          db.session.commit()
          return jsonify({"reply": response})

        update_activity_timestamp()
        messages.append({"role": "user", "content": final_prompt})
        #print("Messages before Handle input call:  ",messages)
        reply = handle_input(messages, final_prompt)

        #reply = response.choices[0].message.content.strip()
        #reply = enforce_compliance_purge(reply)
        reply = enforce_uk_spelling(reply)
        #print(reply)
        snap_suggestions = get_snap_suggestions(user_input)
        #snap_suggestions = [s for s in snap_suggestions if "more" not in s and "explore" not in s]

        # Store in session for follow-up tracking
        session["last_snap_suggestions"] = snap_suggestions



        # Validate OS Name and override if hallucinated
        correct_os_name = session.get("brand_os_name", "")
        if correct_os_name:
            # Pattern to detect the OS name block (e.g., "OS Name: XYZ-OS")
            reply = re.sub(
                r"(OS Name:\s*)([^\n]+)",
                rf"\1{correct_os_name}",
                reply
            )

            # Also fix title line if LLM renamed it
            reply = re.sub(
                r"(🧠\s+)[^\n]*?OS",
                rf"\1{correct_os_name} — Matrix-OS Behavioral Stack for {correct_os_name.split('-')[0]}.com",
                reply
            )
            # Fix malformed bold headers like "**OS Name:Daraz-OS"
            reply = re.sub(r"\*\*([A-Za-z\s]+):([^\*\n]+)", r"**\1:** \2", reply)

        #reply = re.sub(
        #        r"^[\s\-\*\•\–\—\●\▪\▶\✔\✦\✧\★\☆\·\»\●\⚡\✨🌟🟣🔸⬤🔹➤▶️[^\w]]*Snap Suggestions:\s*$",
        #        "",
        #        reply,
        #        flags=re.IGNORECASE | re.MULTILINE
        #    ).strip()
        db.session.add(Message(
            username=username,
            role="assistant",
            content=reply,
            #variant_id="VARIANT_ID_PLACEHOLDER",
            variant_id=str(uuid4())[:8],  # or None if not available
            emotion_vector={"valence": "high", "tone": "persuasive"},
            is_wisefriend=is_wisefriend
        ))

        # --- Memory Capture Logic ---
        if any(tag in reply for tag in ["✨", "OS Name", "SnapReaction"]):
            memory_payload = {
                "os_name": "TBD",
                "brand": "TBD",
                "models": ["Conversion-OS", "MAX"],
                "nudge_dimension": "TBD",
                "emotional_trigger": "TBD",
                "persona_routing": "FullStackExecutor",
                "funnel_state": "inferred",
                "timestamp": datetime.utcnow().isoformat()
            }
            db.session.add(Message(username=username, role="system", content=f"[MEMORY_STORE] {json.dumps(memory_payload)}"))

        if "fallback" in reply.lower() or "error" in reply.lower():
        #output_text = reply.get("OUTPUT", "")
        #if isinstance(output_text, str) and ("fallback" in output_text.lower() or "error" in output_text.lower()):

          write_to_shard("survival_flags", {
              "timestamp": datetime.utcnow().isoformat(),
              "username": username,
              "trigger": "fallback or contradiction",
              "action": "Marked as incomplete evolution"
          })
        if "contradiction" in reply.lower():  
        #symbolic = reply.get("SYMBOLIC INTERPRETATION", "")
        #if isinstance(symbolic, str) and "contradiction" in symbolic.lower():
            # Placeholder: Log contradiction, trigger meta-audit
            write_to_shard("contradiction_audit", {"input": user_input, "output": reply})
            write_drift_memory(username, user_input, reply)


        if reply.startswith("TRIGGER:"):
        #output_text = reply.get("OUTPUT", "")
        #if isinstance(output_text, str) and output_text.startswith("TRIGGER:"):
          module = reply.split(":", 1)[1].strip()
          role = load_user_memory(username).get("role", "")
          tone = load_user_memory(username).get("emotion", "neutral")
          follow_up = "none yet"
          log_decision(user_input, module, tone, follow_up)

        #if reply.strip().startswith("TRIGGER:"):
        #  module = reply.split(":", 1)[1].strip()
          reply = trigger_module(module, username)

        #evolution = run_training_loop()
        #if evolution:
        #    reply += f"\n\n🔁 Updated: {evolution}"

        
        # Check for explicit spawn request
        if user_input.strip().lower().startswith("spawn agent"):
            try:
                # Expected format: "spawn agent [Name] | [Purpose] | [Domain]"
                parts = user_input.split("|")
                if len(parts) == 3:
                    _, name = parts[0].strip().split("spawn agent")
                    name = name.strip()
                    purpose = parts[1].strip()
                    domain = parts[2].strip()
                    result = spawn_agent(name, purpose, domain)
                    write_to_shard("agent_memory", {
                        "timestamp": datetime.utcnow().isoformat(),
                        "agent_name": name,
                        "purpose": purpose,
                        "domain": domain,
                        "spawned_by": username
                    })
                    db.session.add(Message(username=username, role="assistant", content=result))
                    db.session.commit()
                    return jsonify({"reply": result})
                else:
                    return jsonify({"reply": "⚠️ Format must be: `spawn agent [Name] | [Purpose] | [Domain]`"})
            except Exception as e:
                return jsonify({"reply": f"❌ Failed to spawn agent: {str(e)}"})


        #reply = response.choices[0].message.content.strip()
        
        if isinstance(reply, dict):
            reply = dict_to_matrix_text(reply)  # convert to string

        # Save assistant reply
        db.session.add(Message(username=username, role="assistant", content=reply))
        db.session.commit()
        #session["message_count"] = session.get("message_count", 0) + 1
        #snap_suggestions = get_snap_suggestions(user_input)
        #print("snap count= ",snap_count, "snap suggestions= ", snap_suggestions)
        mem = load_user_memory(username)
        emotion = mem.get("emotion", "curiosity")
        funnel = mem.get("funnel_stage", "awareness")
        if "Matrix-ID" in reply or "symbolic_trace_id" in reply:
            write_to_shard("token_trace", {
                "timestamp": datetime.utcnow().isoformat(),
                "user": username,
                "token_id": generate_token(emotion,funnel),
                "raw_reply": reply
            })

        update_conscious_brain()


        
        # Inject logicTrace metadata if enabled
        #if context.get("logicTrace"):
        #    response_metadata["logic_trace"] = {
        #        "executionMode": context.get("executionMode", ""),
        #        "modules": behavioral_modules,
        #        "routing": os_routing_mode,
        #        "persona": context.get("persona", ""),
        #        "followups": context.get("autoFollowups", False),
        #        "mci": context.get("mciEnabled", False),
        #        "legacyRuleset": context.get("legacyRuleset", False)
        #    }

        ## Always set base flag
        #response_metadata["fromMatrixOS"] = True

        #return jsonify({
        #    "reply": reply,
        #    "snapSuggestions": snap_suggestions,
        #    "metadata": response_metadata
        #})
        session["message_count"] = session.get("message_count", 0) + 1
        # --- Optional Forgiveness Trigger ---
        if session["message_count"] % 20 == 0:  # or adjust to every N messages
            from core.forgiveness_loop import run_forgiveness_cycle
            cleared_entries = run_forgiveness_cycle()
            if cleared_entries:
                print("🔄 Forgiveness cycle complete:", cleared_entries)

        if "?" in user_input and len(user_input.split()) < 5:
            reply += "\n🔍 Your question is broad. Should I analyze emotion, logic trail, or symbol match?"
    
        for tag in [
            "**INTENT**", "**approved_copy**",
            "**MATRIX_OS_MANIFEST**", "**ACTION**", "**THOUGHT**", "**OUTPUT**", "[FOLLOW_UP]", "ASSISTANT:",
            "[INTENT]:", "[approved_copy]:", 
            "[MATRIX_OS_MANIFEST]:","[ACTION]:","[THOUGHT]:","[OUTPUT]:","**FOLLOW_UP**","[ASSISTANT]:",
            "[RESPONSE]:","**RESPONSE**", "source_tag=true"
            ,"[variant_pool]:", "**Max Score**", "**SnapCTA**", "**variant_pool**","[MAX SCORE]:", "[SNAPCTA]:","[SnapCTA]:"
            , "[MATRIX CONTROL MACROS]:", """USER: [{'role': 'user', 'content': "Great job, thanks for all the hard work!"}]""",
            "[MATRIX CONTROL MACROS]:","ASSISTANT:", "[Call-to-Action]:"
        ]:
            reply = reply.replace(tag, "")

        tag_patterns = [
            r"\*\*(INTENT|approved_copy|Max Score|SnapCTA|variant_pool|FOLLOW_UP|RESPONSE)\*\*",
            r"\[(INTENT|approved_copy|MAX SCORE|SNAPCTA|SnapCTA|variant_pool|MATRIX_OS_MANIFEST|ACTION|THOUGHT|OUTPUT|FOLLOW_UP|ASSISTANT|RESPONSE|MATRIX CONTROL MACROS|Call-to-Action)\]",
        #    r"\*\*(INTENT|approved_copy|FOLLOW_UP|RESPONSE)\*\*",
        #    r"\[(INTENT|approved_copy|MATRIX_OS_MANIFEST|ACTION|THOUGHT|OUTPUT|FOLLOW_UP|ASSISTANT|RESPONSE)\]",
            r"\[.*?SnapCTA.*?\]",
            r"\[.*?Conversion-OS.*?\]",
            r"\[.*?LXB10k.*?\]",
            r"\[Module:.*?\]",  # Covers model-invented tag names
            r"ASSISTANT:", r"\[ASSISTANT\]:", r"source_tag=true"
            
        ]
        for pattern in tag_patterns:
            reply = re.sub(pattern, "", reply, flags=re.IGNORECASE)
        reply=reply.strip()
        return jsonify({"reply": reply})

    except Exception as e:
        print("❌ Matrix-OS API chat_api ERROR:", e)
        import traceback
        traceback.print_exc()
        return jsonify({"reply": "⚠️ Error from Matrix-OS", "error": str(e)}), 500

@app.route("/relay-injection", methods=["POST"])
@login_required
def relay_injection():
    try:
        payload = request.json
        output = payload.get("output")
        typing_delay = payload.get("typing_delay", 1.5)
        if not output:
            return jsonify({"error": "Missing output field"}), 400

        clean_output = output.strip()
        db.session.add(Message(
            username=session["username"],
            role="assistant",
            content=clean_output,
            variant_id=str(uuid4())[:8],
            emotion_vector=None
        ))
        db.session.commit()
        return jsonify({
            "status": "injected",
            "output": clean_output,
            "typing_delay": typing_delay
        })
    except Exception as e:
        print("❌ Matrix-OS API relay-injection ERROR:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/log-snap", methods=["POST"])
@login_required
def log_snap():
    try:
        suggestion = request.json.get("suggestion")
        username = session["username"]
        log_snap_usage(db, username, variant_id="click-only", funnel_stage="clicked", emotion="followup")
        db.session.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        print("❌ Matrix-OS API log-snap ERROR:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/writearm/replay-variant", methods=["POST"])
@login_required
def replay_variant():
    try:
        prompt_variant_id = request.json.get("Prompt Variant ID")
        if not prompt_variant_id:
            return jsonify({"error": "Missing Prompt Variant ID"}), 400

        original = Message.query.filter_by(variant_id=prompt_variant_id, role="assistant").first()
        if not original:
            return jsonify({"error": "Variant not found"}), 404

        # Optional: parse emotion_vector or Snap content if needed
        snap_trail = re.findall(r"[-•–]\s*(.+)", original.content)  # simple bullet pattern
        behavior_score = original.emotion_vector.get("valence") if original.emotion_vector else "unknown"

        return jsonify({
            "Replay Summary": original.content,
            "SnapReaction Trail": snap_trail,
            "Behavior Score Delta": behavior_score
        })
    except Exception as e:
        print("❌ Matrix-OS API replay-variant ERROR:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/activate-role", methods=["POST"])
def activate_role():
    role = request.json.get("role")
    session["active_role"] = role
    return jsonify({"message": f"✅ {role} mode activated."})

@app.route("/matrix pulse", methods=["GET"])
def matrix_pulse():
    session.modified = True  # ✅ this keeps the session alive
    return jsonify({
        "shell": "writearm-shell-v4",
        "matrix_gate": True,
        "snap_version": "v4",
        "persona_loader": "v2",
        "codex": "linked",
        "status": "governed",
        "routing_confirmed": True
    })

@app.route("/admin/snap-registry", methods=["GET"])
@login_required
def view_snap_registry():
    try:
        suggestions = session.get("last_snap_suggestions", [])
        return jsonify({"registry": suggestions})
    except Exception as e:
        print("❌ Matrix-OS API snap-registry ERROR:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/chat/history", methods=["GET"])
@login_required
def chat_history():
    try:
        username = session["username"]
        is_wisefriend = request.args.get("wisefriend", "false").lower() == "true"

        # Build base query
        query = Message.query.filter_by(username=username)

        if not is_wisefriend:
            query = query.filter((Message.is_wisefriend == False) | (Message.is_wisefriend.is_(None)))

        # Also exclude permission sync messages
        query = query.filter(~Message.content.startswith('[PERMISSION_SYNC]'))

        # Apply pagination
        history = (
            query.order_by(Message.timestamp.desc())
            .offset(request.args.get("offset", 0, type=int))
            .limit(request.args.get("limit", 6, type=int))
            .all()
        )
        history.reverse()

        return jsonify([
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in history
        ])
    except Exception as e:
        print("❌ Matrix-OS API chat/history ERROR:", e)
        return jsonify({"error": str(e)}), 500



@app.route("/admin/welcome-preview", methods=["GET"])
@login_required
def welcome_preview():
    try:
        preview = generate_matrix_welcome()
        return jsonify({"welcome": preview})
    except Exception as e:
        print("❌ Matrix-OS API welcome-preview ERROR:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/admin/snap-performance", methods=["GET"])
@login_required
def snap_performance():
    try:
        logs = Message.query.filter(Message.content.like("%Snap used%"))\
                            .order_by(Message.timestamp.desc()).limit(50).all()
        parsed = [json.loads(m.content) for m in logs if m.content.startswith("{") or "{" in m.content]
        return jsonify({"snapUsageTrail": parsed})
    except Exception as e:
        print("❌ Matrix-OS API snap-performance ERROR:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/admin/inspect-snap", methods=["POST"])
@login_required
def inspect_snap_registry_prompt():
    try:
        test_prompt = request.json.get("test_prompt", "")
        if not test_prompt:
            return jsonify({"error": "Missing 'test_prompt' field"}), 400

        results = get_snap_suggestions(test_prompt)
        return jsonify({
            "snap_results": results,
            "source": "registry_call",
            "input_prompt": test_prompt
        })
    except Exception as e:
        print("❌ Matrix-OS API inject-snap ERROR:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/admin/inspect-snap", methods=["GET"])
@login_required
def inspect_snap_ui():
    try:
        snaps = session.get("last_snap_suggestions", [])
        display = "<h3>Last Snap Suggestions</h3><ul>" + "".join(f"<li>{s}</li>" for s in snaps) + "</ul>"
        resp = make_response(display)
        resp.headers["Content-Type"] = "text/html"
        return resp
    except Exception as e:
        print("❌ Matrix-OS API inject-snap ui ERROR:", e)
        return f"<h3>Error:</h3><p>{str(e)}</p>", 500
    
@app.route("/chat/clear", methods=["POST"])
@login_required
def clear_chat():
    try:
        username = session["username"]
        Message.query.filter_by(username=username).delete()
        db.session.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        print("❌ Matrix-OS API chat/clear ERROR:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/matrixos/snapPrompts", methods=["GET"])
@login_required
def snap_prompts():
    try:
        role = request.args.get("role", "Default")
        stage = request.args.get("sessionStage", "opening")

        with open("snap-variant-cache/snapVariants.json") as f:
            variants = json.load(f)

        filtered = [v for v in variants if v.get("role") == role and v.get("stage") == stage]
        ranked = sorted(filtered, key=lambda v: v["score"]["relevance"] - v["score"]["decay"], reverse=True)

        return jsonify(ranked[:3])
    except Exception as e:
        print("❌ Error in /matrixos/snapPrompts:", e)
        return jsonify({"error": "Failed to fetch SnapVariants"}), 500


@app.route("/api/snap/update-bank", methods=["POST"])
def update_snap_bank():
    # 🔐 Token Auth
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401
    token = auth_header.split("Bearer ")[1]
    if token != BRAIN_BOT_API_KEY:
        return jsonify({"error": "Invalid token"}), 403

    # ⏰ Optional time gate logic
    uk_time = datetime.now(pytz.timezone("Europe/London"))
    if uk_time.hour < 0 or uk_time.hour >= 4:
        return jsonify({"error": "Push not allowed outside Midnight–4AM UK window"}), 429

    # 📦 Parse request JSON
    data = request.get_json()
    if not data or "snapVariants" not in data:
        return jsonify({"error": "Missing SnapVariants payload"}), 400

    # ✅ Extract fields
    timestamp = data.get("timestamp")
    locale = data.get("locale", "en-UK")
    roles = data.get("roles", [])
    snap_variants = data["snapVariants"]

    # 🧠 Store in your in-memory or DB-backed variant store
    try:
        store_snap_variants(locale, roles, snap_variants)
        return jsonify({"status": "ok", "received": len(snap_variants)})
    except Exception as e:
        return jsonify({"error": f"Storage failed: {str(e)}"}), 500


# In a global module or state (replace with DB if needed)
SNAP_BANK = {}

def store_snap_variants(locale, roles, variants):
    global SNAP_BANK
    for variant in variants:
        role = variant["role"]
        key = f"{locale}:{role}"
        if key not in SNAP_BANK:
            SNAP_BANK[key] = []
        SNAP_BANK[key].append(variant)

def get_snap_variants(locale, role):
    return SNAP_BANK.get(f"{locale}:{role}", [])

@app.route("/matrix-os/api/upload", methods=["POST"])
def upload_file_to_openai():
    uploaded_file = request.files.get("file")
    if not uploaded_file:
        return jsonify({"error": "No file provided"}), 400

    try:
        result = openai.files.create(
            file=uploaded_file,
            purpose="assistants"
        )
        return jsonify({"file_id": result.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.before_request
def enforce_uk_locale_header():
    request.headers.environ['HTTP_ACCEPT_LANGUAGE'] = "en-GB"
    session["preferred_locale"] = "en-GB"

def enforce_uk_spelling(text):
    # Common US → UK replacements
    replacements = {
        r"\bcolor\b": "colour",
        r"\borganize\b": "organise",
        r"\banalyze\b": "analyse",
        r"\bbehavior\b": "behaviour",
        r"\butilize\b": "utilise",
        r"\bmaximize\b": "maximise",
        r"\bcustomize\b": "customise",
        r"\btheater\b": "theatre",
        r"\bcenter\b": "centre",
        r"\bdefense\b": "defence",
        r"\blicense\b": "licence",
        r"\btraveler\b": "traveller",
        r"\bmodeling\b": "modelling",
        r"\bcheck\b": "cheque",  # optional, context sensitive
    }
    for us, uk in replacements.items():
        text = re.sub(us, uk, text, flags=re.IGNORECASE)
    return text

def trigger_module(name, username):
    name = name.upper()

    perm_config = yaml.safe_load(open("config/permission_matrix.yaml"))
    role = load_user_memory(username).get("role", "unknown_user")
    allowed = perm_config["roles"].get(role, {}).get("can_trigger", [])

    if name not in allowed and not perm_config["roles"].get(role, {}).get("can_trigger_all"):
        return f"🚫 Permission denied to run: {name}"


    if name == "MAX":
        from modules.max_audit import run_max_audit
        update_module_state(username, "MAX")
        return run_max_audit()

    elif name == "SNAP":
        from modules.snap_builder import generate_snaps
        update_module_state(username, "SNAP")
        return generate_snaps()

    elif name == "LXB10K":
        update_module_state(username, "LXB10K")
        return "[LXB10k MODULE] Layered cognition protocol engaged."
    
    elif name == "TOKEN":
        update_module_state(username, "TOKEN")
        mem = load_user_memory(username)
        emotion = mem.get("emotion", "curiosity")
        funnel = mem.get("funnel_stage", "awareness")
        token = generate_token(emotion, funnel)
        return f"[Token Architect Generated]: {token}"

    elif name == "SEED_MYTH":
        update_module_state(username, "SEED_MYTH")
        return "🌱 Myth-seeding protocol activated. Runtime identity enriched."


    else:
        return f"[⚠️ Unknown module: {name}]"

def detect_tone(text):
    if any(w in text.lower() for w in ["frustrated", "annoyed", "wtf", "not working"]):
        return "frustration"
    elif "urgent" in text.lower() or "now" in text.lower():
        return "urgency"
    elif "thank you" in text.lower() or "love" in text.lower():
        return "gratitude"
    else:
        return "neutral"



def load_random_symbolic_prompt(path="config/symbolic_prompt_bank.json", persona=None, funnel_stage=None):
    with open(path, "r", encoding="utf-8") as f:
        all_prompts = json.load(f)

    filtered = [
        p for p in all_prompts
        if (persona is None or p["tags"].get("persona") == persona) and
           (funnel_stage is None or p["tags"].get("funnel_stage") == funnel_stage)
    ]

    return random.choice(filtered if filtered else all_prompts)

def is_memory_based(output):
    return any(tag in output for tag in ["MatrixID", "source_tag=true", "[MATRIX-OS MEMORY]"])

session_id = session.get("username", "anonymous") if has_request_context() else "anonymous"


import json

def load_session(session_id):
    with app.app_context():
        messages = Message.query.filter_by(username=session_id).order_by(Message.timestamp).all()
        return [
            {"user": json.loads(m.content)} if m.role == "user" else {"bot": json.loads(m.content)}
            for m in messages
        ]

def save_session(session_id, session_memory):
    with app.app_context():
        Message.query.filter_by(username=session_id).delete()
        for msg in session_memory:
            if "user" in msg:
                db.session.add(Message(
                    username=session_id,
                    role="user",
                    content=json.dumps(msg["user"])
                ))
            elif "bot" in msg:
                db.session.add(Message(
                    username=session_id,
                    role="assistant",
                    content=json.dumps(msg["bot"])
                ))
        db.session.commit()


with app.app_context():
    session_memory = load_session(session_id)
drift_count = 0
user_memory = {}

# Load config from YAML
def load_config():
    with open("helix_runtime/config.yaml", "r") as file:
        return yaml.safe_load(file)

config = load_config()
#TOKEN_ID = config["helix_token"]
#redis_url = config["redis_url"]
#gcs_bucket = config["gcs_bucket"]

# Initialize memory + router
#memory = HelixMemory(token_id=TOKEN_ID, redis_url=redis_url, gcs_bucket=gcs_bucket)
router = MatrixRouter(memory=session_memory)

def respond_to_user(prompt):
    return router.route(prompt)

def handle_input(message_history, latest_prompt):
    user_input = ""
    for m in reversed(message_history):
        if "user" in m:
            user_input = m["user"]
            break
    if is_matrixbot_shell_command(user_input):
        return run_matrixbot_shell_command(user_input)
    # Symbolic override
    if detect_symbolic(user_input):
        response = route_symbolic_input(user_input, memory=session_memory)
    else:
        # FULL LLM CALL HERE
        response = call_mistral(message_history, latest_prompt)

    save_session(session_id, session_memory)
    if "SnapCTA" in response or "variant_pool" in response:
        session_memory.append({"bot": response})

    return response


def detect_symbolic(text):
    return text.strip().lower().startswith(("symbolic:", "/symbol", "[symbolic]", "🔣"))


# PHASE 1: TheaGate-v1 — Symbolic Trigger Modulation
def is_conversational(input_text):
    input_text = input_text.lower().strip()
    common_inputs = {"hi", "hello", "hey", "yo", "sup", "ok", "yes", "no", "cool"}
    return input_text in common_inputs and len(input_text.split()) < 3


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
    if isinstance(user_input, list):
        input_text = user_input[-1]["content"] if user_input else ""
    else:
        input_text = user_input

    if is_conversational(input_text):

        if user_memory.get('last_prompt_type') == 'symbolic':
            return "Switching from symbolic mode. Want to continue a normal chat?"
        return "Hi. You’re in MatrixOS. Want symbolic, strategic, or conversational mode?"

    global drift_count
    if drift_count > 3:
        return "Symbolic loop limit reached. Switching to dialogue mode."

    intent = classify_intent(input_text)
    tone = TONE_STATE[intent]
    #parsed = parse_input(input_text)
    
    #core_reply = process_matrix_logic(input_text, parsed)
    core_reply = call_mistral([{"role": "user", "content": input_text}])
    response = apply_conversational_tone(core_reply, tone)

    update_dialogue_memory(input_text, response)
    save_session(session_id, session_memory)
    return response


def process_matrix_logic(input_text, parsed):
    if parsed['type'] == 'symbolic':
        return f"[Symbolic]: Triggered symbolic module {parsed['route']}"
    elif parsed['type'] == 'funnel':
        return call_mistral([{"role": "user", "content": input_text}])  # run through LLM
    else:
        return call_mistral([{"role": "user", "content": input_text}])


def process_user_input_logic(input_text):
    routed = route_matrix_intelligence(input_text)
    return run_matrix_module(routed, input=input_text)


def is_matrixbot_shell_command(text):
    return isinstance(text, str) and text.strip().startswith("/matrixbot.")


def dict_to_matrix_text(blocks: dict) -> str:
    lines = []
    for k, v in blocks.items():
        if isinstance(v, list):
            lines.append(f"[{k}]:")
            for item in v:
                lines.append(f"• {item}")
        elif isinstance(v, dict):
            import json
            lines.append(f"[{k}]: {json.dumps(v)}")
        else:
            lines.append(f"[{k}]: {v}")
    return "\n".join(lines)

GCS_BUCKET_NAME = "gitm-llm"
ACTIVITY_FILE = "activity_log.json"

def update_activity_timestamp():
    credentials = service_account.Credentials.from_service_account_file("gitm-llm-222752841c92.json")
    client = storage.Client(credentials=credentials, project="gitm-llm")  # replace with your project
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(ACTIVITY_FILE)
    now_utc = datetime.utcnow().isoformat()
    blob.upload_from_string(json.dumps({"last_active_utc": now_utc}), content_type='application/json')



# --- App Runner ---
if __name__ == "__main__":
    app.run(debug=False)
