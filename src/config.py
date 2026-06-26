"""Configuration for the raw OULAD feature pipeline."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

BASE_KEY = ["code_module", "code_presentation", "id_student"]
TARGET_COL = "target_at_risk"

CUTOFFS = {
    "week5": {"week": 5, "day": 35, "filename": "features_week5.csv"},
    "week7": {"week": 7, "day": 49, "filename": "features_week7.csv"},
    "week10": {"week": 10, "day": 70, "filename": "features_week10.csv"},
}

LEAKAGE_COLUMNS = {
    "final_result",
    "date_unregistration",
    "target_at_risk",
    "target_withdrawn",
}

FEATURE_PATHS = {
    cutoff: PROCESSED_DIR / config["filename"]
    for cutoff, config in CUTOFFS.items()
}

OUTPUT_COLUMNS = BASE_KEY + [
    TARGET_COL,
    "active_days_until_cutoff",
    "total_click_until_cutoff",
    "used_site_count_until_cutoff",
    "avg_click_per_active_day_until_cutoff",
    "days_since_last_activity_at_cutoff",
    "assessment_count_until_cutoff",
    "mean_score_until_cutoff",
    "mean_score_until_cutoff_missing",
    "avg_days_before_due_until_cutoff",
    "avg_days_before_due_until_cutoff_missing",
    "on_time_submission_count_until_cutoff",
    "on_time_submission_count_until_cutoff_missing",
    "highest_education_encoded",
    "num_of_prev_attempts",
    "credits_bin",
]


def ensure_project_dirs() -> None:
    """Create output folders for derived feature files."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
