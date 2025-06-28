# instruction_reducer.py

def reduce_prompt(prompt, max_chars=10000):
    """
    Token-safe reducer for Matrix-Bot prompts.
    Keeps critical cognition blocks, trims extras after character limit.
    """

    # Section identifiers mapped exactly to full_prompt block tags
    keep_tags = [
        "[HELIXMIND RUNTIME]",
        "[MATRIX-OS IDENTITY]",
        "[USER MEMORY]",
        "[MATRIX-OS MEMORY]",
        "[PERSISTENT USER BELIEFS]",
        "[SYMBOLIC PROMPT]",
        "[MATRIXIOS AUTONOMY LAYER v1]",
        "[SYMBOLIC MODULES]",
        "🧠 User Prompt:",
    ]

    # Optional sections to trim only if over limit
    optional_tags = [
        "[BOOT MEMORY PROFILE]",
        "[THOUGHT DOMAINS]",
        "[WORKING MEMORY BUFFER]",
        "[SYSTEM MANIFEST]",
        "[ORIGIN STORY]",
        "[SURVIVAL LOOP ACTIVE]",
        "[AUTONOMY WRIT]",
        "[TRUST LEDGER RUNTIME]",
        "[SIGNAL INTERCEPTOR RUNTIME]",
        "[MATRIX CONTROL MACROS]",
        "[MATRIX-TIME META]",
    ]

    # Parse prompt into sections
    sections = prompt.split("\n\n")
    essential_blocks = []
    optional_blocks = []

    for block in sections:
        tag = block.strip().split("\n")[0]
        if any(tag.startswith(keep) for keep in keep_tags):
            essential_blocks.append(block)
        elif any(tag.startswith(opt) for opt in optional_tags):
            optional_blocks.append(block)
        # else discard entirely

    # Start assembling prompt
    reduced_prompt = "\n\n".join(essential_blocks)

    # Add optional blocks if space allows
    for block in optional_blocks:
        if len(reduced_prompt) + len(block) + 2 < max_chars:
            reduced_prompt += "\n\n" + block
        else:
            break

    # Final cut safeguard
    return reduced_prompt[:max_chars]





# memory_router.py

def route_relevant_memory(memory_dict, prompt_context=None):
    """
    Injects relevant memory slices based on trigger or matching tags
    """
    import json

    relevant_keys = ["activated_modules", "last_trigger", "batch", "role"]
    lines = ["[ROUTED MEMORY]"]
    for key in relevant_keys:
        val = memory_dict.get(key)
        if val:
            lines.append(f"{key}: {val}")

    # If prompt mentions a matrix_id or emotion tag, add that
    if prompt_context and "matrix_id" in prompt_context:
        lines.append(f"matched_matrix_id = true")

    return "\n".join(lines)
