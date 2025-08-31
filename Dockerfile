# ────────────────────────────────────────────────────────────────
# Dockerfile · IELTS Bot v2
# ---------------------------------------------------------------
# • Base: Python 3.12-slim (Debian bookworm)
# • Extra libs: ffmpeg  ▸  audio ↔ MP3 conversion
#                build-essential, libpq-dev  ▸  compile asyncpg
# • Smart layer caching: copy + install requirements first,
#   then copy source → fastest rebuilds during dev.
# • Entrypoint: python main.py   (long-polling dispatcher)
# ────────────────────────────────────────────────────────────────

FROM python:3.12-slim AS runtime

# ---- system deps ------------------------------------------------
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        build-essential \
        libpq-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ---- python deps (cached layer) --------------------------------
WORKDIR /bot
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt

# ---- project source -------------------------------------------
COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]

# Auto-added: serve minimal ASGI so Fly proxy reaches the app
CMD ["uvicorn", "__guard_only:app", "--host", "0.0.0.0", "--port", ""]


COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]


