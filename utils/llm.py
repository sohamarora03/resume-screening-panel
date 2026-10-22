"""
LLM factory.

* Live mode: CrewAI's native OpenAI-compatible client pointed at Groq.
* Demo mode: `DemoLLM`, a CrewAI `BaseLLM` subclass. CrewAI still builds the
  prompts and runs the agents/tasks exactly as in live mode - only the final
  "model" call is answered by each agent's offline engine instead of the
  internet. This keeps one code path for both modes.
"""
import json
import time

from crewai import LLM, BaseLLM

import config
from agents import bias_checker, hr_summary, jd_analyst, screener
from tasks.prompts import END, START

DEMO_ENGINES = {
    jd_analyst.ROLE: jd_analyst.demo_respond,
    screener.ROLE: screener.demo_respond,
    bias_checker.ROLE: bias_checker.demo_respond,
    hr_summary.ROLE: hr_summary.demo_respond,
}


class DemoLLM(BaseLLM):
    """Offline stand-in for a real model, routed by the calling agent's role."""

    def call(self, messages, tools=None, callbacks=None, available_functions=None,
             from_task=None, from_agent=None, response_model=None, **kwargs):
        text = messages if isinstance(messages, str) else "\n".join(
            str(m.get("content", "")) for m in messages)
        start, end = text.rfind(START), text.rfind(END)
        if start == -1 or end == -1:
            raise ValueError("DemoLLM: task input markers not found")
        payload = json.loads(text[start + len(START):end])
        role = getattr(from_agent, "role", None)
        engine = DEMO_ENGINES.get(role)
        if engine is None:
            raise ValueError(f"DemoLLM: no offline engine for agent role {role!r}")
        time.sleep(config.DEMO_DELAY)  # lets the UI show which agent is working
        return json.dumps(engine(payload))

    def supports_function_calling(self) -> bool:
        return False


def get_llm():
    if config.DEMO_MODE:
        return DemoLLM(model="demo-offline-engine")
    return LLM(
        model=f"openai/{config.GROQ_MODEL}",
        base_url=config.GROQ_BASE_URL,
        api_key=config.GROQ_API_KEY,
        temperature=0.1,
    )
