import redis
import json
import os

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def save_session(session_id, data):
    r.set(f"session:{session_id}", json.dumps(data))

def load_session(session_id):
    data = r.get(f"session:{session_id}")
    return json.loads(data) if data else []

def clear_session(session_id):
    r.delete(f"session:{session_id}")
