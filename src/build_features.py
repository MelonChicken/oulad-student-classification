"""Build raw OULAD cutoff feature files.

This script creates one leakage-aware derived feature file for each early
prediction cutoff: Week 5, Week 7, and Week 10. It reads raw CSV files from
`data/raw` and never modifies raw data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

try:
    from .config import (
        BASE_KEY,
        CUTOFFS,
        FEATURE_PATHS,
        LEAKAGE_COLUMNS,
        OUTPUT_COLUMNS,
        TARGET_COL,
        ensure_project_dirs,
    )
    from .data_loader import load_raw_tables, require_columns
except ImportError:
    from config import (
        BASE_KEY,
        CUTOFFS,
        FEATURE_PATHS,
        LEAKAGE_COLUMNS,
        OUTPUT_COLUMNS,
        TARGET_COL,
        ensure_project_dirs,
    )
    from data_loader import load_raw_tables, require_columns

VLE_KEY = BASE_KEY + ["id_site", "date"]

EDUCATION_ORDER = {
    "No Formal quals": 0,
    "Lower Than A Level": 1,
    "A Level or Equivalent": 2,
    "HE Qualification": 3,
    "Post Graduate Qualification": 4,
}


def build_base(student_info: pd.DataFrame, registration: pd.DataFrame) -> pd.DataFrame:
    """Create the base student-course-presentation table and binary target."""
    base_columns = BASE_KEY + [
        "final_result",
        "highest_education",
        "num_of_prev_attempts",
        "studied_credits",
    ]
    require_columns(student_info, base_columns, "studentInfo")
    require_columns(registration, BASE_KEY + ["date_unregistration"], "studentRegistration")

    base = student_info[base_columns].copy()
    base[TARGET_COL] = np.where(
        base["final_result"].isin(["Fail", "Withdrawn"]),
        1,
        np.where(base["final_result"].isin(["Pass", "Distinction"]), 0, np.nan),
    )
    if base[TARGET_COL].isna().any():
        bad_labels = sorted(base.loc[base[TARGET_COL].isna(), "final_result"].dropna().unique())
        raise ValueError(f"Unexpected final_result values: {bad_labels}")
    base[TARGET_COL] = base[TARGET_COL].astype(int)

    registration = registration[BASE_KEY + ["date_unregistration"]].copy()
    duplicated_registration = int(registration.duplicated(subset=BASE_KEY, keep=False).sum())
    if duplicated_registration:
        raise ValueError(f"studentRegistration has duplicated base keys: {duplicated_registration}")

    base = base.merge(registration, on=BASE_KEY, how="left", validate="one_to_one")
    duplicated_base = int(base.duplicated(subset=BASE_KEY, keep=False).sum())
    if duplicated_base:
        raise ValueError(f"Base table has duplicated keys after registration merge: {duplicated_base}")
    return base


def filter_active_at_cutoff(base: pd.DataFrame, cutoff_day: int) -> pd.DataFrame:
    """Remove students unregistered on or before the cutoff."""
    active_mask = base["date_unregistration"].isna() | base["date_unregistration"].gt(cutoff_day)
    active = base.loc[active_mask].copy()
    print(
        f"Active-at-cutoff day {cutoff_day}: input_rows={len(base)}, "
        f"active_rows={len(active)}, removed_rows={len(base) - len(active)}"
    )
    return active


def aggregate_vle(student_vle: pd.DataFrame, cutoff_day: int) -> tuple[pd.DataFrame, dict[str, int]]:
    """Aggregate VLE rows up to the cutoff after mean duplicate handling."""
    require_columns(student_vle, VLE_KEY + ["sum_click"], "studentVle")
    cutoff_rows = student_vle.loc[student_vle["date"].le(cutoff_day)].copy()
    post_cutoff_rows_excluded = int(student_vle["date"].gt(cutoff_day).sum())
    duplicate_key_rows = int(cutoff_rows.duplicated(subset=VLE_KEY, keep=False).sum())

    grouped = (
        cutoff_rows.groupby(VLE_KEY, dropna=False)["sum_click"]
        .mean()
        .rename("sum_click_mean")
        .reset_index()
    )
    if grouped.empty:
        return pd.DataFrame(columns=BASE_KEY), {
            "post_cutoff_rows_excluded": post_cutoff_rows_excluded,
            "duplicate_key_rows": duplicate_key_rows,
            "max_vle_date_used": -1,
        }

    aggregated = (
        grouped.groupby(BASE_KEY, dropna=False)
        .agg(
            active_days_until_cutoff=("date", "nunique"),
            total_click_until_cutoff=("sum_click_mean", "sum"),
            used_site_count_until_cutoff=("id_site", "nunique"),
            last_activity_date_until_cutoff=("date", "max"),
        )
        .reset_index()
    )
    aggregated["avg_click_per_active_day_until_cutoff"] = np.where(
        aggregated["active_days_until_cutoff"].gt(0),
        aggregated["total_click_until_cutoff"] / aggregated["active_days_until_cutoff"],
        0,
    )
    aggregated["days_since_last_activity_at_cutoff"] = (
        cutoff_day - aggregated["last_activity_date_until_cutoff"]
    )
    max_date_used = int(grouped["date"].max()) if not grouped.empty else -1
    return aggregated.drop(columns=["last_activity_date_until_cutoff"]), {
        "post_cutoff_rows_excluded": post_cutoff_rows_excluded,
        "duplicate_key_rows": duplicate_key_rows,
        "max_vle_date_used": max_date_used,
    }


def aggregate_assessments(
    student_assessment: pd.DataFrame,
    assessments: pd.DataFrame,
    cutoff_day: int,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Aggregate assessment rows submitted up to the cutoff."""
    require_columns(
        student_assessment,
        ["id_assessment", "id_student", "date_submitted", "score"],
        "studentAssessment",
    )
    require_columns(
        assessments,
        BASE_KEY[:2] + ["id_assessment", "date", "weight"],
        "assessments",
    )

    cutoff_rows = student_assessment.loc[student_assessment["date_submitted"].le(cutoff_day)].copy()
    post_cutoff_rows_excluded = int(student_assessment["date_submitted"].gt(cutoff_day).sum())
    joined = cutoff_rows.merge(
        assessments[BASE_KEY[:2] + ["id_assessment", "date", "weight"]],
        on="id_assessment",
        how="left",
        validate="many_to_one",
    )
    unmatched_rows = int(joined["code_module"].isna().sum())
    joined["days_before_due"] = joined["date"] - joined["date_submitted"]
    joined["on_time_submission"] = np.where(
        joined["date"].notna(),
        joined["date_submitted"].le(joined["date"]).astype(int),
        np.nan,
    )

    if joined.empty:
        return pd.DataFrame(columns=BASE_KEY), {
            "post_cutoff_rows_excluded": post_cutoff_rows_excluded,
            "unmatched_assessment_rows": unmatched_rows,
            "max_assessment_date_used": -1,
        }

    aggregated = (
        joined.groupby(BASE_KEY, dropna=False)
        .agg(
            assessment_count_until_cutoff=("id_assessment", "count"),
            mean_score_until_cutoff=("score", "mean"),
            avg_days_before_due_until_cutoff=("days_before_due", "mean"),
            on_time_submission_count_until_cutoff=("on_time_submission", "sum"),
        )
        .reset_index()
    )
    max_date_used = int(joined["date_submitted"].max()) if not joined.empty else -1
    return aggregated, {
        "post_cutoff_rows_excluded": post_cutoff_rows_excluded,
        "unmatched_assessment_rows": unmatched_rows,
        "max_assessment_date_used": max_date_used,
    }


