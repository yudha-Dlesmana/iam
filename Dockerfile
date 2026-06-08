# BUILDER
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

COPY requirements-prod.txt .
RUN pip install --prefix=/install -r requirements-prod.txt

# RUNTIME
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/usr/local/bin:$PATH"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libssl3 curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

COPY src ./src
COPY alembic ./alembic
COPY alembic.ini main.py ./
COPY scripts ./scripts

RUN groupadd --system --gid 10001 app \
     && useradd --system --uid 10001 --gid app --create-home app 

USER app

EXPOSE 9001

HEALTHCHECK --interval=60s --timeout=3s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:9001/v1/health || exit 1

CMD ["python", "main.py"]
