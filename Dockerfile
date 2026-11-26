# renovate: datasource=docker depName=ghcr.io/astral-sh/uv currentValue=0.13.10
FROM ghcr.io/astral-sh/uv@sha256:a3ea1357342c1a4bf9a0c53a3deb1b55379aefa037338d8113d5771efa01774f AS uv
# renovate: datasource=docker depName=python currentValue=3.15-slim
FROM python@sha256:63bb298d2b7b88f176f51b5189f54ce6535c997682ea70885d2132f5d473a8a5 AS build
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
# Keep third-party installation wheel-only; the reviewed local project uses
# an editable install, with its source copied into the runtime image below.
RUN uv sync --frozen --no-dev --no-build --python /usr/local/bin/python

# renovate: datasource=docker depName=python currentValue=3.15-slim
FROM python@sha256:63bb298d2b7b88f176f51b5189f54ce6535c997682ea70885d2132f5d473a8a5
RUN groupadd --gid 10001 climate && useradd --uid 10001 --gid climate --no-create-home climate \
    && mkdir /data && chown climate:climate /data
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY --from=build /app/src /app/src
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
USER 10001:10001
ENTRYPOINT ["inverter-climate"]
CMD ["--config", "/app/config.toml"]
