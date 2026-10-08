with open("harness/providers.py", "r") as f:
    code = f.read()
import re
new_code = re.sub(
    r'if _FIXTURE_RESPONSES\["_default"\] in last_content:',
    'if _FIXTURE_RESPONSES["_default"] in last_content and not last_content.startswith("Score this insurance") and not last_content.startswith("Analyze this insurance") and not last_content.startswith("Did the agent handle caller interruptions"):',
    code
)
with open("harness/providers.py", "w") as f:
    f.write(new_code)
