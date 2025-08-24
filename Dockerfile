FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PYTHONIOENCODING=UTF-8
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["bash","-lc","exec uvicorn app.mux_main:app --host 0.0.0.0 --port 8080 --proxy-headers --forwarded-allow-ips=* --no-access-log --no-server-header --no-date-header"]
