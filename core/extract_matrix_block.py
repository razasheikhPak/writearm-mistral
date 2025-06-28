import re

def extract_matrix_blocks(raw_text: str) -> dict:
    """
    Extracts tagged Matrix-OS blocks from raw Mistral output into a structured dictionary.
    Supports multi-line and bullet-style variant pools.
    """
    blocks = {}
    current_key = None
    current_value = []

    lines = raw_text.splitlines()

    for line in lines:
        line = line.strip()

        # Match block start: [KEY]:
        match = re.match(r'^\[(.+?)\](:)?\s*(.*)', line)
        if match:
            if current_key:
                blocks[current_key] = "\n".join(current_value).strip() if current_key != "variant_pool" else current_value

            current_key = match.group(1).strip()
            value = match.group(3).strip()

            if current_key == "variant_pool":
                current_value = []
                if value:
                    current_value.append(value)
            else:
                current_value = [value]


        elif current_key == "variant_pool" and (line.startswith("•") or line.startswith("-")):
            current_value.append(line.strip("•- ").strip())
        elif current_key:
            current_value.append(line)

    # Capture the last block
    if current_key:
        blocks[current_key] = "\n".join(current_value).strip() if current_key != "variant_pool" else current_value

    return blocks

def apply_dynamic_matrix_fixes(response_data: dict, input_prompt: str) -> dict:
    """
    Applies compliance and formatting corrections to Mistral's symbolic response.
    Ensures Markdown integrity, Snap suppression, and manifest completeness.
    """
    symbolic = response_data.get("SYMBOLIC INTERPRETATION", "").strip()
    intent = response_data.get("INTENT", "").strip()
    output = response_data.get("OUTPUT", "").strip()
    snapcta = response_data.get("SNAPCTA", "").strip()
    variant_pool = response_data.get("variant_pool", [])
    manifest = response_data.get("MATRIX_OS_MANIFEST", {})

    # Fix 1: Enforce Markdown-style SYMBOLIC INTERPRETATION if malformed
    if symbolic and "•" not in symbolic:
        response_data["SYMBOLIC INTERPRETATION"] = (
            "• Primary trigger: [System Error or User Command]\n"
            f"• Secondary intent: [{intent or 'Unknown'}]\n"
            "• Resolution priority: [Process Intent → Resolve System Event]"
        )

    # Fix 2: Strip SnapReminder/SilenceNudge lines safely
    if any(keyword in output.lower() for keyword in ["snap_reminder", "silence nudge", "silence_nudge"]):
        cleaned_output = "\n".join(
            line for line in output.splitlines()
            if not any(k in line.lower() for k in ["snap_reminder", "silence nudge", "silence_nudge"])
        )
        response_data["OUTPUT"] = cleaned_output.strip()

    # Fix 3: Add minimal manifest if input implies control context
    if any(term in input_prompt.lower() for term in ["project", "canvas", "snaplayer", "routine"]) and not manifest:
        response_data["MATRIX_OS_MANIFEST"] = {
            "runtime": "MatrixOS.v5-Mistral",
            "codex_ref": "auto-inferred from input",
            "prompt_type": "SystemAction",
            "safety_layers": ["MatrixGate", "SnapDisplayClean"]
        }

    # Fix 4: Optional emotional SnapCTA enforcement (if re-enabled)
    # if isinstance(variant_pool, list) and all("journey" not in v.lower() for v in variant_pool):
    #     variant_pool.append("Snap into focus — your OS journey deserves ignition, not delay.")
    #     response_data["variant_pool"] = variant_pool

    return response_data


# --- App Runner ---
if __name__ == "__main__":
    from threading import Thread

    def run_async_tasks():
        asyncio.run(matrix_routines_async.main())

    #execute_payload("MatrixOS_TransferPayload_v2_FULL.docx")
    Thread(target=run_async_tasks).start()
    app.run(debug=False)



