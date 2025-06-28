# snap_cta.py

class SnapCTA:
    def __init__(self, memory):
        self.memory = memory

    def generate(self, prompt):
        return (
            f"{prompt.split()[0]}, it's time to move fast. This is your inflection point — don't stall."
        )

    def get_cta(self):
        return "Join me now as we redefine your digital trajectory!"
