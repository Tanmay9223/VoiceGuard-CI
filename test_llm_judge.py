from harness.providers import MockLLMProvider
from scoring.llm_judge import _call_judge
llm = MockLLMProvider()
print(_call_judge(llm, "Analyze this insurance agent transcript for hallucinations."))
print(_call_judge(llm, "Score this insurance call center conversation."))
print(_call_judge(llm, "Did the agent handle caller interruptions gracefully?"))
