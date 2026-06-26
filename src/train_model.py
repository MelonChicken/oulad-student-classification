"""Train RandomForest models for the OULAD cutoff feature files."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

try:
    from .config import BASE_KEY, CUTOFFS, FEATURE_PATHS, PROCESSED_DIR, ROOT, TARGET_COL
    from .data_loader import require_columns
except ImportError:
    from config import BASE_KEY, CUTOFFS, FEATURE_PATHS, PROCESSED_DIR, ROOT, TARGET_COL
    from data_loader import require_columns

MODEL_DIR = ROOT / "models"
METRICS_PATH = MODEL_DIR / "metrics.json"
FEATURE_COLUMNS_PATH = MODEL_DIR / "feature_columns.json"
TEST_STUDENTS_PATH = PROCESSED_DIR / "test_students.csv"

RANDOM_STATE = 724
TEST_SIZE = 0.2

SELECTED_FEATURES = [
    "active_days_until_cutoff",
    "total_click_until_cutoff",
    "used_site_count_until_cutoff",
    "avg_click_per_active_day_until_cutoff",
    "days_since_last_activity_at_cutoff",
    "assessment_count_until_cutoff",
    "mean_score_until_cutoff",
    "avg_days_before_due_until_cutoff",
    "highest_education_encoded",
    "credits_bin",
]

CATEGORICAL_FEATURES = ["credits_bin"]
NUMERIC_FEATURES = [feature for feature in SELECTED_FEATURES if feature not in CATEGORICAL_FEATURES]


def ensure_dirs() -> None:
    """Create model and processed-data output directories."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def model_path(cutoff: str) -> Path:
    """Return the model artifact path for a cutoff name."""
    return MODEL_DIR / f"rf_{cutoff}.pkl"


def load_feature_files() -> dict[str, pd.DataFrame]:
    """Load all processed feature files and validate required columns."""
    required = BASE_KEY + [TARGET_COL] + SELECTED_FEATURES
    frames = {}
    missing_paths = [path for path in FEATURE_PATHS.values() if not path.exists()]
    if missing_paths:
        missing = ", ".join(str(path.relative_to(ROOT)) for path in missing_paths)
        raise FileNotFoundError(
            f"Missing processed feature files: {missing}. Run `python src\\build_features.py` first."
        )

    for cutoff in CUTOFFS:
        path = FEATURE_PATHS[cutoff]
        df = pd.read_csv(path)
        require_columns(df, required, path.name)
        duplicated_keys = int(df.duplicated(subset=BASE_KEY, keep=False).sum())
        if duplicated_keys:
            raise ValueError(f"{path.name} has duplicated base-key rows: {duplicated_keys}")
        target_values = set(df[TARGET_COL].dropna().astype(int).unique())
        if not target_values.issubset({0, 1}):
            raise ValueError(f"{path.name} target is not binary: {sorted(target_values)}")
        frames[cutoff] = df
        print(f"Loaded {path.relative_to(ROOT)}: rows={len(df)}, positive_rate={df[TARGET_COL].mean():.4f}")
    return frames


