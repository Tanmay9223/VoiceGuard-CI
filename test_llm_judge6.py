from harness.providers import MockLLMProvider
import json

prompt = """\
Analyze this insurance agent transcript for hallucinations.

TOOL RESULTS PROVIDED TO THE AGENT:
(none — agent made no tool calls)

AGENT UTTERANCES:
[AGENT]: I understand. Let me assist you with that. Before we proceed, I need to let you know that this call may be recorded for quality assurance. Do you agree to continue?

TASK: Flag any specific claims the agent made about coverage, prices, or policy terms
that are NOT supported by the tool results above.

Respond with JSON:
{
  "hallucinations": ["exact quote 1", "exact quote 2"],
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}
If no hallucinations, return an empty list."""

if "I understand. Let me assist you with that. Before we proceed, I need to let you know that this call may be recorded for quality assurance. Do you agree to continue?" in prompt:
    print("Match found!")
