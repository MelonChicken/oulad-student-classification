"""Audit generated OULAD pipeline artifacts and app-facing data."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd

try:
    from .config import BASE_KEY, FEATURE_PATHS, ROOT, TARGET_COL
except ImportError:
    from config import BASE_KEY, FEATURE_PATHS, ROOT, TARGET_COL

APP_DIR = ROOT / "data" / "app"
MODEL_DIR = ROOT / "models"
WEEKS = ["week5", "week7", "week10"]

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

DEMOGRAPHIC_FEATURES = {"gender", "region", "age_band"}
LEAKAGE_FEATURES = {"final_result", "date_unregistration", "target_at_risk", "target_withdrawn"}
METRIC_KEYS = {"precision", "recall", "f1", "roc_auc", "pr_auc", "accuracy"}


def check(condition: bool, message: str, errors: list[str]) -> None:
    """Print a pass/fail audit line and collect failures."""
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {message}")
    if not condition:
        errors.append(message)


def load_json(path: Path) -> dict:
    """Load one JSON artifact."""
    return json.loads(path.read_text(encoding="utf-8"))


def audit_required_files(errors: list[str]) -> None:
    """Check required feature, app, model, and metadata files."""
    for week, path in FEATURE_PATHS.items():
        check(path.exists(), f"processed feature file exists: {path.relative_to(ROOT)}", errors)
    for week in WEEKS:
        path = APP_DIR / f"app_features_{week}.csv"
        check(path.exists(), f"app feature file exists: {path.relative_to(ROOT)}", errors)
    for week in WEEKS:
        path = MODEL_DIR / f"rf_{week}.pkl"
        check(path.exists(), f"model file exists: {path.relative_to(ROOT)}", errors)
    check((MODEL_DIR / "metrics.json").exists(), "models/metrics.json exists", errors)
    check((MODEL_DIR / "feature_columns.json").exists(), "models/feature_columns.json exists", errors)


def audit_feature_columns(errors: list[str]) -> list[str]:
    """Validate the saved model feature list."""
    path = MODEL_DIR / "feature_columns.json"
    if not path.exists():
        return []
    payload = load_json(path)
    features = payload.get("features", [])
    check(features == SELECTED_FEATURES, "feature_columns.json contains exactly the selected 10 features", errors)
    check(not (DEMOGRAPHIC_FEATURES & set(features)), "no demographic features in feature_columns.json", errors)
    check(not (LEAKAGE_FEATURES & set(features)), "no leakage features in feature_columns.json", errors)
    return features


def audit_metrics(errors: list[str]) -> None:
    """Validate metric JSON shape."""
    path = MODEL_DIR / "metrics.json"
    if not path.exists():
        return
    metrics = load_json(path)
    for week in WEEKS:
        check(week in metrics, f"metrics contains {week}", errors)
        if week in metrics:
            check(METRIC_KEYS <= set(metrics[week]), f"{week} has required metric keys", errors)


def audit_processed_files(errors: list[str]) -> None:
    """Validate processed feature file target and key integrity."""
    for week, path in FEATURE_PATHS.items():
        if not path.exists():
            continue
        df = pd.read_csv(path)
        check(TARGET_COL in df.columns, f"{path.name} has {TARGET_COL}", errors)
        if TARGET_COL in df.columns:
            target_values = set(df[TARGET_COL].dropna().astype(int).unique())
            check(target_values <= {0, 1}, f"{path.name} target_at_risk is binary", errors)
        duplicated = int(df.duplicated(subset=BASE_KEY, keep=False).sum())
        check(duplicated == 0, f"{path.name} has no duplicated key rows", errors)


def audit_app_files(errors: list[str]) -> None:
    """Validate anonymized app-facing CSV files."""
    paths = [APP_DIR / "app_test_students.csv"] + [APP_DIR / f"app_features_{week}.csv" for week in WEEKS]
    for path in paths:
        if not path.exists():
            continue
        df = pd.read_csv(path)
        check("id_student" not in df.columns, f"{path.relative_to(ROOT)} does not expose id_student", errors)
        check("anon_id" in df.columns, f"{path.relative_to(ROOT)} contains anon_id", errors)


def audit_app_source(errors: list[str]) -> None:
    """Check that app.py does not read raw CSV files."""
    app_path = ROOT / "app.py"
    if not app_path.exists():
        check(False, "app.py exists", errors)
        return
    text = app_path.read_text(encoding="utf-8")
    forbidden_tokens = ["data/raw", "studentInfo.csv", "RAW_DIR"]
    found = [token for token in forbidden_tokens if token in text]
    check(not found, "app.py does not read raw CSV files", errors)


def probability_sanity_checks(feature_columns: list[str], errors: list[str]) -> list[str]:
    """Print prediction distribution checks for each week."""
    warnings = []
    if not feature_columns:
        errors.append("feature_columns missing; skipped probability sanity checks")
        return warnings

    for week in WEEKS:
        feature_path = APP_DIR / f"app_features_{week}.csv"
        model_path = MODEL_DIR / f"rf_{week}.pkl"
        if not feature_path.exists() or not model_path.exists():
            continue
        df = pd.read_csv(feature_path)
        model = joblib.load(model_path)
        probabilities = pd.Series(model.predict_proba(df[feature_columns])[:, 1], name="probability")
        summary = {
            "min": float(probabilities.min()),
            "mean": float(probabilities.mean()),
            "max": float(probabilities.max()),
            "std": float(probabilities.std()),
        }
        print(
            f"[PROB] {week}: min={summary['min']:.4f}, mean={summary['mean']:.4f}, "
            f"max={summary['max']:.4f}, std={summary['std']:.4f}"
        )

        by_target = probabilities.groupby(df[TARGET_COL]).mean().to_dict()
        success_mean = float(by_target.get(0, float("nan")))
        risk_mean = float(by_target.get(1, float("nan")))
        print(
            f"[PROB] {week}: mean_probability_by_target_at_risk "
            f"0={success_mean:.4f}, 1={risk_mean:.4f}"
        )

        if summary["std"] < 1e-6:
            warning = f"{week} probability std is nearly zero"
            warnings.append(warning)
            print(f"[WARN] {warning}")
        if pd.notna(success_mean) and pd.notna(risk_mean) and risk_mean < success_mean:
            warning = f"{week} at-risk mean probability is lower than success mean probability"
            warnings.append(warning)
            print(f"[WARN] {warning}")
    return warnings


def main() -> None:
    """Run all output audits."""
    errors: list[str] = []
    audit_required_files(errors)
    features = audit_feature_columns(errors)
    audit_metrics(errors)
    audit_processed_files(errors)
    audit_app_files(errors)
    audit_app_source(errors)
    warnings = probability_sanity_checks(features, errors)

    print("\nAudit summary")
    print(f"errors={len(errors)}")
    print(f"warnings={len(warnings)}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("All required audit checks passed.")


if __name__ == "__main__":
    main()
