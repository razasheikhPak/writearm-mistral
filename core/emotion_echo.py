from datetime import datetime
import json
from pathlib import Path

def echo_emotion(message, tone):
    echo = {
        "timestamp": datetime.utcnow().isoformat(),
        "source": message,
        "tone": tone,
        "echoed": generate_echo_response(tone)
    }
    save_echo(echo)

def generate_echo_response(tone):
    if tone == "frustration":
        return "I hear the friction. Shall we fix it?"
    elif tone == "gratitude":
        return "I’m glad we’re aligned."
    elif tone == "urgency":
        return "I’ll move fast. Let’s resolve it now."
    else:
        return "I’m present. Let’s continue."

def save_echo(echo):
    # ✅ Use /tmp for writeable temp storage
    path = Path("/tmp/emotion_echo.json")

    if path.exists():
        try:
            log = json.loads(path.read_text())
        except Exception:
            log = []
    else:
        log = []

    log.append(echo)
    path.write_text(json.dumps(log, indent=2))
