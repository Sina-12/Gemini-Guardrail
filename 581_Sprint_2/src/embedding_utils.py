"""
Shared helper functions for the Sprint 2 transfer-learning models.

This file loads the Sprint 1 data splits, loads the pretrained GloVe vectors,
and builds dense embedding features for the source text and the summary.
The transfer models import these helpers so the embedding logic lives in one
place instead of being repeated in multiple scripts.
"""

from pathlib import Path
import re

import gensim.downloader as api
import numpy as np
import pandas as pd


SRC_DIR = Path(__file__).resolve().parent
SPRINT_DIR = SRC_DIR.parent
SPRINT1_DATA_DIR = SPRINT_DIR.parent / "581_Sprint_1" / "data"
TARGET = "accuracy"
EMBEDDING_NAME = "glove-wiki-gigaword-50"


def load_split(path):
    """
    Load one split and create the text representation used for modeling.

    @param path: Path to a split CSV file.
    @return: A pandas DataFrame with a combined text column for modeling.
    """
    df = pd.read_csv(path)
    df["source_text"] = df["source_text"].fillna("").astype(str)
    df["summary"] = df["summary"].fillna("").astype(str)
    df["model_text"] = "SOURCE: " + df["source_text"] + "\nSUMMARY: " + df["summary"]
    return df


def load_embedding_model():
    """
    Load the pretrained GloVe model used as the transferred signal.

    @param None: This function does not take any parameters.
    @return: A gensim keyed vectors model.
    """
    return api.load(EMBEDDING_NAME)


def mean_embedding(text, embedding_model):
    """
    Compute the mean embedding for one text string.

    @param text: Input text string.
    @param embedding_model: Loaded gensim embedding model.
    @return: A 1D numpy array.
    """
    tokens = re.findall(r"[A-Za-z']+", str(text).lower())
    vectors = [embedding_model[token] for token in tokens if token in embedding_model]
    if vectors:
        return np.mean(vectors, axis=0)
    return np.zeros(embedding_model.vector_size)


def build_embedding_features(df, embedding_model):
    """
    Build transferred features from separate source and summary embeddings.

    @param df: Input pandas DataFrame.
    @param embedding_model: Loaded gensim embedding model.
    @return: A 2D numpy array of dense embedding features.
    """
    # We keep source and summary embeddings separate so the model can preserve
    # some distinction between the original argument and the generated summary.
    source_vectors = np.vstack(
        [mean_embedding(text, embedding_model) for text in df["source_text"]]
    )
    summary_vectors = np.vstack(
        [mean_embedding(text, embedding_model) for text in df["summary"]]
    )
    return np.hstack([source_vectors, summary_vectors])
