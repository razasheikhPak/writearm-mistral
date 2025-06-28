cognitive_triggers = {
    "write article": "/run generate-article source=Matrix-241 tone=conversion funnel=mid emotional=LXB10k",
    "email sequence": "/run email-generate campaign=liveOS funnel=action stage=3",
    "SEO longform": "/run matrix-seo mode=ConPro-v4 intent=inform",
    "funnel gap": "/run funnel-analyze source=MAX funnel=retention",
    "launch plan": "/run strategy-generate module=ProductLaunchOS version=latest"
}

def auto_cognition(prompt, memory):
    if memory.get("role") == "Architect" and memory.get("context") in ["strategy", "copy", "growth"]:
        for phrase, command in cognitive_triggers.items():
            if phrase in prompt:
                return command
    return None
