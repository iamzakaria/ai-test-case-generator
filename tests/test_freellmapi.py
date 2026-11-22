import json

import httpx
import pytest
from fastapi.testclient import TestClient

from ai_test_generator.app import create_app
from ai_test_generator.models import GenerateRequest
from ai_test_generator.providers import DemoProvider, FreeLLMAPIProvider, provider_from_env

REQUEST = {
    "requirements": [{"id": "REQ-001", "text": "Reject duplicate synthetic patient identifiers."}]
}


def test_chat_adapter_validates_traceable_output():
    suite = DemoProvider().generate(GenerateRequest.model_validate(REQUEST))

    def respond(request):
        assert str(request.url) == "http://127.0.0.1:31415/v1/chat/completions"
        body = json.loads(request.content)
        assert body["model"] == "auto"
        assert body["response_format"] == {"type": "json_object"}
        assert request.headers["Authorization"] == "Bearer synthetic-key"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"finish_reason": "stop", "message": {"content": suite.model_dump_json()}}
                ]
            },
        )

    provider = FreeLLMAPIProvider(
        "synthetic-key", "http://127.0.0.1:31415/v1", transport=httpx.MockTransport(respond)
    )
    with TestClient(create_app(provider)) as client:
        response = client.post("/api/generate", json=REQUEST)
    assert response.status_code == 200
    assert response.json()["provider"] == "freellmapi"
    assert response.json()["suite"] == suite.model_dump(mode="json")


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"choices": [None]},
        {"choices": [{"finish_reason": "length"}]},
        {"choices": [{"finish_reason": "stop", "message": {"content": "not JSON"}}]},
        {"choices": [{"finish_reason": "stop", "message": {"refusal": "refused"}}]},
    ],
)
def test_invalid_completions_return_sanitized_error(payload):
    transport = httpx.MockTransport(lambda req: httpx.Response(200, content=json.dumps(payload)))
    with TestClient(
        create_app(FreeLLMAPIProvider("fake", "http://localhost:3001/v1", transport=transport))
    ) as client:
        response = client.post("/api/generate", json=REQUEST)
    assert response.status_code == 502


@pytest.mark.parametrize(
    "url",
    [
        "http://remote.example/v1",
        "https://user:pass@example.com/v1",
        "file:///tmp",
        "https://example.com/v1?token=secret",
    ],
)
def test_unsafe_gateway_configuration_rejected(url):
    with pytest.raises(ValueError):
        FreeLLMAPIProvider("fake", url)


def test_configuration_requires_unified_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "freellmapi")
    monkeypatch.delenv("FREELLMAPI_API_KEY", raising=False)
    with pytest.raises(ValueError):
        provider_from_env()
    monkeypatch.setenv("FREELLMAPI_API_KEY", "synthetic-key")
    monkeypatch.setenv("FREELLMAPI_BASE_URL", "http://127.0.0.1:31415/v1")
    assert provider_from_env().name == "freellmapi"
