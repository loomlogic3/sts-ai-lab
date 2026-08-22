from dataclasses import asdict
from types import SimpleNamespace

import pytest

from app import prompt_benchmark
from app.config import MENTOR_NUM_PREDICT


def _execution_result(prompt_eval_duration_ms: int = 10):
    return SimpleNamespace(
        status="success",
        duration_ms=prompt_eval_duration_ms + 2,
        metrics=SimpleNamespace(
            prompt_eval_count=20,
            prompt_eval_duration_ms=prompt_eval_duration_ms,
            prompt_tokens_per_second=2.0,
            eval_count=2,
            eval_duration_ms=1,
            output_tokens_per_second=2.0,
            total_duration_ms=prompt_eval_duration_ms + 1,
        ),
    )


def test_isolated_mode_uses_only_selected_variant_and_benchmark_limit(monkeypatch):
    calls = []

    def fake_execute_model(**kwargs):
        calls.append(kwargs)
        return _execution_result(len(calls) * 10)

    monkeypatch.setattr(
        prompt_benchmark,
        "load_agent_definition",
        lambda _name: {
            "model": "sts-fast",
            "temperature": 0.2,
            "prompt_text": "Synthetic system prompt.",
        },
    )
    monkeypatch.setattr(prompt_benchmark, "execute_model", fake_execute_model)

    results, summaries = prompt_benchmark.run_benchmark(
        trials=3,
        variants=("C",),
        num_predict=2,
        isolated=True,
    )

    assert len(calls) == 4  # one residency warm-up plus three measurements
    assert calls[0]["num_predict"] == 1
    assert [call["num_predict"] for call in calls[1:]] == [2, 2, 2]
    assert [(result.variant, result.trial) for result in results] == [
        ("C", 1),
        ("C", 2),
        ("C", 3),
    ]
    assert [result.sequence_position for result in results] == [1, 1, 1]
    assert [result.first_variant_run for result in results] == [True, False, False]
    assert all(result.benchmark_num_predict == 2 for result in results)
    assert all(result.isolated_mode for result in results)
    assert [summary.variant for summary in summaries] == ["C"]
    assert MENTOR_NUM_PREDICT == 80


def test_rotated_mode_remains_deterministic_with_small_output_limit(monkeypatch):
    monkeypatch.setattr(
        prompt_benchmark,
        "load_agent_definition",
        lambda _name: {
            "model": "sts-fast",
            "temperature": 0.2,
            "prompt_text": "Synthetic system prompt.",
        },
    )
    monkeypatch.setattr(
        prompt_benchmark,
        "execute_model",
        lambda **_kwargs: _execution_result(),
    )

    results, _ = prompt_benchmark.run_benchmark(
        trials=2,
        variants=("A", "B", "C", "D"),
        warm_model=False,
        num_predict=3,
    )

    assert [result.variant for result in results[:4]] == ["A", "B", "C", "D"]
    assert [result.variant for result in results[4:]] == ["B", "C", "D", "A"]
    assert all(result.benchmark_num_predict == 3 for result in results)
    assert not any(result.isolated_mode for result in results)


@pytest.mark.parametrize("num_predict", [0, -1])
def test_invalid_benchmark_num_predict_is_rejected(num_predict):
    with pytest.raises(ValueError, match="num_predict"):
        prompt_benchmark.run_benchmark(num_predict=num_predict)


def test_cli_num_predict_validation_rejects_nonpositive_values():
    with pytest.raises(Exception, match="at least 1"):
        prompt_benchmark._positive_int("0")


def test_isolated_mode_requires_one_variant():
    with pytest.raises(ValueError, match="exactly one variant"):
        prompt_benchmark.run_benchmark(
            variants=("A", "B"),
            isolated=True,
        )


def test_new_result_metadata_contains_no_prompt_or_response_content():
    field_names = set(asdict(
        prompt_benchmark.BenchmarkResult(
            variant="C",
            trial=1,
            sequence_position=1,
            first_variant_run=True,
            status="success",
            final_prompt_chars=844,
            prompt_eval_count=241,
            prompt_eval_duration_ms=100,
            prompt_tokens_per_second=2.41,
            eval_count=2,
            eval_duration_ms=1,
            output_tokens_per_second=2.0,
            total_duration_ms=101,
            wall_duration_ms=102,
            benchmark_num_predict=2,
            isolated_mode=True,
        )
    ))

    assert "prompt" not in field_names
    assert "response" not in field_names
    assert "conversation" not in field_names
    assert "knowledge" not in field_names
    assert "user_input" not in field_names
