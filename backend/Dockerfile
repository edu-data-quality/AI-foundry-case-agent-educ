# Dev container do backend FastAPI
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

ENV BACKEND_HOST=0.0.0.0 \
    BACKEND_PORT=8000

WORKDIR /app

# Dependências primeiro: cache de camadas em alterações de código
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY tests ./tests

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host ${BACKEND_HOST} --port ${BACKEND_PORT} --reload"]