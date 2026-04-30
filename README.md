## Dynamic summary workflow (Phase 1)

The Phase 1 guardrail is a stateful audit-and-rewrite loop that starts from the dataset summary and selectively repairs unsupported claims:

1. **Input**: source thread text + prepared summary.
2. **Claim decomposition**: summary is split into atomic sentence-level claims.
3. **Evidence retrieval**: top matching source sentences are found with semantic similarity.
4. **NLI screening**: DeBERTa labels each claim (`entailment` / `neutral` / `contradiction`).
5. **Judge escalation**: low-confidence or contradictory claims are sent to the local Ollama judge (`phi4-mini-reasoning`).
6. **Targeted rewrite**: only hallucinated sentences are rewritten (not the full summary) using `phi4-mini`.
7. **Re-audit + trust update**: rewritten sentences are rechecked and a trust score/status is returned.

The API returns the final summary plus audit artifacts (claim verdicts, evidence, directives, and backend metadata).

## Run locally

### 1) Clone and enter the repo

```bash
git clone <REPO_URL>
cd <REPO_NAME>
```

### 2) Install dependencies

Recommended: create the project environment from `environment.yml`.

```bash
conda env create -f environment.yml
conda activate arg_sum
```

### 3) Start Ollama and required models

This project expects a local OpenAI-compatible Ollama endpoint at `http://localhost:11434/v1`.

```bash
ollama serve
ollama pull phi4-mini
ollama pull phi4-mini-reasoning
```

### 4) Start the backend

Run from `src/`:

```bash
cd src
uvicorn backend:app --reload
```

Open: [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Guardrail API usage

### HTTP endpoint

`POST /guardrail/phase1`

Example request:

```json
{
  "source_text": "Original thread text...",
  "summary": "Prepared summary to audit...",
  "max_iters": 3,
  "min_support_ratio": 0.8
}
```

### WebSocket endpoint

`GET /ws/guardrail/phase1`

Send the same JSON payload as the HTTP endpoint to receive streaming progress events (`claim_scored`, `judge_result`, `new_sentence_rewritten`, `run_complete`, etc.).

## Run with Docker

Build:

```bash
docker build -t gemini-guardrail .
```

Run:

```bash
docker run --rm -p 8000:8000 gemini-guardrail
```

Notes:
- The docker process will take about 5 minutes to install. 
- The container defaults `OLLAMA_BASE_URL` to `http://host.docker.internal:11434/v1`.
- Ensure Ollama is running on your host and both models are pulled (`phi4-mini`, `phi4-mini-reasoning`).
- If needed, override the endpoint:

```bash
docker run --rm -p 8000:8000 -e OLLAMA_BASE_URL=http://host.docker.internal:11434/v1 gemini-guardrail
```

## Repository structure

### `src/`
- `backend.py` - FastAPI app, dataset endpoints, and guardrail endpoints.
- `guardrail_phase1.py` - dynamic summary audit/rewrite orchestrator.
- `frontend.js` - browser UI logic.
- `index.html` - UI shell served at `/`.
- `styles.css` - UI styling.

### `data/`
- corpus and annotation data used by backend endpoints.

### `docs/`
- sprint and project documentation.