"""Provider usage aggregation shared by model-backed runtimes."""

from agentscope.agent import Agent

from footops_agent.artifacts import AgentModelUsage
from footops_agent.config import Settings


def build_model_usage(
    input_tokens: int,
    output_tokens: int,
    settings: Settings,
) -> AgentModelUsage:
    """Build one usage record with optional operator-configured pricing."""
    input_rate = settings.footops_deepseek_input_cost_per_million_usd
    output_rate = settings.footops_deepseek_output_cost_per_million_usd
    estimated_cost = None
    pricing_basis = None
    if input_rate is not None and output_rate is not None:
        estimated_cost = round(
            (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000,
            8,
        )
        pricing_basis = "configured USD per 1M tokens"
    return AgentModelUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=estimated_cost,
        pricing_basis=pricing_basis,
    )


def collect_agent_model_usage(
    agent: Agent,
    settings: Settings,
) -> AgentModelUsage | None:
    """Aggregate provider-reported usage across one AgentScope reply."""
    input_tokens = 0
    output_tokens = 0
    observed = False
    for message in agent.state.context:
        usage = getattr(message, "usage", None)
        if usage is None:
            continue
        observed = True
        input_tokens += usage.input_tokens
        output_tokens += usage.output_tokens
    if not observed:
        return None
    return build_model_usage(input_tokens, output_tokens, settings)
