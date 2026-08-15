import json

from app import ollama_client


class FakeResponse:
    def __init__(self, data=None):
        self.data = data or {"response": "ok"}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.data).encode("utf-8")


def test_run_ollama_sends_temperature_and_num_predict(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr(ollama_client.urllib.request, "urlopen", fake_urlopen)

    result = ollama_client.run_ollama(
        "sts-fast",
        "hello",
        num_predict=77,
        temperature=0.7,
    )

    assert result == "ok"
    assert captured["timeout"] == ollama_client.OLLAMA_TIMEOUT_SECONDS
    assert captured["payload"]["model"] == "sts-fast"
    assert captured["payload"]["prompt"] == "hello"
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["keep_alive"] == ollama_client.OLLAMA_KEEP_ALIVE
    assert captured["payload"]["options"]["num_predict"] == 77
    assert captured["payload"]["options"]["temperature"] == 0.7


def test_structured_result_parses_ollama_timing_metadata(monkeypatch):
    response_data = {
        "response": "private response",
        "total_duration": 2_170_000_000,
        "load_duration": 400_000_000,
        "prompt_eval_count": 56,
        "prompt_eval_duration": 240_000_000,
        "eval_count": 8,
        "eval_duration": 1_520_000_000,
    }
    monkeypatch.setattr(
        ollama_client.urllib.request,
        "urlopen",
        lambda request, timeout: FakeResponse(response_data),
    )

    result = ollama_client.run_ollama_result("sts-fast", "private prompt")

    assert result.response == "private response"
    assert result.total_duration_ms == 2170
    assert result.load_duration_ms == 400
    assert result.prompt_eval_count == 56
    assert result.prompt_eval_duration_ms == 240
    assert result.eval_count == 8
    assert result.eval_duration_ms == 1520
    assert result.prompt_tokens_per_second == 233.33
    assert result.output_tokens_per_second == 5.26


def test_missing_timing_metadata_uses_deterministic_defaults(monkeypatch):
    monkeypatch.setattr(
        ollama_client.urllib.request,
        "urlopen",
        lambda request, timeout: FakeResponse(),
    )

    result = ollama_client.run_ollama_result("sts-fast", "prompt")

    assert result.total_duration_ms == 0
    assert result.load_duration_ms == 0
    assert result.prompt_eval_count == 0
    assert result.prompt_eval_duration_ms == 0
    assert result.eval_count == 0
    assert result.eval_duration_ms == 0
    assert result.prompt_tokens_per_second == 0.0
    assert result.output_tokens_per_second == 0.0


def test_malformed_timing_metadata_fails_safely(monkeypatch):
    response_data = {
        "response": "ok",
        "total_duration": "private duration",
        "load_duration": -1,
        "prompt_eval_count": 1.5,
        "prompt_eval_duration": float("nan"),
        "eval_count": True,
        "eval_duration": None,
    }
    monkeypatch.setattr(
        ollama_client.urllib.request,
        "urlopen",
        lambda request, timeout: FakeResponse(response_data),
    )

    result = ollama_client.run_ollama_result("sts-fast", "prompt")

    assert result.response == "ok"
    assert result.total_duration_ms == 0
    assert result.load_duration_ms == 0
    assert result.prompt_eval_count == 0
    assert result.prompt_eval_duration_ms == 0
    assert result.eval_count == 0
    assert result.eval_duration_ms == 0


def test_timeout_response_text_and_bound_remain_deterministic(monkeypatch):
    captured = {}

    def timed_out(request, timeout):
        captured["timeout"] = timeout
        raise TimeoutError

    monkeypatch.setattr(ollama_client.urllib.request, "urlopen", timed_out)

    result = ollama_client.run_ollama_result("sts-fast", "prompt")

    assert result.response == (
        "Ollama request timed out. Is the local model overloaded?"
    )
    assert captured["timeout"] == 180
    assert 0 < captured["timeout"] < 600


def test_get_ollama_url_default(monkeypatch):
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    monkeypatch.delenv("STS_OLLAMA_URL", raising=False)
    assert ollama_client.get_ollama_url() == "http://127.0.0.1:11434/api/generate"


def test_get_ollama_url_respects_ollama_host(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://custom-host:11435")
    assert ollama_client.get_ollama_url() == "http://custom-host:11435/api/generate"


def test_get_ollama_url_respects_sts_ollama_url_with_existing_api_path(monkeypatch):
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    monkeypatch.setenv("STS_OLLAMA_URL", "http://remote-server:11434/api/generate")
    assert ollama_client.get_ollama_url() == "http://remote-server:11434/api/generate"


def test_run_ollama_sends_to_custom_host(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://remote-host:11434")
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        return FakeResponse()

    monkeypatch.setattr(ollama_client.urllib.request, "urlopen", fake_urlopen)
    ollama_client.run_ollama("sts-fast", "hello")
    assert captured["url"] == "http://remote-host:11434/api/generate"
