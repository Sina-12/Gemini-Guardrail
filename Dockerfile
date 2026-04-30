FROM python:3.10-slim

WORKDIR /app

COPY data ./data
COPY src ./src

RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    pandas \
    openai \
    python-dotenv \
    torch \
    transformers \
    sentencepiece

# Allow containerized backend to reach Ollama via host.docker.internal by default.
ENV OLLAMA_BASE_URL=http://host.docker.internal:11434/v1

WORKDIR /app/src

EXPOSE 8000

CMD ["uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8000"]