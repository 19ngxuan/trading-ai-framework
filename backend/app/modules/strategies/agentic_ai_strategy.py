from app.domain.enums import AgentMode
from app.modules.agents import SingleAgent
from app.modules.agents.pipeline_agent import AgentDecisionPipeline
from app.modules.agents.types import AgentContext, AgentRunResult


class AgenticAIStrategy:
    source_name = "AgenticAIStrategy"

    def __init__(
        self,
        agent: SingleAgent | None = None,
        pipeline: AgentDecisionPipeline | None = None,
    ) -> None:
        self.agent = agent or SingleAgent()
        self.pipeline = pipeline or AgentDecisionPipeline()

    def decide(self, context: AgentContext) -> AgentRunResult:
        if context.agent_mode is AgentMode.PIPELINE:
            return self.pipeline.run(context)
        return self.agent.run(context)
