import json
import urllib.error

from app import cloud_model_client
from app.cloud_model_client import CloudModelConfig


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.data).encode("utf-8")


def cloud_config():
    return CloudModelConfig(
        provider="openai-compatible",
        api_key="private-key",
        base_url="https://example.test/v1",
    )


def test_cloud_model_client_sends_chat_completion_payload(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["headers"] = dict(request.header_items())
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": "cloud answer",
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr(
        cloud_model_client.urllib.request,
        "urlopen",
        fake_urlopen,
    )

    result = cloud_model_client.run_cloud_model_result(
        config=cloud_config(),
        model="cloud-model",
        prompt="private prompt",
        temperature=0.35,
        num_predict=44,
    )

    assert result.response == "cloud answer"
    assert captured["url"] == "https://example.test/v1/chat/completions"
    assert captured["timeout"] == cloud_model_client.CLOUD_MODEL_TIMEOUT_SECONDS
    assert captured["headers"]["Authorization"] == "Bearer private-key"
    assert captured["headers"]["User-agent"] == "sts-ai-lab/1.0"
    assert captured["payload"] == {
        "model": "cloud-model",
        "messages": [
            {
                "role": "user",
                "content": "private prompt",
            }
        ],
        "temperature": 0.35,
        "max_tokens": 44,
    }


def test_cloud_model_client_omits_max_tokens_for_google_ai_studio(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": "cloud answer",
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr(
        cloud_model_client.urllib.request,
        "urlopen",
        fake_urlopen,
    )

    config = CloudModelConfig(
        provider="google-ai-studio",
        api_key="private-key",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
    )

    cloud_model_client.run_cloud_model_result(
        config=config,
        model="gemini-3.6-flash",
        prompt="private prompt",
        temperature=0.2,
        num_predict=100,
    )

    assert "max_tokens" not in captured["payload"]


def test_cloud_model_client_accepts_full_chat_completions_url(monkeypatch):
    captured = {}
    config = CloudModelConfig(
        provider="opencode",
        api_key="private-key",
        base_url="https://example.test/v1/chat/completions",
    )

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": "answer",
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr(
        cloud_model_client.urllib.request,
        "urlopen",
        fake_urlopen,
    )

    cloud_model_client.run_cloud_model_result(
        config=config,
        model="cloud-model",
        prompt="prompt",
    )

    assert captured["url"] == "https://example.test/v1/chat/completions"


def test_cloud_model_client_redacts_http_error_details(monkeypatch):
    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(
            request.full_url,
            401,
            "private auth detail",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(
        cloud_model_client.urllib.request,
        "urlopen",
        fake_urlopen,
    )

    result = cloud_model_client.run_cloud_model_result(
        config=cloud_config(),
        model="cloud-model",
        prompt="private prompt",
    )

    assert result.response == "Cloud model request failed: HTTP 401"
    assert "private prompt" not in result.response
    assert "private-key" not in result.response


def test_cloud_model_client_invalid_shape_is_deterministic(monkeypatch):
    monkeypatch.setattr(
        cloud_model_client.urllib.request,
        "urlopen",
        lambda request, timeout: FakeResponse({"unexpected": []}),
    )

    result = cloud_model_client.run_cloud_model_result(
        config=cloud_config(),
        model="cloud-model",
        prompt="prompt",
    )

    assert result.response == "Cloud model returned an invalid response shape."
