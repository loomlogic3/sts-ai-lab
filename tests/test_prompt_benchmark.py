from dataclasses import asdict

import pytest

from app import prompt_benchmark
from app.agent_config import list_agent_definitions
from app.command_registry import get_handler
from app.config import (
    MAX_CONVERSATION_CHARS,
    MAX_MENTOR_KNOWLEDGE_CHARS,
    MAX_PROMPT_CHARS,
    MENTOR_NUM_PREDICT,
    OLLAMA_KEEP_ALIVE,
    OLLAMA_TIMEOUT_SECONDS,
)
from app.model_execution import ModelExecutionMetrics, ModelExecutionResult
from app.prompt_builder import build_prompt_result


def mentor_definition():
    return {
        "model": "sts-fast",
        "temperature": 0.2,
        "prompt_text": "synthetic canonical-sized system prompt",
    }


@pytest.fixture
def configured_benchmark(monkeypatch):
    monkeypatch.setattr(
        prompt_benchmark,
        "load_agent_definition",
        lambda name: mentor_definition(),
    )


def test_variants_include_only_selected_canonical_components(
    configured_benchmark,
):
    variants = prompt_benchmark.build_variants()

    assert variants["A"].profile.conversation_chars == 0
    assert variants["A"].profile.knowledge_chars == 0
    assert variants["B"].profile.conversation_chars == 125
    assert variants["B"].profile.knowledge_chars == 0
    assert variants["C"].profile.conversation_chars == 0
    assert variants["C"].profile.knowledge_chars == 392
    assert variants["D"].profile.conversation_chars == 125
    assert variants["D"].profile.knowledge_chars == 392
    assert all(
        result.profile.system_prompt_chars
        == len(mentor_definition()["prompt_text"])
        for result in variants.values()
    )
    assert all(
        result.profile.user_input_chars == 26
        for result in variants.values()
    )


def test_variants_use_canonical_prompt_builder(monkeypatch):
    calls = []
    monkeypatch.setattr(
        prompt_benchmark,
        "load_agent_definition",
        lambda name: mentor_definition(),
    )

    def recording_builder(**kwargs):
        calls.append(kwargs)
        return build_prompt_result(**kwargs)

    monkeypatch.setattr(
        prompt_benchmark,
        "build_prompt_result",
        recording_builder,
    )

    prompt_benchmark.build_variants()

    assert len(calls) == 4
    assert [bool(call["conversation"]) for call in calls] == [
        False,
        True,
        False,
        True,
    ]
    assert [bool(call["knowledge"]) for call in calls] == [
        False,
        False,
        True,
        True,
    ]


def test_repeated_trials_rotate_deterministically(
    configured_benchmark,
    monkeypatch,
):
    calls = []

    def fake_execute_model(**kwargs):
        calls.append(kwargs)
        count = len(kwargs["prompt"])
        return ModelExecutionResult(
            "private model response",
            "success",
            count,
            metrics=ModelExecutionMetrics(
                total_duration_ms=count,
                prompt_eval_count=count,
                prompt_eval_duration_ms=count * 2,
                prompt_tokens_per_second=5.0,
                eval_count=7,
                eval_duration_ms=10,
                output_tokens_per_second=4.0,
                prompt_chars=count,
            ),
        )

    monkeypatch.setattr(prompt_benchmark, "execute_model", fake_execute_model)

    results, summaries = prompt_benchmark.run_benchmark(trials=2)

    assert len(calls) == 9
    assert [result.variant for result in results] == [
        "A", "B", "C", "D",
        "B", "C", "D", "A",
    ]
    assert [result.sequence_position for result in results] == [
        1, 2, 3, 4, 1, 2, 3, 4,
    ]
    assert [result.first_variant_run for result in results] == [
        True, True, True, True, False, False, False, False,
    ]
    assert len(summaries) == 4
    assert all(summary.measured_trials == 2 for summary in summaries)
    assert all(call["model"] == "sts-fast" for call in calls)
    assert all(call["temperature"] == 0.2 for call in calls)
    assert all(
        call["num_predict"] == prompt_benchmark.DEFAULT_BENCHMARK_NUM_PREDICT
        for call in calls[1:]
    )


