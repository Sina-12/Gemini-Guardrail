# Run in the src folder with: uvicorn backend:app --reload
# Then paste 'http://127.0.0.1:8000' in browser

import asyncio
from pathlib import Path
import queue
import time
from contextlib import asynccontextmanager

# Load project-root .env (one level above src/) before imports that read os.environ.
try:
    from dotenv import load_dotenv

    _PROJECT_ROOT = Path(__file__).resolve().parents[1]
    load_dotenv(dotenv_path=_PROJECT_ROOT / ".env", override=True)
except ImportError:
    pass

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import pandas as pd
from guardrail_phase1 import GuardrailOrchestrator, create_guardrail_orchestrator

_guardrail: GuardrailOrchestrator | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Load DeBERTa/semantic models before serving requests."""
    global _guardrail
    _guardrail = create_guardrail_orchestrator()
    yield
    _guardrail = None


app = FastAPI(lifespan=lifespan)


def get_guardrail() -> GuardrailOrchestrator:
    global _guardrail
    if _guardrail is None:
        raise RuntimeError("Guardrail not initialized. Startup lifespan did not complete.")
    return _guardrail

# Allow the front end to talk to the back end from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Paths ──────────────────────────────────────────────────────────────────────
# These paths help the app find the data file and the HTML page
BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR.parent / "data" / "full_annotations_with_source_text.csv"
INDEX_FILE = BASE_DIR / "index.html"

# ── Load & enrich data ─────────────────────────────────────────────────────────
# Load the annotation data once when the server starts
df = pd.read_csv(DATA_FILE, encoding="latin1")

# Keep arg_id as string and clean it up
df["arg_id"] = df["arg_id"].astype(str).str.strip()

# Pull out the thread number and whether it is the successful or unsuccessful branch
df["thread_num"] = pd.to_numeric(
    df["arg_id"].str.extract(r"(\d+)")[0],
    errors="coerce"
)
df["variant"] = df["arg_id"].str.extract(r"_([su])$")[0]

# Keep only rows with valid ids
df = df.dropna(subset=["thread_num", "variant"]).copy()
df["thread_num"] = df["thread_num"].astype(int)

# Fill any remaining missing values after parsing
df = df.fillna("")

# ── Serve static files ─────────────────────────────────────────────────────────
# This lets FastAPI serve the JS file and other front end files
app.mount("/static", StaticFiles(directory=str(BASE_DIR)), name="static")


@app.get("/")
def serve_index():
    """
    Return the main HTML page for the app.

    This is the page the user sees when they open the site in the browser.
    """
    return FileResponse(INDEX_FILE)


# ── Helper ─────────────────────────────────────────────────────────────────────
def safe_int(value, default=0):
    """
    Convert a value to an integer safely.

    If the value is missing or cannot be converted, return the default instead.
    This helps prevent the app from crashing on bad data.
    """
    try:
        return int(float(value))
    except Exception:
        return default


def row_to_dict(row):
    """
    Turn one dataframe row into a clean dictionary for the front end.

    This keeps the API response format consistent and makes it easier for the
    JavaScript side to display each thread and its annotations.
    """
    return {
        "arg_id": str(row["arg_id"]),
        "thread_num": int(row["thread_num"]),
        "variant": str(row["variant"]),
        "summary": str(row.get("summary", "")),
        "sentiment": safe_int(row.get("sentiment", 0), 0),
        "accuracy": safe_int(row.get("accuracy", 0), 0),
        "brevity": safe_int(row.get("brevity", 0), 0),
        "reviewer_id": str(row.get("reviewer_id", "System")),
        "source_text": str(row.get("source_text", "No source text available")),
    }


# ── GET /threads ───────────────────────────────────────────────────────────────
@app.get("/threads")
def get_threads(q: str = ""):
    """
    Return all thread pairs, with optional keyword filtering.

    If the user gives a search query, this checks both the summary text and the
    original thread text, then returns only matching thread numbers.
    """
    filtered = df.copy()

    if q.strip():
        # Search both the summary and the original source text
        summary_mask = filtered["summary"].astype(str).str.contains(q.strip(), case=False, na=False)
        text_mask = filtered["source_text"].astype(str).str.contains(q.strip(), case=False, na=False)
        matching_threads = filtered.loc[summary_mask | text_mask, "thread_num"].unique()
        filtered = filtered[filtered["thread_num"].isin(matching_threads)]

    threads = {}
    for _, row in filtered.iterrows():
        t = int(row["thread_num"])
        if t not in threads:
            # Each thread number can have one successful and one unsuccessful branch
            threads[t] = {"thread_num": t, "s": None, "u": None}
        threads[t][row["variant"]] = row_to_dict(row)

    # Return threads in numeric order
    return sorted(threads.values(), key=lambda x: x["thread_num"])


# ── GET /thread/{thread_num} ───────────────────────────────────────────────────
@app.get("/thread/{thread_num}")
def get_thread(thread_num: int):
    """
    Return one thread pair by thread number.

    This is used when the front end wants the successful and unsuccessful
    branches for one specific thread.
    """
    rows = df[df["thread_num"] == thread_num]
    if rows.empty:
        return {"error": "Thread not found"}

    result = {"thread_num": thread_num, "s": None, "u": None}
    for _, row in rows.iterrows():
        result[row["variant"]] = row_to_dict(row)

    return result


class GuardrailPhase1Request(BaseModel):
    source_text: str = Field(..., min_length=1, description="Original source text to summarize.")
    summary: str = Field(..., min_length=1, description="Precomputed summary from dataset.")
    max_iters: int = Field(3, ge=1, le=8, description="Maximum repair loop iterations.")
    min_support_ratio: float = Field(
        0.8, ge=0.4, le=1.0, description="Minimum supported-claim ratio for acceptance."
    )


@app.post("/guardrail/phase1")
def run_guardrail_phase1(payload: GuardrailPhase1Request):
    """
    Run Phase 1 dynamic guardrail loop.

    Returns iterative audit artifacts:
    - candidate summaries
    - atomic claim verdicts
    - correction directives
    - evolving trust score
    """
    try:
        result = get_guardrail().run(
            source_text=payload.source_text,
            prepared_summary=payload.summary,
            max_iters=payload.max_iters,
            min_support_ratio=payload.min_support_ratio,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Guardrail pipeline failed: {exc}") from exc
    return result


@app.websocket("/ws/guardrail/phase1")
async def run_guardrail_phase1_ws(websocket: WebSocket):
    """
    WebSocket streaming endpoint for live guardrail progress events.

    Client flow:
    1) Connect websocket
    2) Send JSON payload matching GuardrailPhase1Request
    3) Receive event packets in real-time and final result packet
    """
    await websocket.accept()
    try:
        while True:
            raw_payload = await websocket.receive_json()
            try:
                payload = GuardrailPhase1Request(**raw_payload)
            except Exception as exc:
                await websocket.send_json({"type": "error", "detail": f"Invalid payload: {exc}"})
                continue

            q: queue.Queue[dict] = queue.Queue()

            def emit(event: dict):
                q.put(event)

            def run_job():
                return get_guardrail().run_stream(
                    source_text=payload.source_text,
                    prepared_summary=payload.summary,
                    max_iters=payload.max_iters,
                    min_support_ratio=payload.min_support_ratio,
                    emit=emit,
                )

            task = asyncio.create_task(asyncio.to_thread(run_job))

            # Do not use blocking queue.get() on the event loop thread: it can delay
            # heartbeats and starve other async work. Drain with get_nowait + sleep.
            while True:
                if task.done() and q.empty():
                    break
                drained_any = False
                while True:
                    try:
                        event = q.get_nowait()
                    except queue.Empty:
                        break
                    drained_any = True
                    await websocket.send_json({"type": "event", "event": event})
                if not drained_any:
                    await websocket.send_json({"type": "heartbeat", "ts": time.time()})
                    await asyncio.sleep(0.25)

            try:
                result = await task
            except RuntimeError as exc:
                await websocket.send_json({"type": "error", "detail": str(exc)})
                continue
            except Exception as exc:
                await websocket.send_json(
                    {"type": "error", "detail": f"Guardrail pipeline failed: {exc}"}
                )
                continue

            await websocket.send_json({"type": "complete", "result": result})
    except WebSocketDisconnect:
        return