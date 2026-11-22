FROM node:22-bookworm-slim AS frontend
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.lock
COPY src src
RUN pip install --no-deps . && useradd --uid 10001 --create-home app
COPY --from=frontend /ui/dist /app/frontend/dist
USER app
ENV LLM_PROVIDER=demo
EXPOSE 8000
CMD ["uvicorn", "ai_test_generator.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
