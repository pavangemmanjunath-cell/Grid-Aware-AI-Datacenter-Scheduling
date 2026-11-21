# Build context: repository root (the API reads the benchmark from data/).
#   docker build -f webapp/backend/Dockerfile -t qh2dc-api .
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    QH2DC_DATA_DIR=/srv/data
WORKDIR /srv/app

COPY webapp/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY data/ /srv/data/
COPY webapp/backend/app ./app

RUN useradd --create-home --uid 10001 qh2dc
USER qh2dc

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
