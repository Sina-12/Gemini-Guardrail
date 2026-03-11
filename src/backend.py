# Run with: uvicorn backend:app --reload



from fastapi import FastAPI
import pandas as pd
from difflib import get_close_matches

app = FastAPI()

df = pd.read_csv("../docs/0-43_Annotations.csv")

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

@app.get("/keyword-search")
def keyword_search(keyword: str, id_suffix: str = None):
    mask = df["summary"].str.contains(keyword, case=False, na=False)
    
    if id_suffix:
        mask &= df["arg_id"].str.endswith(f"_{id_suffix}")
    
    results = df[mask]

    if results.empty:
        return {"results": []}

    return {"results": results.to_dict(orient="records")}

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
