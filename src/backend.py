# Run with: uvicorn backend:app --reload


from fastapi.middleware.cors import CORSMiddleware




app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


from fastapi import FastAPI
import pandas as pd
from difflib import get_close_matches

app = FastAPI()

df = pd.read_csv("../data/0-129_Annotations.csv")

@app.get("/nearest-match")
def nearest_match(query: str):
    arg_ids = df["arg_id"].astype(str).tolist()
    matches = get_close_matches(query, arg_ids, n=1, cutoff=0.1)

    if not matches:
        return {"match": None}

    matched_row = df[df["arg_id"].astype(str) == matches[0]].iloc[0]
    return matched_row.to_dict(into=dict)

# **Call it like:**


# http://127.0.0.1:8000/nearest-match?query=0_s

#on windows: http://localhost:8000/ 

@app.get("/search")
def search(q: str = "", annotated: bool = False):
    # 1. Filter by keyword in the 'summary' column
    results = df[df["summary"].str.contains(q, case=False, na=False)]

    # 2. If 'annotated' checkbox is checked, maybe filter by score > 0 
    # (Adjust this logic based on how your CSV defines 'annotated')
    if annotated:
        results = results[results["success_score"] > 0]

    # 3. Convert to dictionary
    # We rename columns on the fly to match your JS 'item.doc_id' etc.
    output = []
    for _, row in results.iterrows():
        output.append({
            "doc_id": row["arg_id"],
            "summary_text": row["summary"],
            "source_text": row.get("main_argument", "No source available"),
            "success_score": row.get("success_score", 0),
            "brevity_score": row.get("brevity_score", 0),
            "accuracy_score": row.get("accuracy_score", 0)
        })
    
    return output

# **Call it like:**

# # Just keyword
# http://127.0.0.1:8000/keyword-search?keyword=abortion
#on windows: http://localhost:8000/ 


# # Keyword + filter by _s IDs only
# http://127.0.0.1:8000/keyword-search?keyword=abortion&id_suffix=s
#on windows: http://localhost:8000/ 


# # Keyword + filter by _u IDs only
# http://127.0.0.1:8000/keyword-search?keyword=abortion&id_suffix=u
#on windows: http://localhost:8000/ 
