from dataclasses import asdict

from app import agent_runtime, prompt_builder
from app.agent_runtime import AgentRuntimeOptions
from app.config import (
    MAX_CONVERSATION_CHARS,
    MAX_KNOWLEDGE_CHARS_PER_DOCUMENT,
    MAX_MENTOR_KNOWLEDGE_CHARS,
    MAX_PROMPT_CHARS,
    MENTOR_NUM_PREDICT,
    OLLAMA_KEEP_ALIVE,
    OLLAMA_TIMEOUT_SECONDS,
)
from app.model_execution import ModelExecutionMetrics, ModelExecutionResult


class FakeMemory:
    def __init__(self, context=""):
        self.context_text = context
        self.messages = []
        self.save_calls = 0

    def context(self):
        return self.context_text

    def add(self, role, content):
        self.messages.append((role, content))

    def save(self):
        self.save_calls += 1


def agent_definition():
    return {
        "model": "sts-fast",
        "temperature": 0.2,
        "description": "private agent description",
        "prompt_text": "private system prompt",
    }


def test_prompt_profile_counts_components_without_changing_prompt():
    system = " private system "
    conversation = "private conversation"
    knowledge = "private knowledge"
    question = " private user input "
    caller_context = "private caller context"
    agent_context = "private agent context\n"
    previously_composed_conversation = (
        f"{agent_context}\n{conversation}\n\n"
        f"Caller-provided context:\n{caller_context}"
    )
    expected = prompt_builder.build_prompt(
        system_prompt=system,
        conversation=previously_composed_conversation,
        user_question=question,
        knowledge=knowledge,
    )

    result = prompt_builder.build_prompt_result(
        system_prompt=system,
        conversation=conversation,
        user_question=question,
        knowledge=knowledge,
        caller_context=caller_context,
        agent_context=agent_context,
    )

    assert result.prompt == expected
    assert result.profile.system_prompt_chars == len(system.strip())
    assert result.profile.conversation_chars == len(conversation)
    assert result.profile.knowledge_chars == len(knowledge)
    assert result.profile.caller_context_chars == len(caller_context)
    assert result.profile.agent_context_chars == len(agent_context.strip())
    assert result.profile.user_input_chars == len(question.strip())
    assert result.profile.untruncated_prompt_chars == len(expected)
    assert result.profile.final_prompt_chars == len(expected)
    assert result.profile.final_prompt_truncated is False


def test_existing_prompt_builder_api_remains_string_compatible():
    kwargs = {
        "system_prompt": "system",
        "conversation": "conversation",
        "user_question": "question",
        "knowledge": "knowledge",
    }

    prompt = prompt_builder.build_prompt(**kwargs)
    structured = prompt_builder.build_prompt_result(**kwargs)

    assert isinstance(prompt, str)
    assert prompt == structured.prompt


def test_prompt_profile_reports_current_truncation(monkeypatch):
    monkeypatch.setattr(prompt_builder, "MAX_PROMPT_CHARS", 20)

    result = prompt_builder.build_prompt_result(
        system_prompt="system prompt",
        conversation="conversation",
        user_question="user question",
        knowledge="knowledge",
        conversation_truncated=True,
        knowledge_truncated=True,
    )

    assert result.profile.conversation_truncated is True
    assert result.profile.knowledge_truncated is True
    assert result.profile.final_prompt_truncated is True
    assert result.profile.untruncated_prompt_chars > 20
    assert result.profile.final_prompt_chars == len(result.prompt)
    assert result.prompt == prompt_builder.truncate_prompt(
        "system prompt\n\n"
        "Knowledge Base:\nknowledge\n\n"
        "Conversation History:\nconversation\n\n"
        "User Question:\nuser question"
    )


