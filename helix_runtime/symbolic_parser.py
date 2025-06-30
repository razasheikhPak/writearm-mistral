from helix_runtime.helix_memory import HelixMemory
from core.mistral_engine import call_mistral

def route_symbolic_input(user_input, memory):
    if "reflect" in user_input or "behavior_test" in user_input:
        return run_matrixbot_shell_command(user_input)

    # Let symbolic_core generate behaviorally compliant output
    memory_obj = HelixMemory(session_id="anonymous")
    prompt, reply = memory_obj.generate_symbolic_prompt(user_input)

    # Optionally call SymbolicCore here to enrich further
    from helix_runtime.symbolic_core import SymbolicCore
    enriched_reply = SymbolicCore().transform(reply)

    memory.append({"user": user_input, "bot": enriched_reply})
    return enriched_reply


def run_matrixbot_shell_command(cmd):
    import re

    # Extract prompt string dynamically
    prompt_match = re.search(r'--prompt="([^"]+)"', cmd)
    mode_match = re.search(r'--mode=(\w+)', cmd)
    input_mode = mode_match.group(1) if mode_match else "symbolic"

    if cmd.startswith("/matrixbot.reflect") and prompt_match:
        user_prompt = prompt_match.group(1)

        # Wrap in Matrix-OS symbolic format
        symbolic_input = f"""[SYMBOLIC PROMPT]: {user_prompt}
        [MODE]: {input_mode}
        [MATRIX_OS]: Please analyze this prompt using symbolic reasoning, emotional layering, and strategic routing. Inject appropriate [INTENT], [THOUGHT], [OUTPUT], and [MATRIX_ID].
        """

        messages = [{"role": "user", "content": symbolic_input}]
        return call_mistral(messages)

    if cmd.startswith("/matrixbot.behavior_test") and prompt_match:
        behavior_prompt = prompt_match.group(1)
        messages = [{
            "role": "user",
            "content": f"""[BEHAVIOR TEST]: {behavior_prompt}
            Please evaluate persona behavior logic, tone modulation, and Conversion-OS layering. Include [THOUGHT], [MAX SCORE], and emotional hooks if detected.
            """
        }]
        return call_mistral(messages)

    # Generic symbolic fallback
    if prompt_match:
        fallback_prompt = prompt_match.group(1)
        messages = [{"role": "user", "content": fallback_prompt}]
        return call_mistral(messages)

    return "⚠️ Could not parse symbolic command."
