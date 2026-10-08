from config.settings import get_settings
from harness.providers import build_llm_provider
from harness.models import CallResult, TurnResult

settings = get_settings()
settings.mock_llm = True
llm = build_llm_provider(settings)

result = CallResult(scenario_id="test", run_id="test_run", turns=[
    TurnResult(speaker="agent", text="hello")
])

from scoring.llm_judge import ConversationQualityJudge
print("before eval")
try:
    print(ConversationQualityJudge().evaluate(result, llm))
except Exception as e:
    print(f"Exception: {e}")
