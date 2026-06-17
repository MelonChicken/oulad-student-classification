from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR_CANDIDATES = [
    ROOT / "data" / "kaggle_oulad",
    ROOT / "open+university+learning+analytics+dataset",
]
RAW_DIR = next((path for path in RAW_DIR_CANDIDATES if path.exists()), RAW_DIR_CANDIDATES[0])
PROCESSED_DIR = ROOT / "data" / "processed"
REPORT_DIR = ROOT / "reports"
REPORT_PATH = REPORT_DIR / "cohort_report.md"
DECISION_LOG_PATH = REPORT_DIR / "decision_log.md"

BASE_KEY = ["code_module", "code_presentation", "id_student"]
CUTOFFS = {"week5": 35, "week7": 49, "week10": 70}


def ensure_dirs() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def load_registration() -> pd.DataFrame:
    registration = pd.read_csv(
        RAW_DIR / "studentRegistration.csv",
        usecols=BASE_KEY + ["date_registration", "date_unregistration"],
        na_values="?",
    )
    duplicated_keys = int(registration.duplicated(subset=BASE_KEY, keep=False).sum())
    if duplicated_keys:
        raise ValueError(f"studentRegistration has duplicated base keys: {duplicated_keys}")
    return registration.rename(columns={"date_registration": "cohort_date_registration"})


def build_cohort_for_cutoff(
    cutoff_name: str,
    cutoff_day: int,
    registration: pd.DataFrame,
) -> dict[str, object]:
    input_path = PROCESSED_DIR / f"features_{cutoff_name}.csv"
    output_path = PROCESSED_DIR / f"features_{cutoff_name}_cohort.csv"

    features = pd.read_csv(input_path)
    before_rows = len(features)
    if features.duplicated(subset=BASE_KEY, keep=False).any():
        duplicated = int(features.duplicated(subset=BASE_KEY, keep=False).sum())
        raise ValueError(f"{input_path.name} has duplicated base keys: {duplicated}")

    cohort_source = features.merge(registration, on=BASE_KEY, how="left", validate="one_to_one")
    missing_registration_join = int(cohort_source["cohort_date_registration"].isna().sum())

    # Keep students who were registered by the cutoff and not yet unregistered by the cutoff.
    registered_by_cutoff = (
        cohort_source["cohort_date_registration"].isna()
        | cohort_source["cohort_date_registration"].le(cutoff_day)
    )
    not_unregistered_by_cutoff = (
        cohort_source["date_unregistration"].isna()
        | cohort_source["date_unregistration"].gt(cutoff_day)
    )
    active_mask = registered_by_cutoff & not_unregistered_by_cutoff

    late_registration_rows = int((~registered_by_cutoff & not_unregistered_by_cutoff).sum())
    pre_cutoff_unregistration_rows = int((registered_by_cutoff & ~not_unregistered_by_cutoff).sum())
    both_late_and_unregistered_rows = int((~registered_by_cutoff & ~not_unregistered_by_cutoff).sum())

    cohort = cohort_source.loc[active_mask, features.columns].copy()
    after_rows = len(cohort)
    if "date_unregistration" in cohort.columns:
        raise ValueError(f"{output_path.name} would include date_unregistration")
    if cohort["date_registration"].gt(cutoff_day).any():
        raise ValueError(f"{output_path.name} contains registration dates after cutoff")
    if cohort.duplicated(subset=BASE_KEY, keep=False).any():
        duplicated = int(cohort.duplicated(subset=BASE_KEY, keep=False).sum())
        raise ValueError(f"{output_path.name} has duplicated base keys: {duplicated}")

    cohort.to_csv(output_path, index=False)

    target_counts = (
        cohort["final_result"].value_counts(dropna=False).sort_index().to_dict()
        if "final_result" in cohort.columns
        else {}
    )
    print(
        f"{cutoff_name}: input_rows={before_rows}, output_rows={after_rows}, "
        f"excluded={before_rows - after_rows}, late_registration_excluded={late_registration_rows}, "
        f"pre_cutoff_unregistration_excluded={pre_cutoff_unregistration_rows}, "
        f"both_excluded={both_late_and_unregistered_rows}, missing_registration_join={missing_registration_join}"
    )

    return {
        "cutoff": cutoff_name,
        "cutoff_day": cutoff_day,
        "input_rows": before_rows,
        "output_rows": after_rows,
        "excluded_rows": before_rows - after_rows,
        "late_registration_excluded": late_registration_rows,
        "pre_cutoff_unregistration_excluded": pre_cutoff_unregistration_rows,
        "both_late_and_unregistered_excluded": both_late_and_unregistered_rows,
        "missing_date_registration_retained": int(cohort["date_registration"].isna().sum()),
        "date_unregistration_present": "date_unregistration" in cohort.columns,
        "duplicated_base_key_rows": int(cohort.duplicated(subset=BASE_KEY, keep=False).sum()),
        "target_distribution": ", ".join(f"{k}: {v}" for k, v in target_counts.items()),
        "path": str(output_path.relative_to(ROOT)),
    }


def write_report(rows: list[dict[str, object]]) -> None:
    df = pd.DataFrame(rows)
    lines = [
        "# Cohort Report",
        "",
        "## Scope",
        "",
        "This report documents active-at-cutoff cohort construction. Raw data files were not modified.",
        "",
        "## Cohort Rule",
        "",
        "Rows are retained when:",
        "",
        "```python",
        "(date_registration.isna() or date_registration <= cutoff_day) and",
        "(date_unregistration.isna() or date_unregistration > cutoff_day)",
        "```",
        "",
        "`date_unregistration` is used only for cohort construction and is not written to cohort outputs.",
        "Rows with missing `date_registration` are retained because registration status cannot be confirmed and the count is small; downstream baseline outputs keep missing flags.",
        "",
        "## Output Files",
        "",
        markdown_table(df),
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REPORT_PATH.relative_to(ROOT)}")


def append_decision_log() -> None:
    entry = """
## Cohort Revision Agent

- Decision: Active-at-cutoff cohort now requires registration on or before each cutoff, unless `date_registration` is missing.
- Decision: Active-at-cutoff cohort retains rows only when `date_registration <= cutoff_day` or missing, and `date_unregistration > cutoff_day` or missing.
- Decision: `date_unregistration` is used only for cohort construction and is not written to cohort or baseline outputs.
- Decision: Rows with missing `date_registration` are retained in the baseline cohort with missing flags because the count is small and registration status cannot be confirmed.
"""
    current = DECISION_LOG_PATH.read_text(encoding="utf-8") if DECISION_LOG_PATH.exists() else "# Decision Log\n"
    if "## Cohort Revision Agent" not in current:
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
    registration = load_registration()
    rows = [
        build_cohort_for_cutoff(cutoff_name, cutoff_day, registration)
        for cutoff_name, cutoff_day in CUTOFFS.items()
    ]
    write_report(rows)
    print("\nCohort build complete. No final models were trained.")


if __name__ == "__main__":
    main()
