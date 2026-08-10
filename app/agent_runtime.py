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
from app.model_execution import ModelExecutionMetrics, execute_model
from app.prompt_builder import PromptProfile, build_prompt_result
from app.response_processor import clean_response
from app.runtime_status import (
    RuntimeStage,
    RuntimeStatusCallback,
    RuntimeStatusEvent,
)


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
class PreprocessingTimings:
    """Monotonic wall-clock timings for major pre-model runtime stages."""

    agent_loading_ms: int = 0
    memory_preparation_ms: int = 0
    knowledge_retrieval_ms: int = 0
    prompt_construction_ms: int = 0


@dataclass(frozen=True)
class AgentExecutionProfile:
    """Transient prompt and model performance metadata for one invocation."""

    prompt_profile: PromptProfile = PromptProfile()
    preprocessing: PreprocessingTimings = PreprocessingTimings()
    model_metrics: ModelExecutionMetrics = ModelExecutionMetrics()


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
    profile: AgentExecutionProfile = AgentExecutionProfile()


def execute_agent(
    agent_name: str,
    question: str,
    memory: ConversationMemory,
    options: AgentRuntimeOptions | None = None,
    on_status: RuntimeStatusCallback | None = None,
) -> str:
    """
    Execute an agent through the shared local runtime.
    """

    return execute_agent_result(
        agent_name=agent_name,
        question=question,
        memory=memory,
        options=options,
        on_status=on_status,
    ).response


def execute_agent_result(
    agent_name: str,
    question: str,
    memory: ConversationMemory,
    options: AgentRuntimeOptions | None = None,
    on_status: RuntimeStatusCallback | None = None,
) -> AgentRuntimeResult:
    """
    Execute an agent and return its structured canonical runtime outcome.
    """

    started_at = perf_counter()
    options = options or AgentRuntimeOptions()
    model = None

    try:
        _emit_status(on_status, "loading_agent", agent_name)
        stage_started_at = perf_counter()
        agent_definition = load_agent_definition(agent_name)
        agent_loading_ms = _elapsed_ms(stage_started_at)
        model = agent_definition["model"]

        _emit_status(on_status, "reading_memory", agent_name, model)
        stage_started_at = perf_counter()
        full_conversation = memory.context()
        conversation_truncated = len(full_conversation) > MAX_CONVERSATION_CHARS
        conversation = full_conversation[-MAX_CONVERSATION_CHARS:]
        memory_preparation_ms = _elapsed_ms(stage_started_at)

        _emit_status(on_status, "searching_knowledge", agent_name, model)
        stage_started_at = perf_counter()
        knowledge = search_knowledge(question)
        knowledge_truncated = False
        if options.knowledge_chars is not None:
            knowledge_truncated = len(knowledge) > options.knowledge_chars
            knowledge = knowledge[:options.knowledge_chars]
        knowledge_retrieval_ms = _elapsed_ms(stage_started_at)

        agent_context = ""
        if options.include_agent_config:
            agent_context = (
                "Agent configuration:\n"
                f"- Agent name: {agent_name}\n"
                f"- Model: {model}\n"
                f"- Description: {agent_definition['description']}\n"
            )

        _emit_status(on_status, "building_prompt", agent_name, model)
        stage_started_at = perf_counter()
        prompt_result = build_prompt_result(
            system_prompt=agent_definition["prompt_text"],
            conversation=conversation,
            user_question=question,
            knowledge=knowledge,
            caller_context=options.caller_context or "",
            agent_context=agent_context,
            conversation_truncated=conversation_truncated,
            knowledge_truncated=knowledge_truncated,
        )
        prompt_construction_ms = _elapsed_ms(stage_started_at)
        prompt = prompt_result.prompt

        _emit_status(on_status, "waiting_for_model", agent_name, model)
        model_result = execute_model(
            model=model,
            prompt=prompt,
            temperature=agent_definition["temperature"],
            num_predict=options.num_predict,
        )
        _emit_status(on_status, "processing_response", agent_name, model)
        answer = clean_response(model_result.response)
        execution_profile = AgentExecutionProfile(
            prompt_profile=prompt_result.profile,
            preprocessing=PreprocessingTimings(
                agent_loading_ms=agent_loading_ms,
                memory_preparation_ms=memory_preparation_ms,
                knowledge_retrieval_ms=knowledge_retrieval_ms,
                prompt_construction_ms=prompt_construction_ms,
            ),
            model_metrics=model_result.metrics,
        )

        if model_result.status != "success":
            _audit_execution(
                started_at=started_at,
                agent_name=agent_name,
                model=model,
                status=model_result.status,
                memory_persisted=False,
                error_category=model_result.error_category,
            )
            result = AgentRuntimeResult(
                response=answer,
                status=model_result.status,
                model=model,
                memory_persisted=False,
                error_category=model_result.error_category,
                profile=execution_profile,
            )
            _emit_status(on_status, model_result.status, agent_name, model)
            return result

        memory_persisted = False
        if options.persist_memory:
            _emit_status(on_status, "saving_memory", agent_name, model)
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
        result = AgentRuntimeResult(
            response=answer,
            status="success",
            model=model,
            memory_persisted=memory_persisted,
            profile=execution_profile,
        )
        _emit_status(on_status, "complete", agent_name, model)
        return result
    except Exception:
        if model is not None:
            _audit_execution(
                started_at=started_at,
                agent_name=agent_name,
                model=model,
                status="failure",
                memory_persisted=False,
                error_category="runtime_error",
            )
        _emit_status(on_status, "failure", agent_name, model)
        raise


def _emit_status(
    callback: RuntimeStatusCallback | None,
    stage: RuntimeStage,
    agent_name: str,
    model: str | None = None,
) -> None:
    if callback is None:
        return
    try:
        callback(RuntimeStatusEvent(stage, agent_name, model))
    except Exception:
        pass


def _elapsed_ms(started_at: float) -> int:
    return max(0, round((perf_counter() - started_at) * 1000))


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
