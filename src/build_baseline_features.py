from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "kaggle_oulad"
PROCESSED_DIR = ROOT / "data" / "processed"
REPORT_DIR = ROOT / "reports"
TABLE_DIR = REPORT_DIR / "tables"
REPORT_PATH = REPORT_DIR / "baseline_feature_report.md"
DECISION_LOG_PATH = REPORT_DIR / "decision_log.md"

BASE_KEY = ["code_module", "code_presentation", "id_student"]
VLE_KEY = ["code_module", "code_presentation", "id_student", "id_site", "date"]
CUTOFFS = {"week5": 35, "week7": 49, "week10": 70}

COUNT_FILL_COLUMNS = {
    "active_days_until_cutoff",
    "used_site_count_until_cutoff",
    "assessment_count_until_cutoff",
    "submitted_late_count_until_cutoff",
    "on_time_submission_count_until_cutoff",
    "assessment_rows_missing_due_date_until_cutoff",
    "scored_assessment_count_until_cutoff",
}

MISSING_FLAG_COLUMNS = [
    "imd_band",
    "date_registration",
    "is_registered_before_start",
    "mean_score_until_cutoff",
    "min_score_until_cutoff",
    "max_score_until_cutoff",
    "weighted_score_until_cutoff",
    "scored_assessment_count_until_cutoff",
    "avg_days_before_due_until_cutoff",
    "first_activity_date_until_cutoff",
    "last_activity_date_until_cutoff",
    "days_since_last_activity_at_cutoff",
]


def ensure_dirs() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)


def clean_name(value: object) -> str:
    return (
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
    )


def load_activity_types() -> list[str]:
    vle = pd.read_csv(RAW_DIR / "vle.csv", usecols=["activity_type"])
    return sorted(clean_name(value) for value in vle["activity_type"].dropna().unique())


def build_vle_mean_features(cutoff_day: int, activity_types: list[str]) -> pd.DataFrame:
    print(f"Building VLE mean features with studentVle.date <= {cutoff_day}")
    student_vle = pd.read_csv(RAW_DIR / "studentVle.csv")
    rows_before = len(student_vle)
    cutoff_rows = student_vle[student_vle["date"] <= cutoff_day].copy()
    rows_after = len(cutoff_rows)

    grouped = (
        cutoff_rows.groupby(VLE_KEY, dropna=False)["sum_click"]
        .mean()
        .rename("sum_click_mean_strategy")
        .reset_index()
    )
    duplicate_key_rows = int(cutoff_rows.duplicated(subset=VLE_KEY, keep=False).sum())
    print(
        "VLE duplicate mean evidence: "
        f"cutoff_rows={rows_after}, future_rows_excluded={rows_before - rows_after}, "
        f"duplicate_key_rows_before_mean={duplicate_key_rows}, grouped_rows={len(grouped)}"
    )

    vle_meta = pd.read_csv(RAW_DIR / "vle.csv", usecols=["id_site", "activity_type"])
    vle_meta = vle_meta.drop_duplicates(subset=["id_site"])
    grouped = grouped.merge(vle_meta, on="id_site", how="left", validate="many_to_one")
    missing_activity_type = int(grouped["activity_type"].isna().sum())
    grouped["activity_type"] = grouped["activity_type"].fillna("unknown_activity_type").map(clean_name)
    print(f"VLE grouped rows without activity_type after id_site join: {missing_activity_type}")

    base_agg = (
        grouped.groupby(BASE_KEY, dropna=False)
        .agg(
            total_click_until_cutoff_mean_strategy=("sum_click_mean_strategy", "sum"),
            active_days_until_cutoff=("date", "nunique"),
            used_site_count_until_cutoff=("id_site", "nunique"),
            first_activity_date_until_cutoff=("date", "min"),
            last_activity_date_until_cutoff=("date", "max"),
        )
        .reset_index()
    )
    base_agg["avg_click_per_active_day_until_cutoff_mean_strategy"] = np.where(
        base_agg["active_days_until_cutoff"] > 0,
        base_agg["total_click_until_cutoff_mean_strategy"] / base_agg["active_days_until_cutoff"],
        np.nan,
    )
    base_agg["days_since_last_activity_at_cutoff"] = (
        cutoff_day - base_agg["last_activity_date_until_cutoff"]
    )

    activity = grouped.pivot_table(
        index=BASE_KEY,
        columns="activity_type",
        values="sum_click_mean_strategy",
        aggfunc="sum",
        fill_value=0,
    )
    expected_activity_columns = [
        f"clicks_activity_{activity_type}_until_cutoff_mean_strategy"
        for activity_type in activity_types
    ]
    activity.columns = [
        f"clicks_activity_{activity_type}_until_cutoff_mean_strategy"
        for activity_type in activity.columns
    ]
    activity = activity.reindex(columns=expected_activity_columns, fill_value=0).reset_index()

    result = base_agg.merge(activity, on=BASE_KEY, how="left", validate="one_to_one")
    print(f"VLE mean feature rows={len(result)}, columns={len(result.columns)}")
    return result


