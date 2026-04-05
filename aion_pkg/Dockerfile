FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir fastapi uvicorn aiosqlite slowapi psycopg2-binary redis

RUN mkdir -p storage

EXPOSE 8000

CMD ["uvicorn", "aion.api:app", "--host", "0.0.0.0", "--port", "8000"]