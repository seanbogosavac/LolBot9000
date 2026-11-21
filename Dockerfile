# Setup container
FROM python:3.14-slim
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Unprivileged user the bot runs as (see docker-entrypoint.sh)
RUN useradd --system --uid 10001 --no-create-home app \
    && mkdir -p /app/data \
    && chown app:app /app/data

# Copy project files
COPY . .
RUN chmod +x docker-entrypoint.sh

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["python", "main.py"]
