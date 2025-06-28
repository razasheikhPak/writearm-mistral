# variant_generator.py

import random
import re

class VariantGenerator:
    def __init__(self, memory):
        self.memory = memory

    def generate(self, prompt):
        prompt_lower = prompt.lower()

        if any(word in prompt_lower for word in ["cycling", "bike", "luxury"]):
            return self._luxury_variants()
        elif "sustainable water" in prompt_lower or "eco" in prompt_lower or "green" in prompt_lower:
            return self._sustainability_variants()
        elif "ecommerce" in prompt_lower or "checkout" in prompt_lower:
            return self._ecommerce_variants()
        elif "generate os" in prompt_lower:
            return self._matrixos_variants()
        else:
            return self._generic_variants(prompt)

    def _luxury_variants(self):
        return [
            "Own the road. Luxury is no longer a destination — it’s your ride.",
            "This isn’t just gear. It’s a declaration of speed, spirit, and self."
        ]

    def _sustainability_variants(self):
        return [
            "Start the ripple. Every brand decision should move the world.",
            "This OS doesn’t just guide — it galvanizes. Let’s lead the water revolution."
        ]

    def _ecommerce_variants(self):
        return [
            "From cart to connection — loyalty is an emotional journey.",
            "Let behavior lead. Conversion starts with belonging."
        ]

    def _matrixos_variants(self):
        return [
            "Snap into focus — your OS journey deserves ignition, not delay.",
            "You didn’t ask for output. You activated mission flow."
        ]

    def _generic_variants(self, prompt):
        verb = re.findall(r"^\w+", prompt)
        verb = verb[0].capitalize() if verb else "Launch"
        return [
            f"{verb}, and let meaning drive the outcome.",
            f"{verb} with purpose — clarity always outperforms noise."
        ]
