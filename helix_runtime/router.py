# router.py

import json
from helix_runtime.snap_cta import SnapCTA
from helix_runtime.max_audit import MAXAudit
from helix_runtime.variant_generator import VariantGenerator

class MatrixRouter:
    def __init__(self, memory):
        self.memory = memory
        self.snap_cta = SnapCTA(memory)
        self.max = MAXAudit(memory)
        self.variant_gen = VariantGenerator(memory)

    def classify_intent(self, prompt):
        if any(k in prompt.lower() for k in ["build os", "generate copy"]):
            return "TRIGGER"
        return "COGNITION"

    def generate_os(self, prompt):
        intent = self.classify_intent(prompt)
        matrix_id = self.memory.create_matrix_id(prompt)

        thought = f"As Matrix-Bot, I interpret this as a {intent}. Using symbolic modules, I will generate a full OS response."
        output = self.snap_cta.generate(prompt)
        max_score = self.max.score(prompt)
        variants = self.variant_gen.generate(prompt)

        return {
            "INTENT": f"To {prompt.strip()}",
            "ACTION": "Build Matrix-OS aligned output using active modules",
            "THOUGHT": thought,
            "OUTPUT": output,
            "FOLLOW_UP": "Would you like to activate Snap or run MAX diagnostics?",
            "MATRIX_ID": matrix_id,
            "SNAPCTA": self.snap_cta.get_cta(),
            "SYMBOLIC INTERPRETATION": intent,
            "MAX SCORE": max_score,
            "approved_copy": output,
            "variant_pool": variants
        }
