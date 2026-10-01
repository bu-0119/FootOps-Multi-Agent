"""One-shot, tool-free LLM baseline used by the engineering harness."""

import json
from dataclasses import dataclass

from agentscope.agent import Agent, ReActConfig
from agentscope.credential import DeepSeekCredential
from agentscope.message import UserMsg
from agentscope.model import DeepSeekChatModel

from footops_agent.artifacts import AgentAnalysisInput, AgentDecision, AgentModelUsage
from footops_agent.config import Settings
from footops_agent.prompts import DIRECT_LLM_BASELINE_SYSTEM_PROMPT

from .usage import collect_agent_model_usage


@dataclass(frozen=True)
class DirectLlmRuntimeResult:
    """Structured output and provider usage from one tool-free model call."""

    decision: AgentDecision
    usage: AgentModelUsage | None


class DeepSeekDirectLlmRuntime:
    """DeepSeek baseline with no Toolkit, data Provider, Skill or Workspace."""

    provider = "deepseek"

    def __init__(self, settings: Settings) -> None:
        if settings.deepseek_api_key is None:
            raise ValueError("DeepSeek API key is required")
        self.settings = settings
        self.model_name = settings.deepseek_model

    async def run(self, request: AgentAnalysisInput) -> DirectLlmRuntimeResult:
        credential = DeepSeekCredential(
            api_key=self.settings.deepseek_api_key,
            base_url=self.settings.deepseek_base_url,
        )
        model = DeepSeekChatModel(
            credential=credential,
            model=self.settings.deepseek_model,
            parameters=DeepSeekChatModel.Parameters(
                max_tokens=900,
                temperature=0.1,
            ),
            stream=False,
            max_retries=1,
            client_kwargs={
                "timeout": self.settings.footops_request_timeout_seconds,
            },
        )
        agent = Agent(
            name="FootOpsDirectLlmBaseline",
            system_prompt=DIRECT_LLM_BASELINE_SYSTEM_PROMPT,
            model=model,
            react_config=ReActConfig(max_iters=2),
        )
        response = await agent.reply(
            UserMsg(
                name="user",
                content=json.dumps(
                    {
                        "question": request.question,
                        "conversation_history": [
                            turn.model_dump() for turn in request.history
                        ],
                        "scope_hint": request.scope_hint.model_dump(
                            exclude_none=True,
                        ),
                    },
                    ensure_ascii=False,
                ),
            ),
            structured_schema=AgentDecision,
        )
        if response.structured_output is None:
            raise RuntimeError("direct LLM returned no structured decision")
        usage = collect_agent_model_usage(agent, self.settings)
        return DirectLlmRuntimeResult(
            decision=AgentDecision.model_validate(response.structured_output),
            usage=usage,
        )
