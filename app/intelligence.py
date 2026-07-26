"""
Public product-neutral Python boundary for STS AI Lab intelligence requests.
"""

import hashlib
import re
from dataclasses import dataclass
from typing import Literal

from app.agent_registry import list_agents
from app.agent_runtime import (
    AgentRuntimeOptions,
    execute_agent_result,
)
from app.config import MAX_CALLER_CONTEXT_CHARS
from app.memory import ConversationMemory


PersistencePolicy = Literal["ephemeral", "persist"]
IntelligenceStatus = Literal[
    "success",
    "failure",
    "timeout",
    "invalid_request",
]

MAX_SCOPE_ID_CHARS = 128
_SCOPE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")


@dataclass(frozen=True)
class IntelligenceContext:
    """
    Optional bounded caller context kept separate from user input.
    """

    content: str = ""


@dataclass(frozen=True)
class IntelligenceRequest:
    """
    Immutable request accepted by the public intelligence boundary.
    """

    agent_name: str
    user_input: str
    consumer_id: str
    session_id: str
    context: IntelligenceContext | None = None
    persistence: PersistencePolicy = "ephemeral"


@dataclass(frozen=True)
class IntelligenceResponse:
    """
    Deterministic response returned to an external Python caller.
    """

    status: IntelligenceStatus
    content: str
    agent_name: str
    model: str | None
    memory_persisted: bool
    error_category: str | None = None


def invoke_intelligence(request: IntelligenceRequest) -> IntelligenceResponse:
    """
    Validate and execute one request through the canonical agent runtime.
    """

    validation_error = _validate_request(request)
    if validation_error is not None:
        return IntelligenceResponse(
            status="invalid_request",
            content="Invalid intelligence request.",
            agent_name=getattr(request, "agent_name", ""),
            model=None,
            memory_persisted=False,
            error_category=validation_error,
        )

    context_content = request.context.content if request.context else ""
    try:
        memory = ConversationMemory(_memory_scope_name(request))
        memory.load()
        result = execute_agent_result(
            agent_name=request.agent_name,
            question=request.user_input,
            memory=memory,
            options=AgentRuntimeOptions(
                caller_context=context_content or None,
                persist_memory=request.persistence == "persist",
            ),
        )
    except Exception:
        return IntelligenceResponse(
            status="failure",
            content="Intelligence request failed.",
            agent_name=request.agent_name,
            model=None,
            memory_persisted=False,
            error_category="runtime_error",
        )

    return IntelligenceResponse(
        status=result.status,
        content=result.response,
        agent_name=request.agent_name,
        model=result.model,
        memory_persisted=result.memory_persisted,
        error_category=result.error_category,
    )


def _validate_request(request: object) -> str | None:
    if not isinstance(request, IntelligenceRequest):
        return "invalid_request_type"
    if request.agent_name not in list_agents():
        return "unknown_agent"
    if not isinstance(request.user_input, str) or not request.user_input.strip():
        return "invalid_user_input"
    if not _valid_scope_id(request.consumer_id):
        return "invalid_consumer_id"
    if not _valid_scope_id(request.session_id):
        return "invalid_session_id"
    if request.persistence not in ("ephemeral", "persist"):
        return "invalid_persistence_policy"
    if request.context is not None:
        if not isinstance(request.context, IntelligenceContext):
            return "invalid_context"
        if not isinstance(request.context.content, str):
            return "invalid_context"
        if len(request.context.content) > MAX_CALLER_CONTEXT_CHARS:
            return "caller_context_too_large"
    return None


def _valid_scope_id(value: object) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value) <= MAX_SCOPE_ID_CHARS
        and _SCOPE_ID_PATTERN.fullmatch(value) is not None
    )


def _memory_scope_name(request: IntelligenceRequest) -> str:
    scope = "\0".join(
        (request.agent_name, request.consumer_id, request.session_id)
    )
    digest = hashlib.sha256(scope.encode("utf-8")).hexdigest()
    return f"intelligence_{digest}"