def test_runtime_correlates_prompt_profile_and_model_metrics(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        agent_runtime,
        "load_agent_definition",
        lambda name: agent_definition(),
    )
    monkeypatch.setattr(agent_runtime, "MAX_CONVERSATION_CHARS", 4)
    monkeypatch.setattr(
        agent_runtime,
        "search_knowledge",
        lambda question: "private knowledge",
    )

    def fake_execute_model(**kwargs):
        captured.update(kwargs)
        captured["metrics"] = ModelExecutionMetrics(
            total_duration_ms=32000,
            load_duration_ms=400,
            prompt_eval_count=300,
            prompt_eval_duration_ms=25000,
            eval_count=40,
            eval_duration_ms=6000,
            prompt_tokens_per_second=12.0,
            output_tokens_per_second=6.67,
            prompt_chars=len(kwargs["prompt"]),
        )
        return ModelExecutionResult(
            "private model response",
            "success",
            32000,
            metrics=captured["metrics"],
        )

    monkeypatch.setattr(agent_runtime, "execute_model", fake_execute_model)
    memory = FakeMemory("private conversation")

    result = agent_runtime.execute_agent_result(
        "code_agent",
        "private user input",
        memory,
        AgentRuntimeOptions(
            knowledge_chars=3,
            caller_context="private caller context",
            include_agent_config=True,
        ),
    )

    profile = result.profile.prompt_profile
    assert result.response == "private model response"
    assert result.profile.model_metrics is captured["metrics"]
    assert profile.system_prompt_chars == len("private system prompt")
    assert profile.conversation_chars == 4
    assert profile.knowledge_chars == 3
    assert profile.caller_context_chars == len("private caller context")
    assert profile.agent_context_chars > 0
    assert profile.user_input_chars == len("private user input")
    assert profile.final_prompt_chars == len(captured["prompt"])
    assert result.profile.model_metrics.prompt_chars == profile.final_prompt_chars
    assert profile.conversation_truncated is True
    assert profile.knowledge_truncated is True
    assert memory.messages == [
        ("User", "private user input"),
        ("code_agent", "private model response"),
    ]
    assert memory.save_calls == 1
    for duration in asdict(result.profile.preprocessing).values():
        assert isinstance(duration, int)
        assert duration >= 0


def test_profiling_metadata_contains_no_content(monkeypatch):
    secrets = (
        "private system prompt",
        "private conversation",
        "private knowledge",
        "private caller context",
        "private user input",
        "private model response",
    )
    monkeypatch.setattr(
        agent_runtime,
        "load_agent_definition",
        lambda name: agent_definition(),
    )
    monkeypatch.setattr(
        agent_runtime,
        "search_knowledge",
        lambda question: secrets[2],
    )
    monkeypatch.setattr(
        agent_runtime,
        "execute_model",
        lambda **kwargs: ModelExecutionResult(
            secrets[5],
            "success",
            1,
            metrics=ModelExecutionMetrics(prompt_chars=len(kwargs["prompt"])),
        ),
    )

    result = agent_runtime.execute_agent_result(
        "sts_mentor",
        secrets[4],
        FakeMemory(secrets[1]),
        AgentRuntimeOptions(
            caller_context=secrets[3],
            persist_memory=False,
        ),
    )

    serialized_profile = repr(result.profile)
    assert all(secret not in serialized_profile for secret in secrets)
    assert set(asdict(result.profile.prompt_profile)) == {
        "system_prompt_chars",
        "conversation_chars",
        "knowledge_chars",
        "caller_context_chars",
        "agent_context_chars",
        "user_input_chars",
        "untruncated_prompt_chars",
        "final_prompt_chars",
        "conversation_truncated",
        "knowledge_truncated",
        "final_prompt_truncated",
    }


def test_performance_milestone_preserves_configuration():
    assert OLLAMA_TIMEOUT_SECONDS == 180
    assert OLLAMA_KEEP_ALIVE == "30m"
    assert MENTOR_NUM_PREDICT == 80
    assert MAX_CONVERSATION_CHARS == 1000
    assert MAX_MENTOR_KNOWLEDGE_CHARS == 1200
    assert MAX_PROMPT_CHARS == 12000
    assert MAX_KNOWLEDGE_CHARS_PER_DOCUMENT == 4000
