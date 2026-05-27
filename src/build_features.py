from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "kaggle_oulad"
PROCESSED_DIR = ROOT / "data" / "processed"
REPORT_DIR = ROOT / "reports"
REPORT_PATH = REPORT_DIR / "feature_pipeline_report.md"
DECISION_LOG_PATH = REPORT_DIR / "decision_log.md"

BASE_KEY = ["code_module", "code_presentation", "id_student"]
VLE_KEY = ["code_module", "code_presentation", "id_student", "id_site", "date"]
CUTOFFS = {
    "week5": 35,
    "week7": 49,
    "week10": 70,
}

STATIC_COLUMNS = [
    "gender",
    "region",
    "highest_education",
    "imd_band",
    "age_band",
    "num_of_prev_attempts",
    "studied_credits",
    "disability",
    "code_module",
    "code_presentation",
]


def ensure_dirs() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)


def read_raw_tables() -> dict[str, pd.DataFrame]:
    tables = {
        "student_info": pd.read_csv(DATA_DIR / "studentInfo.csv"),
        "student_registration": pd.read_csv(DATA_DIR / "studentRegistration.csv"),
        "student_vle": pd.read_csv(DATA_DIR / "studentVle.csv"),
        "vle": pd.read_csv(DATA_DIR / "vle.csv"),
        "student_assessment": pd.read_csv(DATA_DIR / "studentAssessment.csv"),
        "assessments": pd.read_csv(DATA_DIR / "assessments.csv"),
    }
    for name, df in tables.items():
        print(f"Loaded {name}: shape={df.shape}")
    return tables


def build_base(student_info: pd.DataFrame, student_registration: pd.DataFrame) -> pd.DataFrame:
    base_columns = BASE_KEY + [
        "gender",
        "region",
        "highest_education",
        "imd_band",
        "age_band",
        "num_of_prev_attempts",
        "studied_credits",
        "disability",
        "final_result",
    ]
    base = student_info[base_columns].copy()
    base["target_withdrawn"] = (base["final_result"] == "Withdrawn").astype(int)

    registration = student_registration[BASE_KEY + ["date_registration"]].copy()
    registration["is_registered_before_start"] = np.where(
        registration["date_registration"].isna(),
        np.nan,
        (registration["date_registration"] <= 0).astype(int),
    )
    base = base.merge(registration, on=BASE_KEY, how="left", validate="one_to_one")

    duplicated_keys = int(base.duplicated(subset=BASE_KEY, keep=False).sum())
    if duplicated_keys:
        raise ValueError(f"Base table has duplicated keys after registration merge: {duplicated_keys}")
    return base


def prepare_vle(student_vle: pd.DataFrame, vle: pd.DataFrame) -> pd.DataFrame:
    raw_rows = len(student_vle)
    exact_duplicate_rows = int(student_vle.duplicated(keep="first").sum())
    deduped = student_vle.drop_duplicates().copy()
    print(
        "VLE exact duplicate handling: "
        f"raw_rows={raw_rows}, exact_duplicate_rows={exact_duplicate_rows}, rows_after_exact_drop={len(deduped)}"
    )

    vle_meta = vle[["id_site", "activity_type"]].drop_duplicates(subset=["id_site"])
    deduped = deduped.merge(vle_meta, on="id_site", how="left")
    missing_activity_type = int(deduped["activity_type"].isna().sum())
    print(f"VLE rows without activity_type after id_site join: {missing_activity_type}")
    deduped["activity_type"] = deduped["activity_type"].fillna("unknown_activity_type")
    return deduped