def add_background_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create the requested background predictors."""
    result = df.copy()
    result["highest_education_encoded"] = (
        result["highest_education"].map(EDUCATION_ORDER).fillna(-1).astype(int)
    )
    result["credits_bin"] = pd.cut(
        result["studied_credits"],
        bins=[-np.inf, 60, 120, 180, np.inf],
        labels=["<=60", "61-120", "121-180", ">180"],
    ).astype("object")
    result["credits_bin"] = result["credits_bin"].fillna("Unknown")
    return result


def add_missing_flags_and_fill(df: pd.DataFrame) -> pd.DataFrame:
    """Add assessment missing flags, then fill numeric feature missing values with 0."""
    result = df.copy()
    assessment_columns = [
        "mean_score_until_cutoff",
        "avg_days_before_due_until_cutoff",
        "on_time_submission_count_until_cutoff",
    ]
    for column in assessment_columns:
        result[f"{column}_missing"] = result[column].isna().astype(int)

    numeric_columns = result.select_dtypes(include=[np.number]).columns.tolist()
    feature_numeric_columns = [column for column in numeric_columns if column not in BASE_KEY + [TARGET_COL]]
    result[feature_numeric_columns] = result[feature_numeric_columns].fillna(0)
    return result


def validate_output(
    df: pd.DataFrame,
    cutoff_name: str,
    cutoff_day: int,
    vle_evidence: dict[str, int],
    assessment_evidence: dict[str, int],
) -> None:
    """Run required validation checks before saving a cutoff feature file."""
    duplicated_keys = int(df.duplicated(subset=BASE_KEY, keep=False).sum())
    if duplicated_keys:
        raise ValueError(f"{cutoff_name} has duplicated base-key rows: {duplicated_keys}")

    target_values = set(df[TARGET_COL].dropna().astype(int).unique())
    if not target_values.issubset({0, 1}):
        raise ValueError(f"{cutoff_name} target is not binary: {sorted(target_values)}")

    feature_columns = [column for column in df.columns if column not in BASE_KEY + [TARGET_COL]]
    leakage_in_features = sorted((set(feature_columns) & LEAKAGE_COLUMNS) - {TARGET_COL})
    if leakage_in_features:
        raise ValueError(f"{cutoff_name} feature columns contain leakage columns: {leakage_in_features}")

    post_cutoff_used = (
        vle_evidence["max_vle_date_used"] > cutoff_day
        or assessment_evidence["max_assessment_date_used"] > cutoff_day
    )
    if post_cutoff_used:
        raise ValueError(f"{cutoff_name} used records after cutoff day {cutoff_day}")

    print(
        f"Validated {cutoff_name}: rows={len(df)}, "
        f"positive_rate={df[TARGET_COL].mean():.4f}, "
        f"vle_duplicate_key_rows_before_mean={vle_evidence['duplicate_key_rows']}, "
        f"vle_future_rows_excluded={vle_evidence['post_cutoff_rows_excluded']}, "
        f"assessment_future_rows_excluded={assessment_evidence['post_cutoff_rows_excluded']}, "
        f"unmatched_assessment_rows={assessment_evidence['unmatched_assessment_rows']}"
    )


def build_features_for_cutoff(
    base: pd.DataFrame,
    student_vle: pd.DataFrame,
    student_assessment: pd.DataFrame,
    assessments: pd.DataFrame,
    cutoff_name: str,
    cutoff_day: int,
) -> pd.DataFrame:
    """Build one cutoff-specific feature frame."""
    cohort = filter_active_at_cutoff(base, cutoff_day)
    vle_features, vle_evidence = aggregate_vle(student_vle, cutoff_day)
    assessment_features, assessment_evidence = aggregate_assessments(
        student_assessment,
        assessments,
        cutoff_day,
    )

    features = (
        cohort.merge(vle_features, on=BASE_KEY, how="left", validate="one_to_one")
        .merge(assessment_features, on=BASE_KEY, how="left", validate="one_to_one")
    )
    features = add_background_features(features)
    features = add_missing_flags_and_fill(features)
    features = features[OUTPUT_COLUMNS].copy()
    validate_output(features, cutoff_name, cutoff_day, vle_evidence, assessment_evidence)
    return features


def main() -> None:
    """Build and save Week 5, Week 7, and Week 10 feature CSV files."""
    ensure_project_dirs()
    tables = load_raw_tables()
    base = build_base(tables["student_info"], tables["student_registration"])

    for cutoff_name, cutoff_config in CUTOFFS.items():
        cutoff_day = int(cutoff_config["day"])
        print(f"\nBuilding {cutoff_name} features at day {cutoff_day}")
        features = build_features_for_cutoff(
            base=base,
            student_vle=tables["student_vle"],
            student_assessment=tables["student_assessment"],
            assessments=tables["assessments"],
            cutoff_name=cutoff_name,
            cutoff_day=cutoff_day,
        )
        output_path = FEATURE_PATHS[cutoff_name]
        features.to_csv(output_path, index=False)
        print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
