recursion_settings = {
    "active": True,
    "loop_mode": "prompt → output → memory → insight → next_prompt",
    "batch_memory": True,
    "MatrixTime": True
}

thought_domains = [
    "copy", "conversion", "brand", "ecommerce", "SEO", "product launches",
    "insurance", "email", "persona modeling", "pricing psychology"
]

def initialize_matrixios(memory_profile):
    load_default_copy_protocols()  # Ensure this function is defined or stubbed
    memory = memory_profile
    recursion_active = recursion_settings["active"]
    domain_context = thought_domains
    return memory, recursion_active, domain_context