def result(variant, trial, duration, count, rate, first):
    return prompt_benchmark.BenchmarkResult(
        variant=variant,
        trial=trial,
        sequence_position=1,
        first_variant_run=first,
        status="success",
        final_prompt_chars=100,
        prompt_eval_count=count,
        prompt_eval_duration_ms=duration,
        prompt_tokens_per_second=rate,
        eval_count=7,
        eval_duration_ms=10,
        output_tokens_per_second=4.0,
        total_duration_ms=duration + 10,
        wall_duration_ms=duration + 12,
    )


def test_aggregation_is_correct():
    results = [
        result("A", 1, 30, 10, 2.0, True),
        result("A", 2, 10, 20, 4.0, False),
        result("A", 3, 20, 30, 6.0, False),
    ]

    summary = prompt_benchmark.aggregate_results(results, ("A",))[0]

    assert summary.measured_trials == 3
    assert summary.minimum_prompt_eval_duration_ms == 10
    assert summary.maximum_prompt_eval_duration_ms == 30
    assert summary.median_prompt_eval_duration_ms == 20
    assert summary.mean_prompt_eval_duration_ms == 20
    assert summary.mean_prompt_eval_count == 20
    assert summary.mean_prompt_tokens_per_second == 4
    assert summary.first_prompt_eval_duration_ms == 30
    assert summary.repeat_mean_prompt_eval_duration_ms == 15


def test_result_metadata_contains_no_prompt_fixture_or_response(
    configured_benchmark,
    monkeypatch,
):
    monkeypatch.setattr(
        prompt_benchmark,
        "execute_model",
        lambda **kwargs: ModelExecutionResult(
            "private model response",
            "success",
            1,
            metrics=ModelExecutionMetrics(prompt_chars=len(kwargs["prompt"])),
        ),
    )

    results, summaries = prompt_benchmark.run_benchmark(
        trials=1,
        variants=("D",),
        warm_model=False,
    )

    serialized = repr({
        "results": [asdict(item) for item in results],
        "summaries": [asdict(item) for item in summaries],
    })
    assert "prompt" not in asdict(results[0])
    assert "response" not in asdict(results[0])
    assert "private model response" not in serialized
    assert prompt_benchmark.SYNTHETIC_CONVERSATION not in serialized
    assert prompt_benchmark.SYNTHETIC_KNOWLEDGE not in serialized
    assert prompt_benchmark.SYNTHETIC_QUESTION not in serialized
    assert mentor_definition()["prompt_text"] not in serialized


def test_single_variant_trials_are_supported(
    configured_benchmark,
    monkeypatch,
):
    monkeypatch.setattr(
        prompt_benchmark,
        "execute_model",
        lambda **kwargs: ModelExecutionResult("answer", "success", 1),
    )

    results, summaries = prompt_benchmark.run_benchmark(
        trials=3,
        variants=("C",),
        warm_model=False,
    )

    assert [item.variant for item in results] == ["C", "C", "C"]
    assert [item.trial for item in results] == [1, 2, 3]
    assert summaries[0].measured_trials == 3


def test_benchmark_is_not_exposed_through_product_commands():
    assert get_handler("/benchmark") is None
    assert all(
        "/benchmark" not in definition["allowed_tools"]
        for definition in list_agent_definitions()
    )


def test_production_configuration_is_unchanged():
    assert all(
        definition["model"] == "sts-fast"
        for definition in list_agent_definitions()
    )
    assert OLLAMA_TIMEOUT_SECONDS == 180
    assert OLLAMA_KEEP_ALIVE == "30m"
    assert MENTOR_NUM_PREDICT == 80
    assert MAX_CONVERSATION_CHARS == 1000
    assert MAX_MENTOR_KNOWLEDGE_CHARS == 1200
    assert MAX_PROMPT_CHARS == 12000
