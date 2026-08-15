"""Controlled, privacy-safe prompt component benchmark for STS Mentor."""

import argparse
import json
from dataclasses import asdict, dataclass
from statistics import mean, median

from app.agent_config import load_agent_definition
from app.config import MENTOR_NUM_PREDICT
from app.model_execution import execute_model
from app.prompt_builder import PromptBuildResult, build_prompt_result


VARIANT_NAMES = ("A", "B", "C", "D")
DEFAULT_BENCHMARK_NUM_PREDICT = 2


def _sized_fixture(seed: str, target_chars: int) -> str:
    repeated = (seed.strip() + " ") * ((target_chars // len(seed)) + 2)
    fixture = repeated[:target_chars]
    if fixture and fixture[-1].isspace():
        fixture = fixture[:-1] + "."
    return fixture


SYNTHETIC_CONVERSATION = _sized_fixture(
    "Synthetic prior discussion about local model latency and measurement.",
    125,
)
SYNTHETIC_KNOWLEDGE = _sized_fixture(
    "Synthetic reference material describes neutral engineering observations "
    "and repeatable bounded comparisons without private user data.",
    392,
)
SYNTHETIC_QUESTION = "Explain local model timing"  # 26 characters


@dataclass(frozen=True)
class BenchmarkResult:
    """Content-free measurements from one controlled variant invocation."""

    variant: str
    trial: int
    sequence_position: int
    first_variant_run: bool
    status: str
    final_prompt_chars: int
    prompt_eval_count: int
    prompt_eval_duration_ms: int
    prompt_tokens_per_second: float
    eval_count: int
    eval_duration_ms: int
    output_tokens_per_second: float
    total_duration_ms: int
    wall_duration_ms: int
    benchmark_num_predict: int = DEFAULT_BENCHMARK_NUM_PREDICT
    isolated_mode: bool = False


@dataclass(frozen=True)
class BenchmarkSummary:
    """Simple aggregate comparison for one prompt variant."""

    variant: str
    measured_trials: int
    minimum_prompt_eval_duration_ms: int
    maximum_prompt_eval_duration_ms: int
    median_prompt_eval_duration_ms: float
    mean_prompt_eval_duration_ms: float
    mean_prompt_eval_count: float
    mean_prompt_tokens_per_second: float
    first_prompt_eval_duration_ms: int
    repeat_mean_prompt_eval_duration_ms: float | None


def build_variants() -> dict[str, PromptBuildResult]:
    """Build the four controlled variants through the canonical builder."""

    mentor = load_agent_definition("sts_mentor")
    system_prompt = mentor["prompt_text"]
    return {
        "A": build_prompt_result(
            system_prompt=system_prompt,
            conversation="",
            knowledge="",
            user_question=SYNTHETIC_QUESTION,
        ),
        "B": build_prompt_result(
            system_prompt=system_prompt,
            conversation=SYNTHETIC_CONVERSATION,
            knowledge="",
            user_question=SYNTHETIC_QUESTION,
        ),
        "C": build_prompt_result(
            system_prompt=system_prompt,
            conversation="",
            knowledge=SYNTHETIC_KNOWLEDGE,
            user_question=SYNTHETIC_QUESTION,
        ),
        "D": build_prompt_result(
            system_prompt=system_prompt,
            conversation=SYNTHETIC_CONVERSATION,
            knowledge=SYNTHETIC_KNOWLEDGE,
            user_question=SYNTHETIC_QUESTION,
        ),
    }


def rotated_order(variants: tuple[str, ...], trial: int) -> tuple[str, ...]:
    """Return a deterministic trial rotation to expose order effects."""

    offset = (trial - 1) % len(variants)
    return variants[offset:] + variants[:offset]


def run_benchmark(
    *,
    trials: int = 3,
    variants: tuple[str, ...] = VARIANT_NAMES,
    warm_model: bool = True,
    num_predict: int = DEFAULT_BENCHMARK_NUM_PREDICT,
    isolated: bool = False,
) -> tuple[list[BenchmarkResult], list[BenchmarkSummary]]:
    """Run controlled variants and return only content-free measurements."""

    _validate_inputs(trials, variants, num_predict, isolated)
    mentor = load_agent_definition("sts_mentor")
    prompts = build_variants()

    if warm_model:
        execute_model(
            model=mentor["model"],
            prompt="ready",
            temperature=mentor["temperature"],
            num_predict=1,
        )

    results = []
    measured_variants = set()
    for trial in range(1, trials + 1):
        for sequence_position, variant in enumerate(
            rotated_order(variants, trial),
            start=1,
        ):
            prompt_result = prompts[variant]
            model_result = execute_model(
                model=mentor["model"],
                prompt=prompt_result.prompt,
                temperature=mentor["temperature"],
                num_predict=num_predict,
            )
            metrics = model_result.metrics
            results.append(
                BenchmarkResult(
                    variant=variant,
                    trial=trial,
                    sequence_position=sequence_position,
                    first_variant_run=variant not in measured_variants,
                    status=model_result.status,
                    final_prompt_chars=prompt_result.profile.final_prompt_chars,
                    prompt_eval_count=metrics.prompt_eval_count,
                    prompt_eval_duration_ms=metrics.prompt_eval_duration_ms,
                    prompt_tokens_per_second=metrics.prompt_tokens_per_second,
                    eval_count=metrics.eval_count,
                    eval_duration_ms=metrics.eval_duration_ms,
                    output_tokens_per_second=metrics.output_tokens_per_second,
                    total_duration_ms=metrics.total_duration_ms,
                    benchmark_num_predict=num_predict,
                    isolated_mode=isolated,
                    wall_duration_ms=model_result.duration_ms,
                )
            )
            measured_variants.add(variant)

    return results, aggregate_results(results, variants)


def aggregate_results(
    results: list[BenchmarkResult],
    variants: tuple[str, ...] = VARIANT_NAMES,
) -> list[BenchmarkSummary]:
    """Aggregate prompt-evaluation measurements by variant."""

    summaries = []
    for variant in variants:
        selected = [result for result in results if result.variant == variant]
        if not selected:
            continue
        durations = [result.prompt_eval_duration_ms for result in selected]
        repeated = [
            result.prompt_eval_duration_ms
            for result in selected
            if not result.first_variant_run
        ]
        first = next(result for result in selected if result.first_variant_run)
        summaries.append(
            BenchmarkSummary(
                variant=variant,
                measured_trials=len(selected),
                minimum_prompt_eval_duration_ms=min(durations),
                maximum_prompt_eval_duration_ms=max(durations),
                median_prompt_eval_duration_ms=median(durations),
                mean_prompt_eval_duration_ms=mean(durations),
                mean_prompt_eval_count=mean(
                    result.prompt_eval_count for result in selected
                ),
                mean_prompt_tokens_per_second=mean(
                    result.prompt_tokens_per_second for result in selected
                ),
                first_prompt_eval_duration_ms=first.prompt_eval_duration_ms,
                repeat_mean_prompt_eval_duration_ms=(
                    mean(repeated) if repeated else None
                ),
            )
        )
    return summaries


def _validate_inputs(
    trials: int,
    variants: tuple[str, ...],
    num_predict: int,
    isolated: bool,
) -> None:
    if num_predict < 1:
        raise ValueError("num_predict must be at least 1")
    if isolated and len(variants) != 1:
        raise ValueError("isolated mode requires exactly one variant")
    if trials < 1:
        raise ValueError("Trials must be at least one.")
    if not variants or len(set(variants)) != len(variants):
        raise ValueError("Variants must be unique and non-empty.")
    if any(variant not in VARIANT_NAMES for variant in variants):
        raise ValueError("Unknown benchmark variant.")


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the privacy-safe STS Mentor prompt benchmark.",
    )
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument(
        "--variants",
        nargs="+",
        choices=VARIANT_NAMES,
        default=list(VARIANT_NAMES),
    )
    parser.add_argument(
        "--num-predict",
        type=_positive_int,
        default=DEFAULT_BENCHMARK_NUM_PREDICT,
        help="benchmark-only output-token limit (default: 2)",
    )
    parser.add_argument(
        "--isolated",
        action="store_true",
        help="measure one selected variant without interleaving variants",
    )
    args = parser.parse_args()
    results, summaries = run_benchmark(
        trials=args.trials,
        variants=tuple(args.variants),
        num_predict=args.num_predict,
        isolated=args.isolated,
    )
    print(json.dumps(
        {
            "results": [asdict(result) for result in results],
            "summaries": [asdict(summary) for summary in summaries],
        },
        indent=2,
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