def aggregate_vle_for_cutoff(vle_deduped: pd.DataFrame, cutoff_day: int) -> pd.DataFrame:
    cutoff_rows = vle_deduped[vle_deduped["date"] <= cutoff_day].copy()
    future_rows = len(vle_deduped) - len(cutoff_rows)

    grouped_sum = (
        cutoff_rows.groupby(VLE_KEY + ["activity_type"], dropna=False)["sum_click"]
        .sum()
        .rename("sum_click_sum_strategy")
        .reset_index()
    )
    grouped_max = (
        cutoff_rows.groupby(VLE_KEY + ["activity_type"], dropna=False)["sum_click"]
        .max()
        .rename("sum_click_max_strategy")
        .reset_index()
    )
    grouped = grouped_sum.merge(grouped_max, on=VLE_KEY + ["activity_type"], how="inner")

    base_agg = grouped.groupby(BASE_KEY, dropna=False).agg(
        total_click_until_cutoff_sum_strategy=("sum_click_sum_strategy", "sum"),
        total_click_until_cutoff_max_strategy=("sum_click_max_strategy", "sum"),
        active_days_until_cutoff=("date", "nunique"),
        used_site_count_until_cutoff=("id_site", "nunique"),
        first_activity_date_until_cutoff=("date", "min"),
        last_activity_date_until_cutoff=("date", "max"),
    ).reset_index()
    base_agg["avg_click_per_active_day_until_cutoff_sum_strategy"] = (
        base_agg["total_click_until_cutoff_sum_strategy"] / base_agg["active_days_until_cutoff"]
    )
    base_agg["avg_click_per_active_day_until_cutoff_max_strategy"] = (
        base_agg["total_click_until_cutoff_max_strategy"] / base_agg["active_days_until_cutoff"]
    )
    base_agg["days_since_last_activity_at_cutoff"] = cutoff_day - base_agg["last_activity_date_until_cutoff"]

    activity_sum = grouped.pivot_table(
        index=BASE_KEY,
        columns="activity_type",
        values="sum_click_sum_strategy",
        aggfunc="sum",
        fill_value=0,
    )
    activity_sum.columns = [f"clicks_activity_{clean_name(col)}_sum_strategy" for col in activity_sum.columns]
    activity_sum = activity_sum.reset_index()

    activity_max = grouped.pivot_table(
        index=BASE_KEY,
        columns="activity_type",
        values="sum_click_max_strategy",
        aggfunc="sum",
        fill_value=0,
    )
    activity_max.columns = [f"clicks_activity_{clean_name(col)}_max_strategy" for col in activity_max.columns]
    activity_max = activity_max.reset_index()

    result = base_agg.merge(activity_sum, on=BASE_KEY, how="left").merge(activity_max, on=BASE_KEY, how="left")
    print(
        f"VLE cutoff day {cutoff_day}: allowed_rows={len(cutoff_rows)}, "
        f"future_rows_excluded={future_rows}, output_rows={len(result)}"
    )
    return result


def aggregate_assessments_for_cutoff(
    student_assessment: pd.DataFrame,
    assessments: pd.DataFrame,
    cutoff_day: int,
) -> pd.DataFrame:
    cutoff_rows = student_assessment[student_assessment["date_submitted"] <= cutoff_day].copy()
    future_rows = len(student_assessment) - len(cutoff_rows)

    assessment_meta = assessments[
        ["code_module", "code_presentation", "id_assessment", "date", "weight"]
    ].copy()
    joined = cutoff_rows.merge(assessment_meta, on="id_assessment", how="left", validate="many_to_one")
    unmatched_assessments = int(joined["code_module"].isna().sum())
    print(
        f"Assessment cutoff day {cutoff_day}: allowed_rows={len(cutoff_rows)}, "
        f"future_rows_excluded={future_rows}, unmatched_assessment_rows={unmatched_assessments}"
    )

    joined["has_due_date"] = joined["date"].notna()
    joined["submitted_late"] = np.where(
        joined["has_due_date"],
        (joined["date_submitted"] > joined["date"]).astype(int),
        np.nan,
    )
    joined["weighted_score_component"] = joined["score"] * joined["weight"]
    joined["weight_for_scored_submission"] = np.where(joined["score"].notna(), joined["weight"], np.nan)

    agg = joined.groupby(BASE_KEY, dropna=False).agg(
        assessment_count_until_cutoff=("id_assessment", "count"),
        mean_score_until_cutoff=("score", "mean"),
        min_score_until_cutoff=("score", "min"),
        max_score_until_cutoff=("score", "max"),
        submitted_late_count_until_cutoff=("submitted_late", "sum"),
        assessment_rows_missing_due_date_until_cutoff=("has_due_date", lambda s: int((~s).sum())),
        scored_assessment_count_until_cutoff=("score", "count"),
        weighted_score_numerator=("weighted_score_component", "sum"),
        weighted_score_denominator=("weight_for_scored_submission", "sum"),
    ).reset_index()
    agg["weighted_score_until_cutoff"] = np.where(
        agg["weighted_score_denominator"] > 0,
        agg["weighted_score_numerator"] / agg["weighted_score_denominator"],
        np.nan,
    )
    agg = agg.drop(columns=["weighted_score_numerator", "weighted_score_denominator"])
    return agg


