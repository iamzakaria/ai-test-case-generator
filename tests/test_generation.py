import json

import httpx
import pytest
from fastapi.testclient import TestClient

from ai_test_generator.app import create_app
from ai_test_generator.models import GenerateRequest, validate_traceability
from ai_test_generator.providers import (
    DemoProvider,
    GenerationError,
    OpenAIProvider,
    provider_from_env,
)

PAYLOAD = {
    "requirements": [
        {"id": "REQ-REG-01", "text": "Reject duplicate synthetic patient identifiers."},
        {"id": "REQ-APT-01", "text": "Prevent conflicting clinician appointments."},
    ]
}


def test_demo_preserves_traceability(client):
    response = client.post("/api/generate", json=PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "demo-template"
    assert body["requires_review"] is True
    assert len(body["suite"]["cases"]) == 6
    assert {c["requirement_id"] for c in body["suite"]["cases"]} == {"REQ-REG-01", "REQ-APT-01"}


@pytest.mark.parametrize(
    "payload",
    [
        {"requirements": []},
        {"requirements": [{"id": "wrong", "text": "A valid long requirement"}]},
        {"requirements": [{"id": "REQ-1", "text": "short"}]},
        {"requirements": [PAYLOAD["requirements"][0]] * 2},
        {"requirements": [dict(id=f"REQ-{i}", text="A valid long requirement") for i in range(11)]},
        {"requirements": PAYLOAD["requirements"], "provider": "openai"},
    ],
)
def test_invalid_requests_rejected(client, payload):
    assert client.post("/api/generate", json=payload).status_code == 422


def test_health_identifies_provider(client):
    assert client.get("/health").json()["provider"] == "demo-template"


def test_openai_adapter_uses_structured_output():
    request = GenerateRequest.model_validate(PAYLOAD)
    expected = DemoProvider().generate(request)

    def handler(req):
        body = json.loads(req.content)
        assert body["text"]["format"]["strict"] is True
        assert body["store"] is False
        assert req.headers["authorization"] == "Bearer synthetic-test-key"
        assert body["model"] == "test-model"
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": expected.model_dump_json()}],
                    }
                ],
            },
        )

    provider = OpenAIProvider("synthetic-test-key", "test-model", httpx.MockTransport(handler))
    assert provider.generate(request) == expected


@pytest.mark.parametrize(
    "body",
    [
        {"status": "incomplete", "output": []},
        {"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal"}]}]},
        {
            "status": "completed",
            "output": [{"type": "message", "content": [{"type": "output_text", "text": "{}"}]}],
        },
    ],
)
def test_malformed_or_refused_provider_output(body):
    provider = OpenAIProvider(
        "fake", "fake", httpx.MockTransport(lambda req: httpx.Response(200, json=body))
    )
    with pytest.raises(GenerationError):
        provider.generate(GenerateRequest.model_validate(PAYLOAD))


def test_upstream_failure_is_sanitized():
    transport = httpx.MockTransport(lambda req: httpx.Response(429, text="sensitive-upstream-body"))
    with TestClient(create_app(OpenAIProvider("fake", "fake", transport))) as client:
        response = client.post("/api/generate", json=PAYLOAD)
    assert response.status_code == 502
    assert "sensitive" not in response.text


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unknown"])
def test_semantic_validation(mutation):
    request = GenerateRequest.model_validate(PAYLOAD)
    suite = DemoProvider().generate(request)
    if mutation == "missing":
        suite.cases.pop()
    elif mutation == "duplicate":
        suite.cases[1].id = suite.cases[0].id
    else:
        suite.cases[0].requirement_id = "REQ-UNKNOWN"
    with pytest.raises(ValueError):
        validate_traceability(suite, request)


def test_invalid_provider_configuration(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    with pytest.raises(ValueError):
        provider_from_env()
    monkeypatch.setenv("LLM_PROVIDER", "unknown")
    with pytest.raises(ValueError):
        provider_from_env()


@pytest.mark.parametrize(
    "body",
    [
        None,
        [],
        "unexpected",
        {"status": "completed", "output": [None]},
        {"status": "completed", "output": [{"type": "message", "content": [None]}]},
    ],
)
def test_unexpected_provider_json_shapes_are_sanitized(body):
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            200, content=json.dumps(body), headers={"content-type": "application/json"}
        )
    )
    with TestClient(
        create_app(OpenAIProvider("fake", "fake", transport)), raise_server_exceptions=False
    ) as client:
        response = client.post("/api/generate", json=PAYLOAD)
    assert response.status_code == 502
    assert response.json()["detail"] == "Generation failed validation; retry or review requirements"
