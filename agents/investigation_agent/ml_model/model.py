
from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.preprocessing import StandardScaler

from . import config


class AnomalyModel:
    """Isolation Forest anomaly detection model with integrated scaling.

    The model operates as a two-step pipeline:
    1. ``StandardScaler`` normalises features to zero-mean, unit-variance.
    2. ``IsolationForest`` scores each sample — more negative = more anomalous.
    """

    def __init__(
        self,
        n_estimators: int = config.N_ESTIMATORS,
        contamination: float = config.CONTAMINATION,
        random_state: int = config.RANDOM_STATE,
    ) -> None:
        self.scaler = StandardScaler()
        self.model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            max_features=config.MAX_FEATURES,
            bootstrap=config.BOOTSTRAP,
            random_state=random_state,
            n_jobs=-1,
        )
        self._is_fitted: bool = False

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------
    def train(self, X_train: np.ndarray, y_train: np.ndarray | None = None) -> None:
        """Fit the scaler and Isolation Forest on training data.
        """
        print(f"  [model] Fitting StandardScaler on {X_train.shape[0]} samples …")
        X_scaled = self.scaler.fit_transform(X_train)

        print(
            f"  [model] Training IsolationForest "
            f"(n_estimators={self.model.n_estimators}, "
            f"contamination={self.model.contamination}) …"
        )
        self.model.fit(X_scaled)
        self._is_fitted = True
        print("  [model] Training complete.")

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Return predictions: 1 = normal, -1 = anomaly.
        """
        self._check_fitted()
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)

    def score(self, X: np.ndarray) -> np.ndarray:
        """Return anomaly scores (more negative = more anomalous).

       """
        self._check_fitted()
        X_scaled = self.scaler.transform(X)
        return self.model.decision_function(X_scaled)

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------
    def evaluate(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray,
    ) -> dict:
        """Evaluate the model on a test set.
        """
        self._check_fitted()

        raw_preds = self.predict(X_test)

        # Map: IsolationForest -1 (anomaly) → 1 (leak), 1 (normal) → 0
        y_pred = (raw_preds == -1).astype(int)

        cm = confusion_matrix(y_test, y_pred)
        report = classification_report(
            y_test, y_pred,
            target_names=["Normal", "Leak"],
            zero_division=0,
        )

        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)

        return {
            "confusion_matrix": cm,
            "classification_report": report,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def save(
        self,
        model_path: Path | str | None = None,
        scaler_path: Path | str | None = None,
    ) -> None:
        """Serialize the trained model and scaler to disk.

        """
        self._check_fitted()

        model_path = Path(model_path) if model_path else config.MODEL_PATH
        scaler_path = Path(scaler_path) if scaler_path else config.SCALER_PATH

        # Ensure parent directories exist
        model_path.parent.mkdir(parents=True, exist_ok=True)
        scaler_path.parent.mkdir(parents=True, exist_ok=True)

        joblib.dump(self.model, model_path)
        joblib.dump(self.scaler, scaler_path)

        print(f"  [model] Saved model  → {model_path}")
        print(f"  [model] Saved scaler → {scaler_path}")

    def load(
        self,
        model_path: Path | str | None = None,
        scaler_path: Path | str | None = None,
    ) -> None:
        """Load a pre-trained model and scaler from disk.

  
        """
        model_path = Path(model_path) if model_path else config.MODEL_PATH
        scaler_path = Path(scaler_path) if scaler_path else config.SCALER_PATH

        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        if not scaler_path.exists():
            raise FileNotFoundError(f"Scaler file not found: {scaler_path}")

        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        self._is_fitted = True

        print(f"  [model] Loaded model  ← {model_path}")
        print(f"  [model] Loaded scaler ← {scaler_path}")

    @classmethod
    def from_pretrained(
        cls,
        model_path: Path | str | None = None,
        scaler_path: Path | str | None = None,
    ) -> "AnomalyModel":
        """Factory method: load a pre-trained model ready for inference.
        """
        instance = cls()
        instance.load(model_path, scaler_path)
        return instance

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _check_fitted(self) -> None:
        """Raise if the model hasn't been trained or loaded."""
        if not self._is_fitted:
            raise RuntimeError(
                "Model is not fitted. Call train() or load() first."
            )
