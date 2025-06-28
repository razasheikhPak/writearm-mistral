# max_audit.py

class MAXAudit:
    def __init__(self, memory):
        self.memory = memory

    def score(self, prompt):
        # TODO: Hook to symbolic memory analysis later
        if "revolution" in prompt.lower():
            return 9
        elif "build" in prompt.lower():
            return 8
        else:
            return 5
