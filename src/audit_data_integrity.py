from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "kaggle_oulad"
REPORT_DIR = ROOT / "reports"
TABLE_DIR = REPORT_DIR / "tables"
REPORT_PATH = REPORT_DIR / "data_integrity_report.md"

TABLE_FILES = {
    "courses": "courses.csv",
    "assessments": "assessments.csv",
    "vle": "vle.csv",
    "student_info": "studentInfo.csv",
    "student_registration": "studentRegistration.csv",
    "student_assessment": "studentAssessment.csv",
    "student_vle": "studentVle.csv",
}

KEYS = {
    "courses": ["code_module", "code_presentation"],
    "assessments": ["id_assessment"],
    "vle": ["id_site"],
    "student_info": ["code_module", "code_presentation", "id_student"],
    "student_registration": ["code_module", "code_presentation", "id_student"],
    "student_assessment": ["id_assessment", "id_student"],
    "student_vle": ["code_module", "code_presentation", "id_student", "id_site", "date"],
}

SCP_KEY = ["code_module", "code_presentation", "id_student"]
VLE_KEY = ["code_module", "code_presentation", "id_student", "id_site", "date"]

RANGE_COLUMNS = {
    "student_registration": ["date_registration", "date_unregistration"],
    "student_assessment": ["date_submitted", "score"],
    "student_vle": ["date", "sum_click"],
    "assessments": ["date", "weight"],
}


def ensure_dirs() -> None:
    REPORT_DIR.mkdir(exist_ok=True)
    TABLE_DIR.mkdir(exist_ok=True)


def load_tables() -> dict[str, pd.DataFrame]:
    tables = {}
    print(f"Reading raw data from: {DATA_DIR}")
    for name, filename in TABLE_FILES.items():
        path = DATA_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing expected table: {path}")
        df = pd.read_csv(path)
        tables[name] = df
        print(f"Loaded {name}: shape={df.shape}, file={path}")
    return tables


def save_table(df: pd.DataFrame, filename: str) -> Path:
    path = TABLE_DIR / filename
    df.to_csv(path, index=False)
    print(f"Wrote {path.relative_to(ROOT)}")
    return path


