FROM python:3.11-slim

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

# Install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create content store directory
RUN mkdir -p /data/content

# Run as non-root user
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
