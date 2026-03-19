FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install production dependencies only
RUN uv sync --no-dev --frozen

# Copy source code and scripts
COPY src/ ./src/
COPY scripts/ ./scripts/
RUN chmod +x ./scripts/run-checkin.sh

EXPOSE 8000

CMD ["uv", "run", "python", "-m", "ai_journaling_agent.main"]
