from helix_runtime.helix_memory import HelixMemory

class SymbolicCore:
    def __init__(self, session_id="anonymous"):
        self.memory = HelixMemory(session_id=session_id)

    def run(self, user_input):
        return self.memory.generate_symbolic_prompt(user_input)
