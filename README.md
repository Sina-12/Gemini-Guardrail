# argument-summaries
Project for COLX 523, for analysis of LLM summaries of Reddit debates/arguments.

## How to run the corpus collection proof of concept

### 1. Clone the repository

git clone <REPO_URL>  
cd <REPO_NAME>

### 2. Install the required package

pip install requests

### 3. Run the script

python src/download_reddit_doc.py

### 4. Expected output

After the script runs, you should see:

Downloaded one document to data/raw/reddit_comment.json

The file will be saved at:

data/raw/reddit_comment.json



## Repository structure

This repository is organized to separate source code, data, and documentation for each sprint.

### `src/`
Contains all Python scripts used for data collection and processing.

- `download_reddit_doc.py` – proof-of-concept script that downloads one Reddit comment and saves it as a corpus document.

### `data/`
Stores the corpus files.

- `raw/` – original downloaded text data in JSON format.  
  These files are not modified so the data collection step remains reproducible.

### `docs/`
Contains written deliverables for the project.

- `teamwork_contract.md` – description of team workflow, responsibilities, and communication plan  
- `project_proposal.md` – description of the corpus design and annotation plan  
- `step_by_step_algo.md` – algorithm for programmatic corpus collection  

### Top-level files

- `README.md` – overview of the project and instructions for running the code  
- `LICENSE` – project license