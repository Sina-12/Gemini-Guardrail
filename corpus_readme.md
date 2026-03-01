This corpus has been largely obtained from https://huggingface.co/datasets/Siddish/change-my-view-subreddit-cleaned.

The extracted and formatted corpus is called corpus_raw.csv and is in the data/raw folder of our repo: https://github.ubc.ca/gillylg/argument-summaries/blob/main/data/raw/corpus_raw.csv

Alternatively, the entire code to extract and use this data has been provided in the loading_corpus.py file located in the src folder. 

The data has been obtained from the subreddit 'Change My View' from Reddit. In this subreddit, the main user provides a stance they have over an issue, and other users argue against the original stance. We have used this domain because we want to assess how well can the models summarize argumentative and persuasive text, not only in accuracy but inference. This data provides the optimal source of arguments for our purpose. 

This data has been extracted as a pandas dataframe and converted to a csv file to be saved online. The main user's arguments have been under the label of Human, and other arguments opposing the main view are under the label of Assistant. These labels precede by the symbol ### to help identify them. 

There are 1917 rows (example arguments) in this data, plus the ones that have scraped directly fro reddit and added to the corpus. In total, there are at least 1,436,145 tokens divided by whitespace. Each example contains back and forth arguments from the human and the assistant, until a 'change of view' has been achieved, or not. 