def build_assessment_features(cutoff_day: int) -> pd.DataFrame:
    print(f"Building assessment features with date_submitted <= {cutoff_day}")
    student_assessment = pd.read_csv(RAW_DIR / "studentAssessment.csv")
    assessments = pd.read_csv(
        RAW_DIR / "assessments.csv",
        usecols=["code_module", "code_presentation", "id_assessment", "date", "weight"],
    )
    missing_due_assessment_ids = assessments.loc[
        assessments["date"].isna(), "id_assessment"
    ].tolist()
    clean_assessments = assessments[assessments["date"].notna()].copy()
    before_missing_drop = len(student_assessment)
    student_assessment = student_assessment[
        ~student_assessment["id_assessment"].isin(missing_due_assessment_ids)
    ].copy()
    missing_due_submission_rows = before_missing_drop - len(student_assessment)

    cutoff_rows = student_assessment[student_assessment["date_submitted"] <= cutoff_day].copy()
    joined = cutoff_rows.merge(
        clean_assessments, on="id_assessment", how="left", validate="many_to_one"
    )
    unmatched_rows = int(joined["code_module"].isna().sum())
    joined["submitted_late"] = (joined["date_submitted"] > joined["date"]).astype(int)
    joined["submitted_on_time"] = (joined["date_submitted"] <= joined["date"]).astype(int)
    joined["days_before_due"] = joined["date"] - joined["date_submitted"]
    joined["weighted_score_component"] = joined["score"] * joined["weight"]
    joined["weight_for_scored_submission"] = np.where(joined["score"].notna(), joined["weight"], np.nan)

    print(
        "Assessment clean-date evidence: "
        f"missing_due_assessment_ids={len(missing_due_assessment_ids)}, "
        f"submission_rows_excluded_for_missing_due_date={missing_due_submission_rows}, "
        f"cutoff_rows={len(cutoff_rows)}, unmatched_rows={unmatched_rows}"
    )

    agg = (
        joined.groupby(BASE_KEY, dropna=False)
        .agg(
            assessment_count_until_cutoff=("id_assessment", "count"),
            mean_score_until_cutoff=("score", "mean"),
            min_score_until_cutoff=("score", "min"),
            max_score_until_cutoff=("score", "max"),
            submitted_late_count_until_cutoff=("submitted_late", "sum"),
            on_time_submission_count_until_cutoff=("submitted_on_time", "sum"),
            avg_days_before_due_until_cutoff=("days_before_due", "mean"),
            assessment_rows_missing_due_date_until_cutoff=("id_assessment", lambda _: 0),
            scored_assessment_count_until_cutoff=("score", "count"),
            weighted_score_numerator=("weighted_score_component", "sum"),
            weighted_score_denominator=("weight_for_scored_submission", "sum"),
        )
        .reset_index()
    )
    agg["weighted_score_until_cutoff"] = np.where(
        agg["weighted_score_denominator"] > 0,
        agg["weighted_score_numerator"] / agg["weighted_score_denominator"],
        np.nan,
    )
    return agg.drop(columns=["weighted_score_numerator", "weighted_score_denominator"])


def drop_existing_strategy_and_assessment_columns(df: pd.DataFrame) -> pd.DataFrame:
    strategy_columns = [
        col
        for col in df.columns
        if col.startswith("total_click_until_cutoff_")
        or col.startswith("avg_click_per_active_day_until_cutoff_")
        or (col.startswith("clicks_activity_") and col.endswith(("_sum_strategy", "_max_strategy")))
    ]
    vle_summary_columns = [
        col
        for col in [
            "active_days_until_cutoff",
            "used_site_count_until_cutoff",
            "first_activity_date_until_cutoff",
            "last_activity_date_until_cutoff",
            "days_since_last_activity_at_cutoff",
        ]
        if col in df.columns
    ]
    assessment_columns = [
        col
        for col in [
            "assessment_count_until_cutoff",
            "mean_score_until_cutoff",
            "min_score_until_cutoff",
            "max_score_until_cutoff",
            "submitted_late_count_until_cutoff",
            "assessment_rows_missing_due_date_until_cutoff",
            "scored_assessment_count_until_cutoff",
            "weighted_score_until_cutoff",
        ]
        if col in df.columns
    ]
    return df.drop(columns=strategy_columns + vle_summary_columns + assessment_columns)


