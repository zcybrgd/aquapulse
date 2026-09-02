
from __future__ import annotations

import logging

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml_model.config import (
    CATEGORICAL_FEATURES,
    DATASET_PATH,
    NUMERICAL_FEATURES,
    RANDOM_STATE,
    TARGET,
    TEST_SIZE,
    VAL_SIZE,
)

logger = logging.getLogger("ml_model.preprocessing")


def load_dataset(path: str = DATASET_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)

    expected = set(NUMERICAL_FEATURES + CATEGORICAL_FEATURES + [TARGET])
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes dans le dataset : {missing}")

    logger.info("Dataset chargé : %d lignes, %d colonnes", df.shape[0], df.shape[1])
    logger.info("Distribution labels : %s", df[TARGET].value_counts().to_dict())
    return df


def split_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Split stratifié en 3 ensembles :
        - Train  (68%)
        - Val    (12%)
        - Test   (20%)
    """
    X = df.drop(columns=[TARGET])
    y = df[TARGET]

    # Premier split : train+val vs test
    X_trainval, X_test, y_trainval, y_test = train_test_split(
        X, y,
        test_size=TEST_SIZE,
        stratify=y,
        random_state=RANDOM_STATE,
    )

    # Deuxième split : train vs val
    X_train, X_val, y_train, y_val = train_test_split(
        X_trainval, y_trainval,
        test_size=VAL_SIZE,
        stratify=y_trainval,
        random_state=RANDOM_STATE,
    )

    logger.info("Split : train=%d, val=%d, test=%d", len(X_train), len(X_val), len(X_test))

    train_df = pd.concat([X_train, y_train], axis=1)
    val_df = pd.concat([X_val, y_val], axis=1)
    test_df = pd.concat([X_test, y_test], axis=1)

    return train_df, val_df, test_df


def build_preprocessor() -> ColumnTransformer:

    numerical_pipeline = Pipeline([
        ("scaler", StandardScaler()),
    ])

    categorical_pipeline = Pipeline([
        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numerical_pipeline, NUMERICAL_FEATURES),
            ("cat", categorical_pipeline, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )
    return preprocessor
