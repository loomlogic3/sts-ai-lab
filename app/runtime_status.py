"""Structured, content-free status events for agent execution."""

from dataclasses import dataclass
from typing import Callable, Literal


RuntimeStage = Literal[
    "loading_agent",
    "reading_memory",
    "searching_knowledge",
    "building_prompt",
    "waiting_for_model",
    "processing_response",
    "saving_memory",
    "complete",
    "timeout",
    "failure",
]


@dataclass(frozen=True)
class RuntimeStatusEvent:
    """Control metadata describing a real canonical runtime boundary."""

    stage: RuntimeStage
    agent_name: str
    model: str | None = None


RuntimeStatusCallback = Callable[[RuntimeStatusEvent], None]