def add_target(df: pd.DataFrame) -> pd.DataFrame:
    df["target_at_risk"] = df["final_result"].isin(["Withdrawn", "Fail"]).astype(int)
    df["is_retake"] = (df["num_of_prev_attempts"] > 0).astype(int)
    return df


def add_missing_flags_and_fill(df: pd.DataFrame) -> pd.DataFrame:
    for col in MISSING_FLAG_COLUMNS:
        if col not in df.columns:
            continue
        missing_col = f"{col}_missing"
        df[missing_col] = df[col].isna().astype(int)
        if pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].fillna(0)
        else:
            df[col] = df[col].fillna("Unknown")

    count_like = [
        col
        for col in df.columns
        if col in COUNT_FILL_COLUMNS
        or col.startswith("total_click_until_cutoff_")
        or col.startswith("avg_click_per_active_day_until_cutoff_")
        or col.startswith("clicks_activity_")
    ]
    for col in count_like:
        df[col] = df[col].fillna(0)
    return df


def validate_baseline(df: pd.DataFrame, cutoff_name: str, cutoff_day: int, path: Path) -> dict[str, object]:
    duplicated_base_keys = int(df.duplicated(subset=BASE_KEY, keep=False).sum())
    has_date_unregistration = "date_unregistration" in df.columns
    target_rate = float(df["target_at_risk"].mean())
    target_counts = df["target_at_risk"].value_counts(dropna=False).sort_index().to_dict()
    missing_flag_columns = [col for col in df.columns if col.endswith("_missing")]
    non_binary_flags = [
        col
        for col in missing_flag_columns
        if not set(df[col].dropna().unique()).issubset({0, 1})
    ]
    after_cutoff_violations = []
    if df["last_activity_date_until_cutoff"].gt(cutoff_day).any():
        after_cutoff_violations.append("last_activity_date_until_cutoff")
    if df["first_activity_date_until_cutoff"].gt(cutoff_day).any():
        after_cutoff_violations.append("first_activity_date_until_cutoff")
    required_final_features = [
        "on_time_submission_count_until_cutoff",
        "avg_days_before_due_until_cutoff",
        "avg_days_before_due_until_cutoff_missing",
        "is_retake",
    ]
    missing_final_features = [col for col in required_final_features if col not in df.columns]
    is_retake_binary = "is_retake" in df.columns and set(df["is_retake"].dropna().unique()).issubset({0, 1})
    is_retake_rate = float(df["is_retake"].mean()) if "is_retake" in df.columns else np.nan

    print(f"\nVALIDATION {cutoff_name} day {cutoff_day}")
    print(f"Output file: {path.relative_to(ROOT)}")
    print(f"Shape: {df.shape}")
    print(f"date_unregistration present: {has_date_unregistration}")
    print(f"Duplicated base key row count: {duplicated_base_keys}")
    print(f"target_at_risk distribution: {target_counts}, positive_rate={target_rate:.4f}")
    print(f"Missing flag columns: {len(missing_flag_columns)}")
    print(f"Non-binary missing flags: {non_binary_flags}")
    print(f"Any feature evidence after cutoff: {bool(after_cutoff_violations)} {after_cutoff_violations}")
    print(f"Missing final Stage 5 features: {missing_final_features}")
    print(f"is_retake binary: {is_retake_binary}, positive_rate={is_retake_rate:.4f}")
    print(f"Remaining missing cells: {int(df.isna().sum().sum())}")

    return {
        "cutoff": cutoff_name,
        "cutoff_day": cutoff_day,
        "path": str(path.relative_to(ROOT)),
        "rows": len(df),
        "columns": len(df.columns),
        "date_unregistration_present": has_date_unregistration,
        "duplicated_base_key_rows": duplicated_base_keys,
        "target_at_risk_positive_rate": target_rate,
        "missing_flag_columns": len(missing_flag_columns),
        "non_binary_missing_flags": ", ".join(non_binary_flags),
        "after_cutoff_feature_violations": ", ".join(after_cutoff_violations),
        "missing_final_features": ", ".join(missing_final_features),
        "is_retake_positive_rate": is_retake_rate,
        "remaining_missing_cells": int(df.isna().sum().sum()),
    }


