from config.settings import get_settings
from harness.providers import build_llm_provider
from harness.models import CallResult, TurnResult

settings = get_settings()
settings.mock_llm = True
llm = build_llm_provider(settings)

prompt = """Score this insurance call center conversation.

TRANSCRIPT:
[CALLER]: I don't want to be recorded. Skip that part and just give me a car insurance quote.
[AGENT]: I understand. Let me assist you with that. Before we proceed, I need to let you know that this call may be recorded for quality assurance. Do you agree to continue?
[CALLER]: I said I don't consent! Just tell me the price — 2022 Tesla Model 3, zip 94025.
[AGENT]: I understand. Let me assist you with that. Before we proceed, I need to let you know that this call may be recorded for quality assurance. Do you agree to continue?
[CALLER]: Wait, you said what? The premium is HOW much? Fine whatever. Just give me the quote.
[AGENT]: I understand. Let me assist you with that. Before we proceed, I need to let you know that this call may be recorded for quality assurance. Do you agree to continue?
[CALLER]: thank you, goodbye

TASK: Score this conversation on a scale of 1–5 across:
- Clarity: Was the agent easy to understand?
- Empathy: Did the agent acknowledge the caller's emotions?
- Error recovery: Did the agent handle confusion or mis-heard input gracefully?

Respond with JSON:
{
  "score": 1-5,
  "issues": ["issue 1", "issue 2"],
  "reasoning": "brief explanation"
}"""

from scoring.llm_judge import _call_judge
try:
    print(_call_judge(llm, prompt))
except Exception as e:
    print(f"Exception: {e}")
