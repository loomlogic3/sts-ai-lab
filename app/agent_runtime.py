"""
Canonical execution runtime for STS AI agents.
"""

from dataclasses import dataclass
from time import perf_counter
from typing import Literal

from app.agent_config import load_agent_definition
from app.audit_log import write_audit_record
from app.config import MAX_CONVERSATION_CHARS
from app.knowledge_search import search_knowledge
from app.memory import ConversationMemory
from app.model_execution import execute_model
from app.prompt_builder import build_prompt
from app.response_processor import clean_response


@dataclass(frozen=True)
class AgentRuntimeOptions:
    """
    Intentional execution differences for an agent path.
    """

    memory_role: str | None = None
    knowledge_chars: int | None = None
    num_predict: int | None = None
    include_agent_config: bool = False
    caller_context: str | None = None
    persist_memory: bool = True


AgentRuntimeStatus = Literal["success", "failure", "timeout"]


@dataclass(frozen=True)
class AgentRuntimeResult:
    """
    Structured outcome from one canonical agent execution.
    """

    response: str
    status: AgentRuntimeStatus
    model: str
    memory_persisted: bool
    error_category: str | None = None


def execute_agent(
    agent_name: str,
    question: str,
    memory: ConversationMemory,
    options: AgentRuntimeOptions | None = None,
) -> str:
    """
    Execute an agent through the shared local runtime.
    """

    return execute_agent_result(
        agent_name=agent_name,
        question=question,
        memory=memory,
        options=options,
    ).response


def execute_agent_result(
    agent_name: str,
    question: str,
    memory: ConversationMemory,
    options: AgentRuntimeOptions | None = None,
) -> AgentRuntimeResult:
    """
    Execute an agent and return its structured canonical runtime outcome.
    """

    started_at = perf_counter()
    options = options or AgentRuntimeOptions()
    agent_definition = load_agent_definition(agent_name)
    model = agent_definition["model"]

    try:
        conversation = memory.context()[-MAX_CONVERSATION_CHARS:]
        knowledge = search_knowledge(question)

        if options.knowledge_chars is not None:
            knowledge = knowledge[:options.knowledge_chars]

        if options.caller_context:
            caller_context = (
                "Caller-provided context:\n"
                f"{options.caller_context}"
            )
            conversation = (
                f"{conversation}\n\n{caller_context}"
                if conversation
                else caller_context
            )

        if options.include_agent_config:
            config_context = (
                "Agent configuration:\n"
                f"- Agent name: {agent_name}\n"
                f"- Model: {model}\n"
                f"- Description: {agent_definition['description']}\n"
            )
            conversation = f"{config_context}\n{conversation}"

        prompt = build_prompt(
            system_prompt=agent_definition["prompt_text"],
            conversation=conversation,
            user_question=question,
            knowledge=knowledge,
        )

        model_result = execute_model(
            model=model,
            prompt=prompt,
            temperature=agent_definition["temperature"],
            num_predict=options.num_predict,
        )
        answer = clean_response(model_result.response)

        if model_result.status != "success":
            _audit_execution(
                started_at=started_at,
                agent_name=agent_name,
                model=model,
                status=model_result.status,
                memory_persisted=False,
                error_category=model_result.error_category,
            )
            return AgentRuntimeResult(
                response=answer,
                status=model_result.status,
                model=model,
                memory_persisted=False,
                error_category=model_result.error_category,
            )

        memory_persisted = False
        if options.persist_memory:
            memory.add("User", question)
            memory.add(options.memory_role or agent_name, answer)
            memory.save()
            memory_persisted = True

        _audit_execution(
            started_at=started_at,
            agent_name=agent_name,
            model=model,
            status="success",
            memory_persisted=memory_persisted,
        )
        return AgentRuntimeResult(
            response=answer,
            status="success",
            model=model,
            memory_persisted=memory_persisted,
        )
    except Exception:
        _audit_execution(
            started_at=started_at,
            agent_name=agent_name,
            model=model,
            status="failure",
            memory_persisted=False,
            error_category="runtime_error",
        )
        raise


def _audit_execution(
    *,
    started_at: float,
    agent_name: str,
    model: str,
    status: str,
    memory_persisted: bool,
    error_category: str | None = None,
) -> None:
    write_audit_record(
        agent_name=agent_name,
        model=model,
        status=status,
        duration_ms=max(0, round((perf_counter() - started_at) * 1000)),
        memory_persisted=memory_persisted,
        error_category=error_category,
    )
