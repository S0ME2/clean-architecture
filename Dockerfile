# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:0.11.28 AS uv-bin



FROM python:3.12-slim AS builder

COPY --from=uv-bin /uv /uvx /bin/

WORKDIR /build

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=0

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --locked --no-dev --no-install-project

COPY app app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --locked --no-dev --no-editable



FROM python:3.12-slim AS runner

WORKDIR /library

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/library/.venv/bin:$PATH"

RUN addgroup --system group \
    && adduser --system --ingroup group user

COPY --from=builder --chown=user:group /build/.venv /library/.venv
COPY --chown=user:group app /library/app

USER user

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8888"]