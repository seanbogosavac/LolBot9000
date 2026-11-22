# Setup container
FROM python:3.14-slim
WORKDIR /app

# Unprivileged user the bot runs as (see docker-entrypoint.sh)
RUN useradd --system --uid 10001 --no-create-home app \
    && mkdir -p /app/data \
    && chown app:app /app/data

# Install the project and its dependencies
COPY pyproject.toml README.md ./
COPY lolbot ./lolbot
RUN pip install --no-cache-dir . && rm -rf build *.egg-info

COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

# Deployed version, passed by the deploy workflow (see .github/workflows/deploy.yml).
# Declared after the install layer so a new version doesn't invalidate the pip cache.
ARG APP_VERSION=dev
ARG APP_COMMIT=unknown
ENV APP_VERSION=$APP_VERSION APP_COMMIT=$APP_COMMIT

# The package is installed in site-packages, so don't derive the data path from its location
ENV PLAYERS_DB=/app/data/players.db

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["python", "-m", "lolbot"]
