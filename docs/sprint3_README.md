# SPRINT 3 README.MD
# Sprint README

This sprint focuses on expanding our corpus, organizing our annotation data, and planning the interface for interacting with the project data.

## Scraper

The main scraper for this sprint is `src/scraper.py`. It collects Reddit discussion data from the `changemyview` subreddit and formats the extracted output so it matches the structure of our original corpus. The scraper is designed to gather successful and unsuccessful discussion branches and save them in the same general format as the rest of our dataset.

When the scraper is run, it saves its output in:

`src/output/changemyview/`

This folder contains the scraper generated corpus output for that subreddit.

We used this scraper to collect 100+ Reddit threads. The resulting entries were then added to our main corpus as additional data.

## Corpus Files

Inside the `data/` folder, there are two main corpus files:

- `corpus_preprocessed.csv`
- `corpus_preprocessed_with_scraper.csv`

`corpus_preprocessed.csv` contains the original main corpus.

`corpus_preprocessed_with_scraper.csv` contains the original corpus plus the additional entries collected by our scraper.

## Summaries, Annotations, and Interface Plan

The `data/` folder also contains the generated summaries, annotation related files, and our interface planning document:

- docs/0-43_Annotations.csv
- docs/44-86_Annotations.csv
- docs/87-129_Annotations.csv
- docs/Scraped_Annotations.csv

The interface plan describes how we intend to build a simple way for users to explore the corpus, summaries, and annotations.
- docs/plan_for_the_interface.md





## Interannotator Data

Inside:

`data/interannotations/interannotations.csv`

you can find a set of examples that were annotated by all 4 group members. This file includes each annotator’s scores, and each annotator is identified with a different `reviewer_id`.

This file is useful for comparing how different group members labeled the same examples and for examining agreement across annotations.

The results are discussed in:
docs/annotation_process.md

## Notes

Overall, this sprint adds new scraped Reddit data, integrates that data into the larger corpus, keeps track of annotations and interannotator work, and prepares for the next stage of the project by outlining the planned interface.