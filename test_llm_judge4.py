from harness.providers import MockLLMProvider
llm = MockLLMProvider()
prompt = "Analyze this"
print(repr(llm.complete([{"role": "user", "content": prompt}], system="test")))
