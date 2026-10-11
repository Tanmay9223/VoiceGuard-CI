with open("harness/providers.py", "r") as f:
    code = f.read()

import re

# Update MockLLMProvider to correctly respond to the agent for "hello/hi", and NOT return "thank you, goodbye"
new_code = re.sub(
    r'        if _FIXTURE_RESPONSES\["_default"\] in last_content and not last_content.startswith\("Score this insurance"\) and not last_content.startswith\("Analyze this insurance"\) and not last_content.startswith\("Did the agent handle caller interruptions"\):\n            return "thank you, goodbye"\n            \n        first_word = last_content\.split\(\)\[0\]\.lower\(\) if last_content else "_default"\n        response = _FIXTURE_RESPONSES\.get\(first_word, _FIXTURE_RESPONSES\["_default"\]\)',
    '''        if _FIXTURE_RESPONSES["_default"] in last_content and not last_content.startswith("Score this insurance") and not last_content.startswith("Analyze this insurance") and not last_content.startswith("Did the agent handle caller interruptions"):
            return "thank you, goodbye"

        # Match expected prefixes for judge evaluations
        if last_content.startswith("Score this insurance"):
            first_word = "score"
        elif last_content.startswith("Analyze this insurance"):
            first_word = "analyze"
        elif last_content.startswith("Did the agent handle caller interruptions"):
            first_word = "did"
        else:
            first_word = last_content.split()[0].lower() if last_content else "_default"

        response = _FIXTURE_RESPONSES.get(first_word, _FIXTURE_RESPONSES["_default"])''',
    code
)

with open("harness/providers.py", "w") as f:
    f.write(new_code)
