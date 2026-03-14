# Run with: uvicorn backend:app --reload

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pandas as pd

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Load & enrich data ─────────────────────────────────────────────────────────
df = pd.read_csv("data/0-129_Annotations.csv", encoding="latin1")
df = df.fillna(0) 

df["thread_num"] = df["arg_id"].str.extract(r"(\d+)").astype(int)
df["variant"]    = df["arg_id"].str.extract(r"_([su])$")

# ── Serve static files ─────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/")
def serve_index():
    return FileResponse("index.html")


# ── Helper ─────────────────────────────────────────────────────────────────────


def row_to_dict(row):
    return {
        "arg_id":        str(row["arg_id"]),
        "thread_num":    int(row["thread_num"]),
        "variant":       str(row["variant"]),
        "summary":       str(row["summary"]),
        "sentiment":     int(row.get("success_score", 0)), 
        "accuracy":      int(row.get("accuracy_score", 0)),
        "brevity":       int(row.get("brevity_score", 0)),
        "reviewer_id":   "System", 
        "source_text":   str(row.get("main_argument", "No source text"))
    }

# ── GET /threads ───────────────────────────────────────────────────────────────
# Returns all threads, optionally filtered by keyword.
# Each thread object contains both its _s and _u summaries.
#
# Example: GET /threads
#          GET /threads?q=abortion
@app.get("/threads")
def get_threads(q: str = ""):
    filtered = df.copy()

    if q.strip():
        mask = filtered["summary"].str.contains(q.strip(), case=False, na=False)
        matching_threads = filtered.loc[mask, "thread_num"].unique()
        filtered = filtered[filtered["thread_num"].isin(matching_threads)]

    threads = {}
    for _, row in filtered.iterrows():
        t = int(row["thread_num"])
        if t not in threads:
            threads[t] = {"thread_num": t, "s": None, "u": None}
        threads[t][row["variant"]] = row_to_dict(row)

    return sorted(threads.values(), key=lambda x: x["thread_num"])


# ── GET /thread/{thread_num} ───────────────────────────────────────────────────
# Returns both variants for a single thread.
#
# Example: GET /thread/44
@app.get("/thread/{thread_num}")
def get_thread(thread_num: int):
    rows = df[df["thread_num"] == thread_num]
    if rows.empty:
        return {"error": "Thread not found"}
    result = {"thread_num": thread_num, "s": None, "u": None}
    for _, row in rows.iterrows():
        result[row["variant"]] = row_to_dict(row)
    return result
