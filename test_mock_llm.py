from harness.providers import MockLLMProvider
llm = MockLLMProvider()
print("test 1:", repr(llm.complete([{"role": "user", "content": "Did the agent"}], system="...")))
print("test 2:", repr(llm.complete([{"role": "user", "content": "did the agent"}], system="...")))
