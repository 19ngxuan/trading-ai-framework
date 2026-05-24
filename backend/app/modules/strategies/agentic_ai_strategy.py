from app.modules.agents import SingleAgent
from app.modules.agents.types import AgentContext, AgentRunResult


class AgenticAIStrategy:
    source_name = "AgenticAIStrategy"

    def __init__(self, agent: SingleAgent | None = None) -> None:
        self.agent = agent or SingleAgent()

    def decide(self, context: AgentContext) -> AgentRunResult:
        return self.agent.run(context)
