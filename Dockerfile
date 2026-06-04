FROM python:3.11-slim

# --- system deps (must be root) ---
    RUN apt-get update && apt-get install -y \
    git

# --- create non-root user ---
RUN useradd -u 1000 -m appuser

WORKDIR /app

# --- Python deps ---
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- copy code ---
COPY ./src/sitecheck ./sitecheck

USER appuser

ENV PATH="/home/appuser/.local/bin:${PATH}"

COPY --chmod=755 ./src/docker_entry.py /app/docker_entry.py

CMD ["python", "/app/docker_entry.py"]
