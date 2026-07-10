import json

from app import ollama_client


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps({"response": "ok"}).encode("utf-8")


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
    assert captured["payload"]["options"]["num_predict"] == 77
    assert captured["payload"]["options"]["temperature"] == 0.7
