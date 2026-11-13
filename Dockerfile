# renovate: datasource=docker depName=ghcr.io/astral-sh/uv currentValue=0.13.8
FROM ghcr.io/astral-sh/uv@sha256:5cc1805e2426484abca4ad46ea783bab281fdb225fd82d8ce6d66a81254bac85 AS uv
# renovate: datasource=docker depName=python currentValue=3.15-slim
FROM python@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928 AS build
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
# Keep third-party installation wheel-only; the reviewed local project uses
# an editable install, with its source copied into the runtime image below.
RUN uv sync --frozen --no-dev --no-build --python /usr/local/bin/python

# renovate: datasource=docker depName=python currentValue=3.15-slim
FROM python@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928
RUN groupadd --gid 10001 climate && useradd --uid 10001 --gid climate --no-create-home climate \
    && mkdir /data && chown climate:climate /data
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY --from=build /app/src /app/src
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
USER 10001:10001
ENTRYPOINT ["inverter-climate"]
CMD ["--config", "/app/config.toml"]
