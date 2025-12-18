FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# Create virtual environment and install dependencies
RUN python -m venv .venv
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml ./
COPY src ./src/

RUN pip install --no-cache-dir -e . --only-binary=all

FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        curl \
        procps \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean && \
    apt-get autoremove -y

RUN groupadd -r -g 1000 app && \
    useradd -r -g app -u 1000 -d /app -s /bin/false app && \
    chown -R app:app /app && \
    chmod 755 /app && \
    chmod -R go-w /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/src /app/src
COPY --chown=app:app pyproject.toml /app/

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app" \
    PYTHONFAULTHANDLER=1

USER app

EXPOSE 8080

CMD ["/app/.venv/bin/prometheus-mcp-server"]

LABEL org.opencontainers.image.title="Prometheus JSON-RPC Server" \
      org.opencontainers.image.description="Stateless HTTP JSON-RPC server for Prometheus integration, enabling direct API access to query metrics and monitor system health" \
      org.opencontainers.image.version="1.5.1" \
      org.opencontainers.image.authors="Pavel Shklovsky <pavel@cloudefined.com>" \
      org.opencontainers.image.source="https://github.com/pab1it0/prometheus-mcp-server" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.url="https://github.com/pab1it0/prometheus-mcp-server" \
      org.opencontainers.image.documentation="https://github.com/pab1it0/prometheus-mcp-server/blob/main/docs/" \
      org.opencontainers.image.vendor="Pavel Shklovsky" \
      org.opencontainers.image.base.name="python:3.12-slim-bookworm" \
      org.opencontainers.image.created="" \
      org.opencontainers.image.revision=""