def clean_name(value: object) -> str:
    return (
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
    )


def fill_count_features(df: pd.DataFrame) -> pd.DataFrame:
    count_like = [
        col
        for col in df.columns
        if col.startswith("total_click_")
        or col.startswith("active_days_")
        or col.startswith("used_site_count_")
        or col.startswith("clicks_activity_")
        or col in {
            "assessment_count_until_cutoff",
            "submitted_late_count_until_cutoff",
            "assessment_rows_missing_due_date_until_cutoff",
            "scored_assessment_count_until_cutoff",
        }
    ]
    for col in count_like:
        df[col] = df[col].fillna(0)
    return df


def validate_output(df: pd.DataFrame, cutoff_name: str, cutoff_day: int, path: Path) -> dict[str, object]:
    duplicated_key_count = int(df.duplicated(subset=BASE_KEY, keep=False).sum())
    target_counts = df["target_withdrawn"].value_counts(dropna=False).sort_index()
    target_summary = ", ".join([f"{idx}: {count}" for idx, count in target_counts.items()])

    missing = df.isna().sum()
    missing = missing[missing > 0].sort_values(ascending=False)
    missing_summary = missing.reset_index()
    missing_summary.columns = ["column", "missing_count"]

    forbidden_columns = [col for col in df.columns if col == "date_unregistration"]
    after_cutoff_violations = []
    if "last_activity_date_until_cutoff" in df and df["last_activity_date_until_cutoff"].dropna().gt(cutoff_day).any():
        after_cutoff_violations.append("last_activity_date_until_cutoff")
    if "first_activity_date_until_cutoff" in df and df["first_activity_date_until_cutoff"].dropna().gt(cutoff_day).any():
        after_cutoff_violations.append("first_activity_date_until_cutoff")

    print(f"\nVALIDATION {cutoff_name} day {cutoff_day}")
    print(f"Output file: {path}")
    print(f"Shape: {df.shape}")
    print(f"Duplicated base key row count: {duplicated_key_count}")
    print(f"Target distribution: {target_summary}")
    print(f"Columns created ({len(df.columns)}): {', '.join(df.columns)}")
    print(f"Forbidden predictor columns present: {forbidden_columns}")
    print(f"Any feature evidence after cutoff: {bool(after_cutoff_violations)} {after_cutoff_violations}")
    print("Missing value summary, nonzero only:")
    print(missing_summary.to_string(index=False) if not missing_summary.empty else "No missing values.")

    return {
        "cutoff": cutoff_name,
        "cutoff_day": cutoff_day,
        "path": str(path.relative_to(ROOT)),
        "rows": df.shape[0],
        "columns": df.shape[1],
        "duplicated_base_key_rows": duplicated_key_count,
        "target_distribution": target_summary,
        "missing_columns_nonzero": len(missing_summary),
        "forbidden_columns_present": ", ".join(forbidden_columns) if forbidden_columns else "",
        "after_cutoff_feature_violations": ", ".join(after_cutoff_violations) if after_cutoff_violations else "",
    }


