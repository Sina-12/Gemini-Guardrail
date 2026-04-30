"""
Shared helper functions for the Sprint 3 multi-task models.

This file loads the Sprint 1 splits, loads the pretrained GloVe vectors, and
builds the dense embedding features used by both Sprint 3 models. It also
contains a few small helper functions for building and splitting the joint labels 
used in the multi-task model.


"""

from pathlib import Path
import re

import gensim.downloader as api
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder


SRC_DIR = Path(__file__).resolve().parent
SPRINT_DIR = SRC_DIR.parent
SPRINT1_DATA_DIR = SPRINT_DIR.parent / "581_Sprint_1" / "data"
PRIMARY_TARGET = "accuracy"
AUX_TARGET = "brevity"
EMBEDDING_NAME = "glove-wiki-gigaword-50"


def load_split(path):
    """
    Load one split and create the text representation used for modeling.

    @param path: Path to a split CSV file.
    @return: A pandas DataFrame with cleaned text columns and a combined input.
    """
    df = pd.read_csv(path)
    df["source_text"] = df["source_text"].fillna("").astype(str)
    df["summary"] = df["summary"].fillna("").astype(str)
    df["model_text"] = "SOURCE: " + df["source_text"] + "\nSUMMARY: " + df["summary"]

    return df


def load_embedding_model():
    """
    Load the pretrained GloVe model used as the transferred signal.

    @param None
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
    source_vectors = np.vstack(
        [mean_embedding(text, embedding_model) for text in df["source_text"]]
    )
    summary_vectors = np.vstack(
        [mean_embedding(text, embedding_model) for text in df["summary"]]
    )
    return np.hstack([source_vectors, summary_vectors])


def build_joint_labels(df):
    """
    Create joint labels for the multi-task objective.

    @param df: Input pandas DataFrame with primary and auxiliary labels.
    @return: A pandas Series of joint label strings.
    """
    return (
        "acc_"
        + df[PRIMARY_TARGET].astype(str)
        + "__brev_"
        + df[AUX_TARGET].astype(str)
    )


def unpack_joint_predictions(joint_predictions):
    """
    Split joint prediction strings back into primary and auxiliary labels.

    @param joint_predictions: Iterable of joint label strings.
    @return: Tuple of numpy arrays (pred_accuracy, pred_brevity).
    """
    pred_accuracy = []
    pred_brevity = []

    for label in joint_predictions:
        acc_part, brev_part = str(label).split("__")
        pred_accuracy.append(int(acc_part.replace("acc_", "")))
        pred_brevity.append(int(brev_part.replace("brev_", "")))

    return np.array(pred_accuracy), np.array(pred_brevity)


def fit_joint_label_encoder(joint_labels):
    """
    Fit a label encoder for joint class strings.

    @param joint_labels: Iterable of joint label strings.
    @return: A fitted sklearn LabelEncoder.
    """
    encoder = LabelEncoder()
    encoder.fit(joint_labels)
    return encoder


def decode_joint_predictions(encoded_predictions, encoder):
    """
    Decode integer joint class predictions back into string labels.

    @param encoded_predictions: Iterable of encoded class ids.
    @param encoder: Fitted sklearn LabelEncoder.
    @return: Numpy array of decoded joint label strings.
    """
    return encoder.inverse_transform(encoded_predictions)
