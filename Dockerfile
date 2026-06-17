FROM python:3.11-slim

# --- system deps (must be root) ---
    RUN apt-get update && apt-get install -y \
    git

# --- create non-root user ---
RUN useradd -u 1000 -m appuser

WORKDIR /app

# --- copy code ---
COPY ./src/sitecheck ./src/sitecheck

# --- Python deps ---
COPY pyproject.toml .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install .

USER appuser

ENV PATH="/home/appuser/.local/bin:${PATH}"

COPY --chmod=755 ./src/docker_entry.py /app/docker_entry.py

CMD ["python", "/app/docker_entry.py"]