def write_report(validation_rows: list[dict[str, object]], output_columns: dict[str, list[str]]) -> None:
    validation_df = pd.DataFrame(validation_rows)
    lines = [
        "# Feature Pipeline Report",
        "",
        "## Scope",
        "",
        "This report documents the leakage-safe feature pipeline outputs. No final models were trained.",
        "",
        "## Output Files",
        markdown_table(validation_df),
        "",
        "## Feature Rules Applied",
        "",
        "- Base unit is one row per `code_module`, `code_presentation`, `id_student` from `studentInfo.csv`.",
        "- `final_result` is retained for analysis and `target_withdrawn` is created from it.",
        "- `final_result`, `target_withdrawn`, and key columns must be excluded from predictor columns by model-training code.",
        "- `date_unregistration` is not included in any output file.",
        "- VLE rows are filtered with `studentVle.date <= cutoff_day` before aggregation.",
        "- Assessment rows are filtered with `studentAssessment.date_submitted <= cutoff_day` before aggregation.",
        "- Full-course VLE totals and full-course assessment summaries are not used.",
        "- Static categorical values are kept raw for future encoding.",
        "",
        "## VLE Duplicate Strategy",
        "",
        "The final treatment for `student_vle` key duplicates is unresolved. This script removes exact duplicate rows, then provides both key-level sum and key-level max click variants for VLE click features. Future review must choose one strategy before final modeling.",
        "",
        "## Missing Handling",
        "",
        "- Missing static values are retained.",
        "- Count-like features are filled with 0 after left joins because absence of observed cutoff activity means no observed rows for that cutoff, not a dropped student.",
        "- Score/date-derived numeric summaries remain missing where no qualifying observed row exists.",
        "- `is_registered_before_start` remains missing when `date_registration` is missing.",
        "",
        "## Columns By Output",
    ]
    for cutoff_name, columns in output_columns.items():
        lines.extend(
            [
                "",
                f"### {cutoff_name}",
                "",
                *[f"- `{col}`" for col in columns],
            ]
        )
    lines.extend(
        [
            "",
            "## Open Decisions",
            "",
            "- Choose the final VLE duplicate strategy: sum, max, or another reviewed treatment.",
            "- Decide cohort handling for students already withdrawn before each cutoff.",
            "- Decide missing-value encoding/imputation rules for modeling.",
            "- Decide whether `is_banked`, VLE `week_from/week_to`, and course length metadata should be used in later iterations.",
            "- Decide final encoding plan for raw categorical variables.",
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REPORT_PATH.relative_to(ROOT)}")


def append_decision_log() -> None:
    entry = """# Decision Log

## Feature Pipeline Agent

- Decision: Raw data files were not modified.
- Decision: Feature outputs are written to `data/processed/` as derived artifacts.
- Decision: `studentInfo.csv` is the base table, using one row per `code_module`, `code_presentation`, `id_student`.
- Decision: `date_unregistration` is excluded from feature outputs because the leakage review marks it unsafe as a predictor.
- Decision: VLE rows are filtered by cutoff before aggregation.
- Decision: Assessment rows are filtered by cutoff before aggregation.
- Decision: Exact duplicate rows in `studentVle.csv` are removed inside the feature script before VLE aggregation. This is a derived-pipeline step only; raw data is unchanged.
- Decision: Remaining `student_vle` key-duplicate treatment is unresolved, so both sum and max click aggregation variants are emitted.
- Decision: Count-like missing values after left joins are filled with 0 to preserve all base students while representing no observed cutoff activity.
- Unresolved: Missing-value treatment for model-ready matrices is not finalized.
- Unresolved: Final VLE duplicate strategy is not finalized.
- Unresolved: Active-at-cutoff cohort treatment is not finalized.
"""
    if DECISION_LOG_PATH.exists():
        current = DECISION_LOG_PATH.read_text(encoding="utf-8")
        if "## Feature Pipeline Agent" in current:
            return
        DECISION_LOG_PATH.write_text(current.rstrip() + "\n\n" + "\n".join(entry.splitlines()[2:]) + "\n", encoding="utf-8")
    else:
        DECISION_LOG_PATH.write_text(entry, encoding="utf-8")
    print(f"Wrote {DECISION_LOG_PATH.relative_to(ROOT)}")


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
    tables = read_raw_tables()
    base = build_base(tables["student_info"], tables["student_registration"])
    vle_deduped = prepare_vle(tables["student_vle"], tables["vle"])

    validation_rows = []
    output_columns = {}
    for cutoff_name, cutoff_day in CUTOFFS.items():
        print(f"\nBuilding features for {cutoff_name} day {cutoff_day}")
        vle_features = aggregate_vle_for_cutoff(vle_deduped, cutoff_day)
        assessment_features = aggregate_assessments_for_cutoff(
            tables["student_assessment"],
            tables["assessments"],
            cutoff_day,
        )

        features = base.merge(vle_features, on=BASE_KEY, how="left").merge(
            assessment_features,
            on=BASE_KEY,
            how="left",
        )
        features = fill_count_features(features)

        path = PROCESSED_DIR / f"features_{cutoff_name}.csv"
        features.to_csv(path, index=False)
        print(f"Wrote {path.relative_to(ROOT)}")
        validation_rows.append(validate_output(features, cutoff_name, cutoff_day, path))
        output_columns[cutoff_name] = list(features.columns)

    write_report(validation_rows, output_columns)
    print("\nFeature pipeline complete. No final models were trained.")


if __name__ == "__main__":
    main()
