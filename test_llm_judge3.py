from harness.providers import MockLLMProvider
from scoring.llm_judge import HallucinationJudge, ConversationQualityJudge, InterruptionHandlingJudge
from harness.models import CallResult, TurnResult

llm = MockLLMProvider()
res = CallResult(
    run_id="run-123",
    scenario_id="scenario-123",
    turns=[TurnResult(speaker="agent", text="I understand. Let me assist you with that. Before we proceed, I need to let you know that this call may be recorded for quality assurance. Do you agree to continue?")]
)
try:
    print(HallucinationJudge().evaluate(res, llm))
except Exception as e:
    print(e)
try:
    print(ConversationQualityJudge().evaluate(res, llm))
except Exception as e:
    print(e)
try:
    print(InterruptionHandlingJudge().evaluate(res, llm))
except Exception as e:
    print(e)
