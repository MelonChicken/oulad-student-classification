"""Raw OULAD CSV loading helpers with explicit schema checks."""

from __future__ import annotations

import pandas as pd

try:
    from .config import RAW_DIR
except ImportError:
    from config import RAW_DIR


REQUIRED_COLUMNS = {
    "studentInfo.csv": [
        "code_module",
        "code_presentation",
        "id_student",
        "gender",
        "region",
        "highest_education",
        "imd_band",
        "age_band",
        "num_of_prev_attempts",
        "studied_credits",
        "disability",
        "final_result",
    ],
    "studentRegistration.csv": [
        "code_module",
        "code_presentation",
        "id_student",
        "date_unregistration",
    ],
    "studentVle.csv": [
        "code_module",
        "code_presentation",
        "id_student",
        "id_site",
        "date",
        "sum_click",
    ],
    "studentAssessment.csv": [
        "id_assessment",
        "id_student",
        "date_submitted",
        "score",
    ],
    "assessments.csv": [
        "code_module",
        "code_presentation",
        "id_assessment",
        "assessment_type",
        "date",
        "weight",
    ],
}


def require_columns(df: pd.DataFrame, columns: list[str], name: str) -> None:
    """Raise a clear error when an expected raw or processed column is absent."""
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"{name} is missing required columns: {missing}")


def read_csv_checked(filename: str) -> pd.DataFrame:
    """Read one OULAD CSV and validate its columns."""
    path = RAW_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing raw OULAD file: {path}")
    df = pd.read_csv(path, na_values="?")
    require_columns(df, REQUIRED_COLUMNS[filename], filename)
    print(f"Loaded {filename}: shape={df.shape}")
    return df


def load_raw_tables() -> dict[str, pd.DataFrame]:
    """Load the raw CSV files needed by the portfolio pipeline."""
    return {
        "student_info": read_csv_checked("studentInfo.csv"),
        "student_registration": read_csv_checked("studentRegistration.csv"),
        "student_vle": read_csv_checked("studentVle.csv"),
        "student_assessment": read_csv_checked("studentAssessment.csv"),
        "assessments": read_csv_checked("assessments.csv"),
    }
