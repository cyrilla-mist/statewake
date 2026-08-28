FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY ui ./ui

ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", "uvicorn app.server:app --host 0.0.0.0 --port ${PORT:-8080}"]
