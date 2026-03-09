# argument-summaries
Project for COLX 523, for analysis of LLM summaries of r/ChangeMyView debates/arguments.

For sprint-specific READMEs, see docs/. 

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

- `corpus_preprocess.py` - obtains data from ConvoKit and processes it into a format ready to be fed into an LLM to summarize.
- `scraper.py` - scrapes r/ChangeMyView for the latest 100 posts and formats them like the processed ConvoKit data.
- `calculate_agreement.py` - calculates interannotater agreement across entries that have multiple annotators.
- `download_reddit_doc.py` – proof-of-concept script that downloads one Reddit comment and saves it as a corpus document.

### `data/`
Stores the raw corpus files.

- `raw/` – original downloaded text data in JSON format.  
  These files are not modified so the data collection step remains reproducible.
- `interannotations/interannotations.csv` - data that was annotated by all group members, including each annotator's scores, discernable via reviewer_id.

### `docs/`
Contains written deliverables for the project, as well as the annotated data, e.g.:

- `teamwork_contract.md` – description of team workflow, responsibilities, and communication plan  
- `project_proposal.md` – description of the corpus design and annotation plan  
- `annotation_process.md` - retrospective on the annotation process
- `plan_for_the_interface.md` - plan for the front-end interface of the project
- `docs/0-43_Annotations.csv`
- `docs/44-86_Annotations.csv`
- `docs/87-129_Annotations.csv`
- `docs/Scraped_Annotations.csv` - the various separate annotated files

### Top-level files

- `README.md` – overview of the project and instructions for running the code  
- `LICENSE` – project license