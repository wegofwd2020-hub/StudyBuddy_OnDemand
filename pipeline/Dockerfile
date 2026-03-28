# =============================================================================
# StudyBuddy OnDemand — Pipeline Dockerfile
# Used for running build_grade.py, build_unit.py, seed_default.py CLI tools.
# This container does NOT start a server — it is invoked by docker compose run.
# =============================================================================

FROM python:3.11-slim

WORKDIR /pipeline

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy pipeline source
COPY . .

# Content store directory (bind-mounted at runtime)
RUN mkdir -p /data/content

# Run as non-root
RUN useradd -m -u 1000 pipeline && chown -R pipeline:pipeline /pipeline /data
USER pipeline

# Default command shows available scripts — override with docker compose run
CMD ["python", "-c", "\
import os, glob; \
scripts = [os.path.basename(f) for f in glob.glob('/pipeline/*.py') if not f.endswith('config.py')]; \
print('Available pipeline scripts:'); \
[print(f'  python {s}  --help') for s in sorted(scripts)]"]
