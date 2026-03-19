FROM python:3.11-slim

WORKDIR /app

COPY data ./data
COPY src ./src

RUN pip install --no-cache-dir fastapi uvicorn pandas

WORKDIR /app/src

EXPOSE 8000

CMD ["uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8000"]