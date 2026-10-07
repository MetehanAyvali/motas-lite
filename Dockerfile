# 1. aşama: bağımlılıkları kur
FROM python:3.14-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# 2. aşama: küçük ve güvenli çalışma imajı
FROM python:3.14-slim
RUN useradd --create-home app
WORKDIR /srv
COPY --from=builder /install /usr/local
COPY app ./app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