def markdown_table(df: pd.DataFrame, max_rows: int | None = None) -> str:
    shown = df if max_rows is None else df.head(max_rows)
    if shown.empty:
        return "_No rows._"
    string_df = shown.copy()
    for column in string_df.columns:
        string_df[column] = string_df[column].map(format_markdown_cell)
    headers = [str(column) for column in string_df.columns]
    rows = string_df.values.tolist()
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def format_markdown_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def table_shape_check(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = [
        {"table": name, "rows": len(df), "columns": df.shape[1]}
        for name, df in tables.items()
    ]
    result = pd.DataFrame(rows)
    print("\nTABLE SHAPES")
    print(result.to_string(index=False))
    save_table(result, "table_shapes.csv")
    return result


def missing_value_check(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for table, df in tables.items():
        missing = df.isna().sum()
        missing = missing[missing > 0]
        for column, count in missing.items():
            rows.append(
                {
                    "table": table,
                    "column": column,
                    "missing_count": int(count),
                    "missing_ratio": float(count / len(df)) if len(df) else np.nan,
                }
            )
    result = pd.DataFrame(rows, columns=["table", "column", "missing_count", "missing_ratio"])
    print("\nMISSING VALUES, NONZERO ONLY")
    print(result.to_string(index=False) if not result.empty else "No missing values found.")
    save_table(result, "missing_values_nonzero.csv")
    return result


def key_uniqueness_check(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for table, key in KEYS.items():
        df = tables[table]
        duplicate_count = int(df.duplicated(subset=key, keep="first").sum())
        duplicate_groups = int(df.loc[df.duplicated(subset=key, keep=False), key].drop_duplicates().shape[0])
        rows.append(
            {
                "table": table,
                "key": ", ".join(key),
                "rows": len(df),
                "duplicated_rows_by_key": duplicate_count,
                "duplicated_key_groups": duplicate_groups,
            }
        )
    result = pd.DataFrame(rows)
    print("\nKEY UNIQUENESS")
    print(result.to_string(index=False))
    save_table(result, "key_duplicates.csv")
    return result


def student_vle_duplicate_analysis(student_vle: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    print("\nSTUDENT_VLE DUPLICATE ANALYSIS")
    total_rows = len(student_vle)
    exact_duplicate_rows = int(student_vle.duplicated(keep="first").sum())
    key_duplicate_rows = int(student_vle.duplicated(subset=VLE_KEY, keep="first").sum())

    after_exact = student_vle.drop_duplicates()
    rows_after_exact = len(after_exact)
    remaining_key_duplicate_rows = int(after_exact.duplicated(subset=VLE_KEY, keep="first").sum())

    duplicated_group_sizes = (
        after_exact.groupby(VLE_KEY, dropna=False)
        .size()
        .rename("group_size")
        .reset_index()
    )
    duplicated_group_sizes = duplicated_group_sizes[duplicated_group_sizes["group_size"] > 1]
    duplicated_key_groups = len(duplicated_group_sizes)
    group_size_distribution = (
        duplicated_group_sizes["group_size"]
        .value_counts()
        .sort_index()
        .rename_axis("group_size")
        .reset_index(name="group_count")
    )

    sum_click_nunique = (
        after_exact.groupby(VLE_KEY, dropna=False)["sum_click"]
        .nunique(dropna=False)
        .rename("sum_click_unique_values")
        .reset_index()
    )
    groups_with_different_sum_click = int((sum_click_nunique["sum_click_unique_values"] > 1).sum())
    duplicated_groups_with_different_sum_click = int(
        duplicated_group_sizes[VLE_KEY]
        .merge(sum_click_nunique, on=VLE_KEY, how="left")["sum_click_unique_values"]
        .gt(1)
        .sum()
    )

    raw_total_clicks = int(student_vle["sum_click"].sum())
    exact_dedup_total_clicks = int(after_exact["sum_click"].sum())
    key_sum_total_clicks = int(after_exact.groupby(VLE_KEY, dropna=False)["sum_click"].sum().sum())
    key_max_total_clicks = int(after_exact.groupby(VLE_KEY, dropna=False)["sum_click"].max().sum())

    summary = pd.DataFrame(
        [
            {"metric": "total_rows", "value": total_rows},
            {"metric": "exact_duplicate_rows", "value": exact_duplicate_rows},
            {"metric": "key_duplicate_rows", "value": key_duplicate_rows},
            {"metric": "rows_after_exact_duplicate_removal", "value": rows_after_exact},
            {"metric": "remaining_key_duplicate_rows_after_exact_removal", "value": remaining_key_duplicate_rows},
            {"metric": "duplicated_key_groups_after_exact_removal", "value": duplicated_key_groups},
            {"metric": "all_key_groups_with_different_sum_click_after_exact_removal", "value": groups_with_different_sum_click},
            {"metric": "duplicated_key_groups_with_different_sum_click_after_exact_removal", "value": duplicated_groups_with_different_sum_click},
            {"metric": "raw_total_clicks", "value": raw_total_clicks},
            {"metric": "total_clicks_after_exact_duplicate_removal", "value": exact_dedup_total_clicks},
            {"metric": "total_clicks_after_key_aggregation_sum", "value": key_sum_total_clicks},
            {"metric": "total_clicks_after_key_aggregation_max", "value": key_max_total_clicks},
        ]
    )

    print(summary.to_string(index=False))
    print("\nstudent_vle duplicated group size distribution")
    print(group_size_distribution.to_string(index=False))

    save_table(summary, "student_vle_duplicate_summary.csv")
    save_table(group_size_distribution, "student_vle_duplicate_group_size_distribution.csv")
    return summary, group_size_distribution


def referential_integrity_check(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    checks = [
        ("student_info_to_student_registration", tables["student_info"][SCP_KEY], tables["student_registration"][SCP_KEY], SCP_KEY),
        ("student_vle_to_student_info", tables["student_vle"][SCP_KEY], tables["student_info"][SCP_KEY], SCP_KEY),
        ("student_assessment_to_assessments", tables["student_assessment"][["id_assessment"]], tables["assessments"][["id_assessment"]], ["id_assessment"]),
        ("student_vle_to_vle", tables["student_vle"][["id_site"]], tables["vle"][["id_site"]], ["id_site"]),
    ]
    rows = []
    for name, left, right, key in checks:
        merged = left.drop_duplicates().merge(
            right.drop_duplicates(),
            on=key,
            how="outer",
            indicator=True,
        )
        counts = merged["_merge"].value_counts().to_dict()
        rows.append(
            {
                "check": name,
                "key": ", ".join(key),
                "both": int(counts.get("both", 0)),
                "left_only": int(counts.get("left_only", 0)),
                "right_only": int(counts.get("right_only", 0)),
            }
        )
    result = pd.DataFrame(rows)
    print("\nREFERENTIAL INTEGRITY")
    print(result.to_string(index=False))
    save_table(result, "referential_integrity.csv")
    return result


def range_check(tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    stat_rows = []
    flag_rows = []
    for table, columns in RANGE_COLUMNS.items():
        df = tables[table]
        for column in columns:
            s = pd.to_numeric(df[column], errors="coerce")
            desc = s.describe(percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99])
            row = {"table": table, "column": column}
            for idx, value in desc.items():
                row[str(idx)] = float(value) if pd.notna(value) else np.nan
            stat_rows.append(row)

            if column in {"score", "weight"}:
                negative = int((s < 0).sum())
                above_100 = int((s > 100).sum())
                if negative or above_100:
                    flag_rows.append(
                        {
                            "table": table,
                            "column": column,
                            "issue": "outside expected 0-100 range",
                            "count": negative + above_100,
                        }
                    )
            if column in {"date_registration", "date_unregistration", "date_submitted", "date"}:
                very_negative = int((s < -365).sum())
                if very_negative:
                    flag_rows.append(
                        {
                            "table": table,
                            "column": column,
                            "issue": "date offset less than -365",
                            "count": very_negative,
                        }
                    )
            if column == "sum_click":
                negative = int((s < 0).sum())
                if negative:
                    flag_rows.append(
                        {
                            "table": table,
                            "column": column,
                            "issue": "negative click count",
                            "count": negative,
                        }
                    )

    stats = pd.DataFrame(stat_rows)
    flags = pd.DataFrame(flag_rows, columns=["table", "column", "issue", "count"])
    print("\nDATE AND NUMERIC RANGE STATS")
    print(stats.to_string(index=False))
    print("\nSUSPICIOUS RANGE FLAGS")
    print(flags.to_string(index=False) if not flags.empty else "No suspicious range flags from configured rules.")
    save_table(stats, "date_numeric_range_stats.csv")
    save_table(flags, "date_numeric_range_flags.csv")
    return stats, flags


def target_distribution(student_info: pd.DataFrame) -> dict[str, pd.DataFrame]:
    def counts_with_ratio(group_cols: list[str] | None = None) -> pd.DataFrame:
        if group_cols is None:
            counts = student_info["final_result"].value_counts(dropna=False).rename_axis("final_result").reset_index(name="count")
            counts["ratio"] = counts["count"] / counts["count"].sum()
            return counts
        counts = (
            student_info.groupby(group_cols, dropna=False)["final_result"]
            .value_counts(dropna=False)
            .rename("count")
            .reset_index()
        )
        counts["ratio_within_group"] = counts["count"] / counts.groupby(group_cols)["count"].transform("sum")
        return counts

    outputs = {
        "overall": counts_with_ratio(),
        "by_module": counts_with_ratio(["code_module"]),
        "by_presentation": counts_with_ratio(["code_presentation"]),
        "by_module_presentation": counts_with_ratio(["code_module", "code_presentation"]),
    }

    print("\nTARGET DISTRIBUTION: OVERALL")
    print(outputs["overall"].to_string(index=False))
    for name, df in outputs.items():
        save_table(df, f"target_distribution_{name}.csv")
    return outputs


def build_report(
    shapes: pd.DataFrame,
    missing: pd.DataFrame,
    key_duplicates: pd.DataFrame,
    vle_dup_summary: pd.DataFrame,
    vle_group_dist: pd.DataFrame,
    referential: pd.DataFrame,
    range_stats: pd.DataFrame,
    range_flags: pd.DataFrame,
    target_outputs: dict[str, pd.DataFrame],
) -> None:
    risks = []
    if key_duplicates["duplicated_rows_by_key"].gt(0).any():
        risks.append("At least one expected key is not unique; joins using those keys can multiply rows.")
    student_vle_remaining = int(
        vle_dup_summary.loc[
            vle_dup_summary["metric"] == "remaining_key_duplicate_rows_after_exact_removal", "value"
        ].iloc[0]
    )
    if student_vle_remaining:
        risks.append("student_vle still has duplicate key rows after exact duplicate removal.")
    different_click_groups = int(
        vle_dup_summary.loc[
            vle_dup_summary["metric"] == "duplicated_key_groups_with_different_sum_click_after_exact_removal", "value"
        ].iloc[0]
    )
    if different_click_groups:
        risks.append("Some duplicated student_vle key groups have different sum_click values.")
    if referential[["left_only", "right_only"]].sum().sum() > 0:
        risks.append("Some referential integrity checks have left_only or right_only keys.")
    if not range_flags.empty:
        risks.append("Configured range checks found suspicious values.")

    findings = [
        "All expected Kaggle OULAD tables were loaded from data/kaggle_oulad.",
        "This audit does not drop rows, save cleaned data, create final features, or train models.",
    ]
    findings.extend(risks if risks else ["No high-level integrity risks were flagged by the configured checks."])

    lines = [
        "# Data Integrity Report",
        "",
        "## Findings",
        *[f"- {item}" for item in findings],
        "",
        "## Evidence Tables",
        "",
        "### Table shapes",
        markdown_table(shapes),
        "",
        "### Missing values, nonzero only",
        markdown_table(missing),
        "",
        "### Key uniqueness",
        markdown_table(key_duplicates),
        "",
        "### student_vle duplicate summary",
        markdown_table(vle_dup_summary),
        "",
        "### student_vle duplicated group size distribution",
        markdown_table(vle_group_dist),
        "",
        "### Referential integrity",
        markdown_table(referential),
        "",
        "### Date and numeric range statistics",
        markdown_table(range_stats),
        "",
        "### Suspicious range flags",
        markdown_table(range_flags),
        "",
        "### Target distribution, overall",
        markdown_table(target_outputs["overall"]),
        "",
        "### Target distribution by module",
        markdown_table(target_outputs["by_module"]),
        "",
        "### Target distribution by presentation",
        markdown_table(target_outputs["by_presentation"]),
        "",
        "### Target distribution by module-presentation",
        markdown_table(target_outputs["by_module_presentation"]),
        "",
        "## Risks",
        *[f"- {item}" for item in risks],
        "" if risks else "- No risks were emitted by the configured rules.",
        "",
        "## Recommended Next Checks",
        "- Review leakage rules for unregistration dates, assessment dates/scores, and VLE activity after each prediction cutoff.",
        "- Decide how to treat student_vle exact duplicates and remaining key duplicates before creating click-based features.",
        "- Validate join plans from student_info as the student-course-presentation base unit before feature engineering.",
        "- Compare Kaggle tables against official OULAD where file-level discrepancies may matter.",
        "",
        "## Unresolved Decisions",
        "- No final treatment has been chosen for student_vle duplicates.",
        "- No missing-value imputation or row exclusion rule has been chosen.",
        "- No cutoff-specific leakage boundary has been finalized.",
        "- No final feature construction or modeling has been performed.",
        "",
        "## Generated CSV Evidence",
        *[f"- reports/tables/{path.name}" for path in sorted(TABLE_DIR.glob('*.csv'))],
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REPORT_PATH.relative_to(ROOT)}")


def main() -> None:
    ensure_dirs()
    tables = load_tables()
    shapes = table_shape_check(tables)
    missing = missing_value_check(tables)
    key_duplicates = key_uniqueness_check(tables)
    vle_dup_summary, vle_group_dist = student_vle_duplicate_analysis(tables["student_vle"])
    referential = referential_integrity_check(tables)
    range_stats, range_flags = range_check(tables)
    target_outputs = target_distribution(tables["student_info"])
    build_report(
        shapes,
        missing,
        key_duplicates,
        vle_dup_summary,
        vle_group_dist,
        referential,
        range_stats,
        range_flags,
        target_outputs,
    )
    print("\nAudit complete. No raw data was modified; no cleaned data, features, or models were created.")


if __name__ == "__main__":
    main()
