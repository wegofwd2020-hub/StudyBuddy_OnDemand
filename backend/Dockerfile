# Stage 1: system deps + Python packages (cached unless requirements.txt changes)
FROM python:3.11-slim AS deps
WORKDIR /app

# System dependencies (git for the wegofwd-llm git+ pip dep; libpq/gcc for asyncpg;
# glib/pango/cairo for WeasyPrint PDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libpq-dev \
    gcc \
    libglib2.0-0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: application runner — always rebuilt by CI via no-cache-filters: runner
# so BUILD_ID is never served from a stale GHA mode=max manifest (#583).
FROM deps AS runner
WORKDIR /app

COPY . .

RUN mkdir -p /data/content

# Build identifier surfaced at GET /api/v1/health as `build`.
# Deliberately NOT APP_VERSION: .env.demo sets that to the human label "demo",
# and a compose env_file overrides an image ENV — so reusing it would leave the
# check comparing against "demo" forever.
# Must come after all COPY instructions so it is never overwritten by a cached layer.
ARG BUILD_ID="dev"
ENV BUILD_ID=$BUILD_ID

RUN useradd -m -u 1000 studybuddy && chown -R studybuddy:studybuddy /app /data
USER studybuddy

EXPOSE 8000

CMD ["gunicorn", "main:app", \
     "-w", "4", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