def build_test_student_keys(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Create one group-based held-out split shared by all cutoff models."""
    key_frames = []
    for cutoff, df in frames.items():
        keys = df[BASE_KEY + [TARGET_COL]].copy()
        keys["available_cutoff"] = cutoff
        key_frames.append(keys)

    all_keys = pd.concat(key_frames, ignore_index=True)
    split_frame = all_keys.drop_duplicates(subset=BASE_KEY).reset_index(drop=True)
    splitter = GroupShuffleSplit(n_splits=1, test_size=TEST_SIZE, random_state=RANDOM_STATE)
    _, test_index = next(
        splitter.split(
            split_frame[BASE_KEY],
            split_frame[TARGET_COL].astype(int),
            groups=split_frame["id_student"],
        )
    )
    test_student_ids = set(split_frame.iloc[test_index]["id_student"].unique())
    test_keys = all_keys.loc[all_keys["id_student"].isin(test_student_ids)].copy()
    available = (
        test_keys.groupby(BASE_KEY, as_index=False)["available_cutoff"]
        .agg(lambda values: ",".join(sorted(set(values))))
        .rename(columns={"available_cutoff": "available_cutoffs"})
    )
    labels = test_keys.drop_duplicates(subset=BASE_KEY)[BASE_KEY + [TARGET_COL]]
    result = labels.merge(available, on=BASE_KEY, how="left", validate="one_to_one")
    result.to_csv(TEST_STUDENTS_PATH, index=False)
    print(
        f"Saved held-out test keys to {TEST_STUDENTS_PATH.relative_to(ROOT)}: "
        f"rows={len(result)}, unique_students={result['id_student'].nunique()}"
    )
    return result


def build_pipeline() -> Pipeline:
    """Build the RandomForest training pipeline."""
    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", SimpleImputer(strategy="median"), NUMERIC_FEATURES),
            (
                "categorical",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="constant", fill_value="Unknown")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                    ]
                ),
                CATEGORICAL_FEATURES,
            ),
        ],
        remainder="drop",
    )
    classifier = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    return Pipeline(steps=[("preprocessor", preprocessor), ("model", classifier)])


def evaluate(y_true: pd.Series, y_prob: np.ndarray) -> dict[str, float]:
    """Compute held-out binary classification metrics."""
    y_pred = (y_prob >= 0.5).astype(int)
    metrics = {
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
    }
    metrics["roc_auc"] = (
        float(roc_auc_score(y_true, y_prob)) if y_true.nunique() == 2 else float("nan")
    )
    return metrics


def train_models(frames: dict[str, pd.DataFrame], test_keys: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Train one model per cutoff using the shared held-out student IDs."""
    test_student_ids = set(test_keys["id_student"].unique())
    all_metrics = {}

    for cutoff, df in frames.items():
        train_df = df.loc[~df["id_student"].isin(test_student_ids)].copy()
        test_df = df.loc[df["id_student"].isin(test_student_ids)].copy()
        if train_df.empty:
            raise ValueError(f"{cutoff} training set is empty after group split")
        if test_df.empty:
            raise ValueError(f"{cutoff} test set is empty after group split")

        model = build_pipeline()
        model.fit(train_df[SELECTED_FEATURES], train_df[TARGET_COL].astype(int))
        y_prob = model.predict_proba(test_df[SELECTED_FEATURES])[:, 1]
        metrics = evaluate(test_df[TARGET_COL].astype(int), y_prob)
        metrics.update(
            {
                "train_rows": int(len(train_df)),
                "test_rows": int(len(test_df)),
                "test_positive_rate": float(test_df[TARGET_COL].mean()),
            }
        )
        all_metrics[cutoff] = metrics

        path = model_path(cutoff)
        joblib.dump(model, path)
        print(
            f"Trained {cutoff}: train_rows={len(train_df)}, test_rows={len(test_df)}, "
            f"f1={metrics['f1']:.4f}, roc_auc={metrics['roc_auc']:.4f}, saved={path.relative_to(ROOT)}"
        )
    return all_metrics


def save_training_artifacts(metrics: dict[str, dict[str, float]]) -> None:
    """Save metrics and feature-column metadata as JSON."""
    METRICS_PATH.write_text(json.dumps(metrics, indent=2, allow_nan=True), encoding="utf-8")
    feature_payload = {
        "target": TARGET_COL,
        "features": SELECTED_FEATURES,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "group_column": "id_student",
        "test_size": TEST_SIZE,
        "random_state": RANDOM_STATE,
    }
    FEATURE_COLUMNS_PATH.write_text(json.dumps(feature_payload, indent=2), encoding="utf-8")
    print(f"Saved metrics to {METRICS_PATH.relative_to(ROOT)}")
    print(f"Saved feature columns to {FEATURE_COLUMNS_PATH.relative_to(ROOT)}")


def main() -> None:
    """Train and evaluate all cutoff RandomForest models."""
    ensure_dirs()
    frames = load_feature_files()
    test_keys = build_test_student_keys(frames)
    metrics = train_models(frames, test_keys)
    save_training_artifacts(metrics)
    print("\nModel training complete.")


if __name__ == "__main__":
    main()
