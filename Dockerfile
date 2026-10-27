# renovate: datasource=docker depName=ghcr.io/astral-sh/uv currentValue=0.13.6
FROM ghcr.io/astral-sh/uv@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 AS uv
# renovate: datasource=docker depName=python currentValue=3.15-slim
FROM python@sha256:533b0b2f9b5d46fd097091cf826f27902f1d6c3bca714b6dc74551356aa97a51 AS build
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
# Keep third-party installation wheel-only; the reviewed local project uses
# an editable install, with its source copied into the runtime image below.
RUN uv sync --frozen --no-dev --no-build --python /usr/local/bin/python

# renovate: datasource=docker depName=python currentValue=3.15-slim
FROM python@sha256:533b0b2f9b5d46fd097091cf826f27902f1d6c3bca714b6dc74551356aa97a51
RUN groupadd --gid 10001 climate && useradd --uid 10001 --gid climate --no-create-home climate \
    && mkdir /data && chown climate:climate /data
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY --from=build /app/src /app/src
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
USER 10001:10001
ENTRYPOINT ["inverter-climate"]
CMD ["--config", "/app/config.toml"]
