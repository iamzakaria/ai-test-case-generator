import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from ai_test_generator.models import GenerateRequest, GenerateResponse, validate_traceability
from ai_test_generator.providers import GenerationError, Provider, provider_from_env

logger = logging.getLogger(__name__)


def create_app(provider: Provider | None = None, frontend_dir: Path | None = None) -> FastAPI:
    selected = provider if provider is not None else provider_from_env()
    app = FastAPI(title="AI-Powered Test Case Generator", version="0.1.0")

    @app.get("/health")
    def health():
        return {"status": "ok", "provider": selected.name}

    @app.post("/api/generate", response_model=GenerateResponse)
    def generate(request: GenerateRequest):
        try:
            suite = validate_traceability(selected.generate(request), request)
        except (GenerationError, ValueError) as exc:
            logger.warning("Generation rejected: provider=%s", selected.name)
            raise HTTPException(
                502, "Generation failed validation; retry or review requirements"
            ) from exc
        return GenerateResponse(provider=selected.name, suite=suite)

    directory = frontend_dir or Path(os.getenv("FRONTEND_DIR", "frontend/dist"))
    if directory.is_dir():
        app.mount("/", StaticFiles(directory=directory, html=True), name="frontend")
    return app
