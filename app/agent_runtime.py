"""
Canonical execution runtime for STS AI agents.
"""

from dataclasses import dataclass
from time import perf_counter

from app.agent_config import load_agent_definition
from app.audit_log import write_audit_record
from app.config import MAX_CONVERSATION_CHARS
from app.knowledge_search import search_knowledge
from app.memory import ConversationMemory
from app.ollama_client import is_ollama_error, run_ollama
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


def execute_agent(
    agent_name: str,
    question: str,
    memory: ConversationMemory,
    options: AgentRuntimeOptions | None = None,
) -> str:
    """
    Execute an agent through the shared local runtime.
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

        ollama_options = {
            "temperature": agent_definition["temperature"],
        }
        if options.num_predict is not None:
            ollama_options["num_predict"] = options.num_predict

        raw_answer = run_ollama(
            model,
            prompt,
            **ollama_options,
        )
        answer = clean_response(raw_answer)

        if is_ollama_error(answer):
            status = (
                "timeout"
                if answer.startswith("Ollama request timed out.")
                else "failure"
            )
            error_category = (
                "ollama_timeout"
                if status == "timeout"
                else "ollama_error"
            )
            _audit_execution(
                started_at=started_at,
                agent_name=agent_name,
                model=model,
                status=status,
                memory_persisted=False,
                error_category=error_category,
            )
            return answer

        memory.add("User", question)
        memory.add(options.memory_role or agent_name, answer)
        memory.save()

        _audit_execution(
            started_at=started_at,
            agent_name=agent_name,
            model=model,
            status="success",
            memory_persisted=True,
        )
        return answer
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