def write_report(validation_rows: list[dict[str, object]]) -> None:
    validation_df = pd.DataFrame(validation_rows)
    lines = [
        "# Baseline Feature Report",
        "",
        "## Scope",
        "",
        "This report documents model-ready baseline feature CSV creation. No final models were trained.",
        "",
        "## Decisions Applied",
        "",
        "- `target_at_risk` is 1 for `final_result` in `{Withdrawn, Fail}` and 0 otherwise.",
        "- `target_withdrawn` is preserved for auxiliary analysis and must be excluded from predictors.",
        "- `date_unregistration` is not present in baseline outputs.",
        "- VLE key duplicates are aggregated with mean `sum_click` at `code_module`, `code_presentation`, `id_student`, `id_site`, `date` before student-level summaries.",
        "- Existing `_sum_strategy` and `_max_strategy` click columns are replaced by `_mean_strategy` columns.",
        "- Assessment summaries exclude all `studentAssessment` rows whose `id_assessment` has missing `assessments.date`.",
        "- `on_time_submission_count_until_cutoff` and `avg_days_before_due_until_cutoff` are derived from clean due-date assessment rows.",
        "- `is_retake` is derived as `num_of_prev_attempts > 0`.",
        "- Missing flags are added before filling selected numeric values with 0 and categorical values with `Unknown`.",
        "",
        "## Validation Summary",
        "",
        markdown_table(validation_df),
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REPORT_PATH.relative_to(ROOT)}")


def append_decision_log() -> None:
    entry = """
## Baseline Feature Agent

- Decision: Created `data/processed/features_week{5,7,10}_baseline.csv` from cohort feature files without modifying raw data.
- Decision: `target_at_risk = 1` when `final_result` is `Withdrawn` or `Fail`; otherwise `0`.
- Decision: `final_result`, `target_withdrawn`, `target_at_risk`, and base key columns are retained for audit/joins but must be excluded from predictor matrices.
- Decision: VLE duplicate handling uses key-level mean `sum_click` from original `studentVle.csv`; existing `_sum_strategy` and `_max_strategy` click columns are replaced by `_mean_strategy` columns.
- Decision: Assessment rows for the 11 missing-due-date `assessment_id` values are excluded before computing cutoff assessment summaries.
- Decision: Selected missing-prone fields get `{column}_missing` indicators before numeric zero fill or categorical `Unknown` fill.
- Decision: `date_unregistration` remains excluded from baseline outputs.
- Unresolved: Whether to use banked assessment metadata, VLE release-week metadata, module-presentation length, grouped activity dimensions, or alternate score imputations remains deferred until after first baseline review.
"""
    current = DECISION_LOG_PATH.read_text(encoding="utf-8") if DECISION_LOG_PATH.exists() else "# Decision Log\n"
    if "## Baseline Feature Agent" not in current:
        DECISION_LOG_PATH.write_text(current.rstrip() + "\n" + entry, encoding="utf-8")
        print(f"Updated {DECISION_LOG_PATH.relative_to(ROOT)}")


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    string_df = df.copy()
    for column in string_df.columns:
        string_df[column] = string_df[column].map(format_markdown_cell)
    headers = [str(column) for column in string_df.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in string_df.values.tolist():
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def format_markdown_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def main() -> None:
    ensure_dirs()
    append_decision_log()
    activity_types = load_activity_types()
    validation_rows = []

    for cutoff_name, cutoff_day in CUTOFFS.items():
        print(f"\nBuilding baseline for {cutoff_name}")
        cohort_path = PROCESSED_DIR / f"features_{cutoff_name}_cohort.csv"
        output_path = PROCESSED_DIR / f"features_{cutoff_name}_baseline.csv"

        cohort = pd.read_csv(cohort_path)
        print(f"Loaded {cohort_path.relative_to(ROOT)} shape={cohort.shape}")
        if cohort.duplicated(subset=BASE_KEY, keep=False).any():
            raise ValueError(f"{cohort_path.name} has duplicated base keys before baseline build")

        vle_features = build_vle_mean_features(cutoff_day, activity_types)
        assessment_features = build_assessment_features(cutoff_day)

        baseline = drop_existing_strategy_and_assessment_columns(cohort)
        baseline = baseline.merge(vle_features, on=BASE_KEY, how="left", validate="one_to_one")
        baseline = baseline.merge(assessment_features, on=BASE_KEY, how="left", validate="one_to_one")
        baseline = add_target(baseline)
        baseline = add_missing_flags_and_fill(baseline)

        baseline.to_csv(output_path, index=False)
        print(f"Wrote {output_path.relative_to(ROOT)}")
        validation_rows.append(validate_baseline(baseline, cutoff_name, cutoff_day, output_path))

    write_report(validation_rows)
    print("\nBaseline feature build complete. No final models were trained.")


if __name__ == "__main__":
    main()
