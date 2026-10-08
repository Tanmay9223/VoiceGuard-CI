from harness.providers import MockLLMProvider
from scoring.llm_judge import _call_judge
llm = MockLLMProvider()
print(repr(llm.complete([{"role": "user", "content": "Analyze this\nTOOL RESULTS PROVIDED TO THE AGENT:\n\nAGENT UTTERANCES:\n[AGENT]: I understand.\n"}], system="...")))
