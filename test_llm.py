from harness.providers import MockLLMProvider
llm = MockLLMProvider()
print(repr(llm.complete([{"role": "user", "content": "Analyze this"}], system="You are an expert evaluator...")))
