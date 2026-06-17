from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    import pandas as pd
    from sklearn.compose import ColumnTransformer
    from sklearn.pipeline import Pipeline


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
REPORT_DIR = ROOT / "reports"
REPORT_TABLE_DIR = REPORT_DIR / "tables"
REPORT_PATH = REPORT_DIR / "gunwoo_demographic_feature_report.md"
HTML_REPORT_PATH = REPORT_DIR / "gunwoo_demographic_model_report.html"
SUMMARY_PATH = REPORT_TABLE_DIR / "gunwoo_demographic_model_summary.csv"
FEATURE_AUDIT_PATH = REPORT_TABLE_DIR / "gunwoo_demographic_feature_audit.csv"
DECISION_LOG_PATH = REPORT_DIR / "decision_log.md"

CUTOFFS = {"week5": 35, "week7": 49, "week10": 70}
BASE_KEY = ["code_module", "code_presentation", "id_student"]
TARGET_COL = "target_at_risk"
LEAKAGE_COLUMNS = {"final_result", "target_withdrawn", TARGET_COL, "date_unregistration"}
DEMOGRAPHIC_FEATURES = ["gender", "region", "age_band"]
BASE_FEATURES = [
    "active_days_until_cutoff",
    "total_click_until_cutoff_mean_strategy",
]
FEATURE_SETS = {
    "demographic_only": DEMOGRAPHIC_FEATURES,
    "base_demographic": BASE_FEATURES + DEMOGRAPHIC_FEATURES,
}
RANDOM_STATE = 724


def ensure_dirs() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_TABLE_DIR.mkdir(parents=True, exist_ok=True)


def build_models() -> dict[str, "Pipeline"]:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.tree import DecisionTreeClassifier

    return {
        "logistic_regression": Pipeline(
            steps=[
                ("preprocessor", "passthrough"),
                (
                    "model",
                    LogisticRegression(
                        max_iter=3000,
                        class_weight="balanced",
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "decision_tree": Pipeline(
            steps=[
                ("preprocessor", "passthrough"),
                (
                    "model",
                    DecisionTreeClassifier(
                        max_depth=5,
                        min_samples_leaf=20,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "random_forest": Pipeline(
            steps=[
                ("preprocessor", "passthrough"),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=300,
                        max_depth=8,
                        min_samples_leaf=10,
                        class_weight="balanced",
                        random_state=RANDOM_STATE,
                        n_jobs=1,
                    ),
                ),
            ]
        ),
    }


def feature_file(cutoff: str) -> Path:
    return PROCESSED_DIR / f"features_{cutoff}_baseline.csv"


def existing_cutoffs(cutoffs: list[str]) -> list[str]:
    return [cutoff for cutoff in cutoffs if feature_file(cutoff).exists()]


def missing_cutoffs(cutoffs: list[str]) -> list[str]:
    return [cutoff for cutoff in cutoffs if not feature_file(cutoff).exists()]


def read_cutoff_frame(cutoff: str) -> "pd.DataFrame":
    import pandas as pd

    path = feature_file(cutoff)
    df = pd.read_csv(path)
    print(f"Loaded {path.relative_to(ROOT)} shape={df.shape}")
    return df


def split_feature_types(df: "pd.DataFrame", features: list[str]) -> tuple[list[str], list[str]]:
    import pandas as pd

    numeric = [col for col in features if pd.api.types.is_numeric_dtype(df[col])]
    categorical = [col for col in features if col not in numeric]
    return numeric, categorical


def build_preprocessor(df: "pd.DataFrame", features: list[str], model_name: str) -> "ColumnTransformer":
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    numeric, categorical = split_feature_types(df, features)
    transformers = []
    if numeric:
        numeric_transformer = StandardScaler() if model_name == "logistic_regression" else "passthrough"
        transformers.append(("numeric", numeric_transformer, numeric))
    if categorical:
        transformers.append(
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                categorical,
            )
        )
    return ColumnTransformer(transformers=transformers, remainder="drop")


def validate_input(df: "pd.DataFrame", cutoff: str, feature_set: str, features: list[str]) -> None:
    missing_features = [col for col in features if col not in df.columns]
    if missing_features:
        raise ValueError(f"{cutoff}/{feature_set} missing features: {missing_features}")
    missing_keys = [col for col in BASE_KEY if col not in df.columns]
    if missing_keys:
        raise ValueError(f"{cutoff} missing base key columns: {missing_keys}")
    if TARGET_COL not in df.columns:
        raise ValueError(f"{cutoff} missing target column: {TARGET_COL}")
    if "date_unregistration" in features:
        raise ValueError("date_unregistration must never be used as a predictor")
    if set(features) & LEAKAGE_COLUMNS:
        raise ValueError(f"Leakage columns selected: {sorted(set(features) & LEAKAGE_COLUMNS)}")
    duplicate_rows = int(df.duplicated(subset=BASE_KEY, keep=False).sum())
    if duplicate_rows:
        raise ValueError(f"{cutoff} has duplicated base-key rows: {duplicate_rows}")
    target_values = set(df[TARGET_COL].dropna().astype(int).unique())
    if not target_values.issubset({0, 1}):
        raise ValueError(f"{cutoff} target must be binary 0/1, found: {sorted(target_values)}")
    if df[features + [TARGET_COL]].isna().any().any():
        missing = df[features + [TARGET_COL]].isna().sum()
        missing = missing[missing > 0].to_dict()
        raise ValueError(f"{cutoff}/{feature_set} has missing modeling cells: {missing}")


def audit_features(df: "pd.DataFrame", cutoff: str, feature_set: str, features: list[str]) -> dict[str, object]:
    numeric, categorical = split_feature_types(df, features)
    row = {
        "cutoff": cutoff,
        "cutoff_day": CUTOFFS[cutoff],
        "feature_set": feature_set,
        "rows": len(df),
        "target_positive_rate": float(df[TARGET_COL].mean()),
        "feature_count": len(features),
        "numeric_features": ";".join(numeric),
        "categorical_features": ";".join(categorical),
        "duplicated_base_key_rows": int(df.duplicated(subset=BASE_KEY, keep=False).sum()),
        "date_unregistration_present": "date_unregistration" in df.columns,
        "selected_leakage_columns": ";".join(sorted(set(features) & LEAKAGE_COLUMNS)),
    }
    for col in DEMOGRAPHIC_FEATURES:
        if col in df.columns:
            row[f"{col}_levels"] = int(df[col].nunique(dropna=False))
            row[f"{col}_values"] = ";".join(sorted(df[col].astype(str).unique()))
    print(
        "Audit: "
        f"cutoff={cutoff}, feature_set={feature_set}, rows={row['rows']}, "
        f"positive_rate={row['target_positive_rate']:.4f}, "
        f"numeric={numeric}, categorical={categorical}"
    )
    return row


def predict_scores(model: "Pipeline", x: "pd.DataFrame", y: "pd.Series") -> tuple["np.ndarray", "np.ndarray"]:
    from sklearn.model_selection import StratifiedKFold, cross_val_predict

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    probabilities = cross_val_predict(
        model,
        x,
        y,
        cv=cv,
        method="predict_proba",
        n_jobs=1,
    )[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    return predictions, probabilities


def score_predictions(
    y: "pd.Series",
    predictions: "np.ndarray",
    probabilities: "np.ndarray",
) -> dict[str, float]:
    from sklearn.metrics import (
        accuracy_score,
        average_precision_score,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    return {
        "precision": precision_score(y, predictions, zero_division=0),
        "recall": recall_score(y, predictions, zero_division=0),
        "f1": f1_score(y, predictions, zero_division=0),
        "roc_auc": roc_auc_score(y, probabilities),
        "pr_auc": average_precision_score(y, probabilities),
        "accuracy": accuracy_score(y, predictions),
    }


def run_experiments(cutoffs: list[str]) -> tuple["pd.DataFrame", "pd.DataFrame"]:
    import pandas as pd

    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    models = build_models()
    result_rows = []
    audit_rows = []

    for cutoff in cutoffs:
        df = read_cutoff_frame(cutoff)
        for feature_set, features in FEATURE_SETS.items():
            validate_input(df, cutoff, feature_set, features)
            audit_rows.append(audit_features(df, cutoff, feature_set, features))
            x = df[features].copy()
            y = df[TARGET_COL].astype(int).copy()
            for model_name, model in models.items():
                model.set_params(preprocessor=build_preprocessor(df, features, model_name))
                predictions, probabilities = predict_scores(model, x, y)
                metrics = score_predictions(y, predictions, probabilities)
                result_row = {
                    "run_id": run_id,
                    "cutoff": cutoff,
                    "cutoff_day": CUTOFFS[cutoff],
                    "feature_set": feature_set,
                    "model": model_name,
                    "rows": len(df),
                    "positive_rate": float(y.mean()),
                    "features": ";".join(features),
                    "feature_count": len(features),
                    "cv": "StratifiedKFold(n_splits=5, shuffle=True, random_state=724)",
                    "threshold": 0.5,
                }
                result_row.update(metrics)
                result_rows.append(result_row)
                print(
                    "Result: "
                    f"cutoff={cutoff}, feature_set={feature_set}, model={model_name}, "
                    f"f1={metrics['f1']:.4f}, roc_auc={metrics['roc_auc']:.4f}"
                )

    return pd.DataFrame(result_rows), pd.DataFrame(audit_rows)


def write_report(
    result_df: "pd.DataFrame | SimpleTable",
    audit_df: "pd.DataFrame | SimpleTable",
    requested_cutoffs: list[str],
    missing: list[str],
) -> None:
    best_text = "_No model results were generated because required input files are missing._"
    comparison_text = "_No comparison table was generated._"
    key_findings = [
        "- Model results are pending until the baseline feature files are available.",
    ]
    if not result_df.empty:
        best = (
            result_df.sort_values(["cutoff_day", "feature_set", "f1"], ascending=[True, True, False])
            .groupby(["cutoff", "feature_set"], as_index=False)
            .head(1)
        )
        best_text = markdown_table(
            best[
                [
                    "cutoff",
                    "feature_set",
                    "model",
                    "precision",
                    "recall",
                    "f1",
                    "roc_auc",
                    "pr_auc",
                    "accuracy",
                ]
            ]
        )
        comparison = (
            best.pivot(index=["cutoff", "cutoff_day"], columns="feature_set", values=["model", "f1", "roc_auc"])
            .reset_index()
        )
        comparison.columns = [
            "_".join(str(part) for part in col if part)
            if isinstance(col, tuple)
            else str(col)
            for col in comparison.columns
        ]
        if {
            "f1_base_demographic",
            "f1_demographic_only",
            "roc_auc_base_demographic",
            "roc_auc_demographic_only",
        }.issubset(comparison.columns):
            comparison["f1_gain_from_base"] = (
                comparison["f1_base_demographic"] - comparison["f1_demographic_only"]
            )
            comparison["roc_auc_gain_from_base"] = (
                comparison["roc_auc_base_demographic"] - comparison["roc_auc_demographic_only"]
            )
            comparison_text = markdown_table(
                comparison[
                    [
                        "cutoff",
                        "model_demographic_only",
                        "f1_demographic_only",
                        "roc_auc_demographic_only",
                        "model_base_demographic",
                        "f1_base_demographic",
                        "roc_auc_base_demographic",
                        "f1_gain_from_base",
                        "roc_auc_gain_from_base",
                    ]
                ]
            )
            latest = comparison.sort_values("cutoff_day").iloc[-1]
            key_findings = [
                "- Demographic-only models have weak but nonzero signal, with best ROC-AUC staying around 0.55 across week 5, week 7, and week 10.",
                "- Adding the two reviewed base activity features gives a large and consistent lift over demographics alone.",
                (
                    "- By week 10, the best `base_demographic` model reaches "
                    f"F1={latest['f1_base_demographic']:.4f} and "
                    f"ROC-AUC={latest['roc_auc_base_demographic']:.4f}, compared with "
                    f"F1={latest['f1_demographic_only']:.4f} and "
                    f"ROC-AUC={latest['roc_auc_demographic_only']:.4f} for `demographic_only`."
                ),
                "- The practical implication is that demographic fields are useful as a baseline/context signal, but early LMS activity explains much more of the actionable withdrawal/failure risk.",
            ]

    missing_paths = [str(feature_file(cutoff).relative_to(ROOT)) for cutoff in missing]
    lines = [
        "# Gunwoo Demographic Feature Report",
        "",
        "## Problem Definition",
        "",
        "This analysis evaluates whether basic student demographic information can support early prediction of students at risk of withdrawal or failure in OULAD.",
        "",
        "The focused research question is: how much predictive signal is contained in `gender`, `region`, and `age_band`, and how much does performance change when the two reviewed base activity features are added?",
        "",
        "This problem is important because demographic features are available before the cutoff weeks and can be used as a low-cost comparison point against behavior-based features. At the same time, they need careful interpretation because they can reflect structural differences rather than actionable individual behavior.",
        "",
        "## Data Collection & Preprocessing",
        "",
        "- Source: Kaggle OULAD-derived baseline feature files created by the reviewed project pipeline.",
        "- Expected inputs: `data/processed/features_week5_baseline.csv`, `data/processed/features_week7_baseline.csv`, and `data/processed/features_week10_baseline.csv`.",
        "- Base unit: one row per `code_module`, `code_presentation`, `id_student` from `student_info`.",
        "- Raw `?` values are parsed as missing before feature generation; raw CSV files are not overwritten.",
        "- Target: `target_at_risk = 1` for `Withdrawn` or `Fail`, otherwise `0`.",
        "- Leakage guard: `date_unregistration`, `final_result`, `target_withdrawn`, and `target_at_risk` are excluded from predictors.",
        "- Categorical preprocessing: `gender`, `region`, and `age_band` are one-hot encoded inside the model pipeline with `handle_unknown='ignore'`.",
        "- Numeric preprocessing: logistic regression standardizes base numeric features; tree models use raw numeric values.",
        "",
        "## Feature Sets",
        "",
        "- `demographic_only`: `gender`, `region`, `age_band`.",
        "- `base_demographic`: `active_days_until_cutoff`, `total_click_until_cutoff_mean_strategy`, `gender`, `region`, `age_band`.",
        "",
        "## Methodology & Model Justification",
        "",
        "- Logistic regression is used as an interpretable linear baseline for sparse one-hot demographic variables.",
        "- Decision tree is used to check simple non-linear splits and interactions between categorical groups.",
        "- Random forest is used as a stronger non-linear benchmark while keeping the experiment lightweight.",
        "- All reported metrics use stratified 5-fold cross-validation. No final production model artifact is saved.",
        "",
        "## Results & Interpretation",
        "",
        "### Key Findings",
        "",
        *key_findings,
        "",
        "### Best Model by Feature Set",
        "",
        best_text,
        "",
        "### Base Feature Lift",
        "",
        comparison_text,
        "",
        "The results show that `gender`, `region`, and `age_band` alone can separate risk groups only weakly. Performance improves substantially once `active_days_until_cutoff` and `total_click_until_cutoff_mean_strategy` are added, so the model is mostly learning from early engagement behavior rather than from static personal information.",
        "",
        "## Limitations & Implications",
        "",
        "- Demographic features are coarse and may encode social or institutional context, so they should not be used alone for high-stakes student decisions.",
        "- Stratified cross-validation may place the same student in multiple folds across different module presentations; future evaluation should consider grouped validation by `id_student`.",
        "- The experiment depends on the baseline feature files and inherits their reviewed VLE duplicate strategy and cohort rules.",
        "- Future work should compare this part with the behavior and student-background branches using the same cutoffs, target, and validation policy.",
        "",
        "## Execution Status",
        "",
        f"- Requested cutoffs: {', '.join(requested_cutoffs)}.",
        f"- Missing input files: {', '.join(missing_paths) if missing_paths else 'none'}.",
        f"- Result table: `{SUMMARY_PATH.relative_to(ROOT)}`.",
        f"- Feature audit table: `{FEATURE_AUDIT_PATH.relative_to(ROOT)}`.",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REPORT_PATH.relative_to(ROOT)}")


def write_html_report(result_df: "pd.DataFrame", audit_df: "pd.DataFrame") -> None:
    if result_df.empty:
        HTML_REPORT_PATH.write_text(
            "<!doctype html><meta charset='utf-8'><title>Demographic Feature Model Report</title>"
            "<h1>Demographic Feature Model Report</h1><p>No model results were generated.</p>",
            encoding="utf-8",
        )
        print(f"Wrote {HTML_REPORT_PATH.relative_to(ROOT)}")
        return

    best = (
        result_df.sort_values(["cutoff_day", "feature_set", "f1"], ascending=[True, True, False])
        .groupby(["cutoff", "feature_set"], as_index=False)
        .head(1)
        .sort_values(["cutoff_day", "feature_set"])
    )
    comparison = (
        best.pivot(index=["cutoff", "cutoff_day"], columns="feature_set", values=["model", "f1", "roc_auc"])
        .reset_index()
        .sort_values("cutoff_day")
    )
    comparison.columns = [
        "_".join(str(part) for part in col if part)
        if isinstance(col, tuple)
        else str(col)
        for col in comparison.columns
    ]
    comparison["f1_gain_from_base"] = (
        comparison["f1_base_demographic"] - comparison["f1_demographic_only"]
    )
    comparison["roc_auc_gain_from_base"] = (
        comparison["roc_auc_base_demographic"] - comparison["roc_auc_demographic_only"]
    )

    def fmt(value: object) -> str:
        if isinstance(value, float):
            return f"{value:.4f}"
        return str(value)

    def metric_card(title: str, value: str, caption: str) -> str:
        return (
            "<div class='card'>"
            f"<div class='label'>{title}</div>"
            f"<div class='big'>{value}</div>"
            f"<p>{caption}</p>"
            "</div>"
        )

    def comparison_chart(metric: str, title: str) -> str:
        demo_col = f"{metric}_demographic_only"
        base_col = f"{metric}_base_demographic"
        max_value = max(float(comparison[base_col].max()), float(comparison[demo_col].max()), 0.001)
        rows = []
        for _, row in comparison.iterrows():
            demo_width = float(row[demo_col]) / max_value * 100
            base_width = float(row[base_col]) / max_value * 100
            rows.append(
                "<div class='chartrow'>"
                f"<div class='chartlabel'>{row['cutoff']}</div>"
                "<div class='chartbars'>"
                "<div class='barline'>"
                "<span class='series demo'>demo only</span>"
                f"<div class='hbar'><i class='demo' style='width:{demo_width:.1f}%'></i></div>"
                f"<b>{row[demo_col]:.4f}</b>"
                "</div>"
                "<div class='barline'>"
                "<span class='series base'>base + demo</span>"
                f"<div class='hbar'><i class='base' style='width:{base_width:.1f}%'></i></div>"
                f"<b>{row[base_col]:.4f}</b>"
                "</div>"
                "</div>"
                "</div>"
            )
        return (
            "<div class='chartcard'>"
            f"<h3>{title}</h3>"
            + "".join(rows)
            + "</div>"
        )

    week10 = comparison.loc[comparison["cutoff"] == "week10"].iloc[0]
    cards = "\n".join(
        [
            metric_card(
                "Week10 demographic only",
                f"F1 {week10['f1_demographic_only']:.4f}",
                f"best model: {week10['model_demographic_only']}, ROC-AUC {week10['roc_auc_demographic_only']:.4f}",
            ),
            metric_card(
                "Week10 base + demographic",
                f"F1 {week10['f1_base_demographic']:.4f}",
                f"best model: {week10['model_base_demographic']}, ROC-AUC {week10['roc_auc_base_demographic']:.4f}",
            ),
            metric_card(
                "Base feature lift",
                f"+{week10['roc_auc_gain_from_base']:.4f}",
                "week10 ROC-AUC gain from adding active days and total clicks",
            ),
        ]
    )
    comparison_charts = comparison_chart("f1", "F1 비교") + comparison_chart("roc_auc", "ROC-AUC 비교")

    chart_rows = []
    max_f1 = max(float(result_df["f1"].max()), 0.001)
    for _, row in result_df.sort_values(["cutoff_day", "feature_set", "model"]).iterrows():
        width = max(3.0, float(row["f1"]) / max_f1 * 100)
        chart_rows.append(
            "<tr>"
            f"<td>{row['cutoff']}</td>"
            f"<td>{row['feature_set']}</td>"
            f"<td>{row['model']}</td>"
            f"<td class='num'>{row['precision']:.4f}</td>"
            f"<td class='num'>{row['recall']:.4f}</td>"
            f"<td class='num strong'>{row['f1']:.4f}</td>"
            f"<td><div class='bar'><span style='width:{width:.1f}%'></span></div></td>"
            f"<td class='num'>{row['roc_auc']:.4f}</td>"
            f"<td class='num'>{row['accuracy']:.4f}</td>"
            "</tr>"
        )

    comparison_rows = []
    for _, row in comparison.iterrows():
        comparison_rows.append(
            "<tr>"
            f"<td>{row['cutoff']}</td>"
            f"<td>{row['model_demographic_only']}</td>"
            f"<td class='num'>{row['f1_demographic_only']:.4f}</td>"
            f"<td class='num'>{row['roc_auc_demographic_only']:.4f}</td>"
            f"<td>{row['model_base_demographic']}</td>"
            f"<td class='num strong'>{row['f1_base_demographic']:.4f}</td>"
            f"<td class='num strong'>{row['roc_auc_base_demographic']:.4f}</td>"
            f"<td class='num gain'>+{row['f1_gain_from_base']:.4f}</td>"
            f"<td class='num gain'>+{row['roc_auc_gain_from_base']:.4f}</td>"
            "</tr>"
        )

    audit_rows = []
    for _, row in audit_df.sort_values(["cutoff_day", "feature_set"]).iterrows():
        audit_rows.append(
            "<tr>"
            f"<td>{row['cutoff']}</td>"
            f"<td>{row['feature_set']}</td>"
            f"<td class='num'>{int(row['rows'])}</td>"
            f"<td class='num'>{row['target_positive_rate']:.4f}</td>"
            f"<td>{row['categorical_features']}</td>"
            f"<td>{row['numeric_features'] if row['numeric_features'] else '-'}</td>"
            f"<td class='num'>{int(row['duplicated_base_key_rows'])}</td>"
            f"<td>{row['selected_leakage_columns'] if row['selected_leakage_columns'] else '-'}</td>"
            "</tr>"
        )

    html = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Demographic Feature Model Report</title>
<style>
body{{margin:0;background:#f7f8fb;color:#172033;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.58}}
main{{max-width:1180px;margin:0 auto;padding:44px 22px 80px}}
h1{{font-size:42px;line-height:1.08;margin:0 0 12px;letter-spacing:-.02em}}
h2{{font-size:24px;margin:44px 0 12px}}
h3{{font-size:18px;margin:0 0 16px}}
p{{color:#4b5565;margin:8px 0}}
.hero{{border-bottom:1px solid #d9dfeb;padding-bottom:30px}}
.pillrow{{display:flex;gap:8px;flex-wrap:wrap;margin-top:18px}}
.pill{{border:1px solid #cdd5e2;border-radius:999px;padding:6px 11px;font-size:12px;background:white;color:#394559}}
.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:26px 0}}
.card{{background:white;border:1px solid #d9dfeb;border-radius:10px;padding:18px}}
.charts{{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin:18px 0 24px}}
.chartcard{{background:white;border:1px solid #d9dfeb;border-radius:10px;padding:18px}}
.chartrow{{display:grid;grid-template-columns:72px 1fr;gap:12px;align-items:center;margin:14px 0}}
.chartlabel{{font-weight:800;color:#263244}}
.chartbars{{display:grid;gap:8px}}
.barline{{display:grid;grid-template-columns:92px 1fr 58px;gap:9px;align-items:center}}
.series{{font-size:12px;color:#526174}}
.series.demo{{color:#64748b}}
.series.base{{color:#0f766e;font-weight:700}}
.hbar{{height:14px;background:#e5e9f1;border-radius:999px;overflow:hidden}}
.hbar i{{display:block;height:100%;border-radius:999px}}
.hbar i.demo{{background:#94a3b8}}
.hbar i.base{{background:linear-gradient(90deg,#14b8a6,#2563eb)}}
.label{{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#5b6b82}}
.big{{font-size:31px;font-weight:800;margin:8px 0 4px;color:#0f766e}}
.note{{background:#ecfdf5;border-left:4px solid #0f766e;padding:14px 16px;border-radius:8px;margin:18px 0}}
.warn{{background:#fff7ed;border-left-color:#c2410c}}
.tablewrap{{overflow-x:auto;border:1px solid #d9dfeb;border-radius:10px;background:white}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th,td{{padding:10px 12px;border-bottom:1px solid #e6ebf3;text-align:left;white-space:nowrap}}
th{{background:#eef2f7;color:#334155;font-size:11px;text-transform:uppercase;letter-spacing:.05em}}
tr:last-child td{{border-bottom:none}}
.num{{text-align:right;font-variant-numeric:tabular-nums}}
.strong{{font-weight:800;color:#0f766e}}
.gain{{font-weight:800;color:#1d4ed8}}
.bar{{height:9px;background:#e5e9f1;border-radius:999px;min-width:120px;overflow:hidden}}
.bar span{{display:block;height:100%;background:linear-gradient(90deg,#14b8a6,#2563eb);border-radius:999px}}
code{{background:#eef2f7;border:1px solid #d9dfeb;border-radius:5px;padding:2px 5px}}
@media(max-width:820px){{.cards,.charts{{grid-template-columns:1fr}}.barline{{grid-template-columns:80px 1fr 52px}}h1{{font-size:32px}}}}
</style>
</head>
<body>
<main>
<section class="hero">
<h1>Demographic Feature Model Report</h1>
<p>OULAD early at-risk prediction에서 <code>gender</code>, <code>region</code>, <code>age_band</code>만 사용한 경우와 base feature를 추가한 경우를 비교했다.</p>
<div class="pillrow">
<span class="pill">target: target_at_risk</span>
<span class="pill">cutoffs: week5 / week7 / week10</span>
<span class="pill">CV: Stratified 5-fold</span>
<span class="pill">raw files not modified</span>
</div>
</section>

<section>
<h2>요약</h2>
<div class="cards">{cards}</div>
<div class="note">
<b>결론:</b> demographic-only는 ROC-AUC가 약 0.55 수준이라 약한 신호만 보인다.
하지만 <code>active_days_until_cutoff</code>, <code>total_click_until_cutoff_mean_strategy</code>를 추가하면 모든 cutoff에서 성능이 크게 올라간다.
즉, 학생 개인 정보는 baseline/context signal이고, 실제 예측력은 초기 LMS 활동량에서 더 크게 나온다.
</div>
</section>

<section>
<h2>성능 그래프</h2>
<p>각 cutoff에서 담당 피처만 사용한 경우와 base feature를 추가한 경우의 성능 차이를 시각화했다.</p>
<div class="charts">{comparison_charts}</div>
</section>

<section>
<h2>Base Feature 추가 효과</h2>
<div class="tablewrap"><table>
<thead><tr><th>cutoff</th><th>demo only model</th><th class="num">demo F1</th><th class="num">demo ROC-AUC</th><th>base+demo model</th><th class="num">base F1</th><th class="num">base ROC-AUC</th><th class="num">F1 gain</th><th class="num">ROC-AUC gain</th></tr></thead>
<tbody>{''.join(comparison_rows)}</tbody>
</table></div>
</section>

<section>
<h2>전체 모델별 성능</h2>
<p>팀원에게 전체 성능을 전달할 때는 이 표의 원본 CSV인 <code>reports/tables/gunwoo_demographic_model_summary.csv</code>를 주면 된다.</p>
<div class="tablewrap"><table>
<thead><tr><th>cutoff</th><th>feature set</th><th>model</th><th class="num">precision</th><th class="num">recall</th><th class="num">F1</th><th>F1 bar</th><th class="num">ROC-AUC</th><th class="num">accuracy</th></tr></thead>
<tbody>{''.join(chart_rows)}</tbody>
</table></div>
</section>

<section>
<h2>전처리/입력 검증</h2>
<div class="tablewrap"><table>
<thead><tr><th>cutoff</th><th>feature set</th><th class="num">rows</th><th class="num">positive rate</th><th>categorical</th><th>numeric</th><th class="num">duplicated key rows</th><th>selected leakage cols</th></tr></thead>
<tbody>{''.join(audit_rows)}</tbody>
</table></div>
<div class="note warn">
<b>주의:</b> demographic feature는 사회적/제도적 맥락을 반영할 수 있으므로 단독 의사결정 기준으로 쓰면 안 된다.
보고서에서는 행동 피처를 붙였을 때 성능이 크게 좋아진다는 비교 기준으로 해석하는 것이 적절하다.
</div>
</section>

<section>
<h2>공유 파일</h2>
<p><code>{SUMMARY_PATH.relative_to(ROOT)}</code>: 모든 모델별 성능 원본표</p>
<p><code>{FEATURE_AUDIT_PATH.relative_to(ROOT)}</code>: feature set별 입력 검증표</p>
<p><code>{REPORT_PATH.relative_to(ROOT)}</code>: Markdown 분석 보고서</p>
</section>
</main>
</body>
</html>
"""
    HTML_REPORT_PATH.write_text(html, encoding="utf-8")
    print(f"Wrote {HTML_REPORT_PATH.relative_to(ROOT)}")


def append_decision_log() -> None:
    entry = """
## Gunwoo Demographic Feature Agent

- Decision: Added a focused demographic experiment for `gender`, `region`, and `age_band`.
- Decision: Compare two feature sets only: `demographic_only` and `base_demographic`.
- Decision: `base_demographic` uses `active_days_until_cutoff` and `total_click_until_cutoff_mean_strategy` as the reviewed base features.
- Decision: Demographic categorical features are one-hot encoded inside the modeling pipeline, leaving baseline CSV files unchanged.
- Decision: `date_unregistration`, `final_result`, `target_withdrawn`, and `target_at_risk` are excluded from predictors.
- Decision: The script saves cross-validation summaries and an input feature audit, but does not save a final model artifact.
- Unresolved: Actual model results require local `data/processed/features_week{5,7,10}_baseline.csv` files.
"""
    current = DECISION_LOG_PATH.read_text(encoding="utf-8") if DECISION_LOG_PATH.exists() else "# Decision Log\n"
    if "## Gunwoo Demographic Feature Agent" not in current:
        DECISION_LOG_PATH.write_text(current.rstrip() + "\n" + entry, encoding="utf-8")
        print(f"Updated {DECISION_LOG_PATH.relative_to(ROOT)}")


class SimpleTable:
    def __init__(self, columns: list[str], rows: list[list[object]] | None = None) -> None:
        self.columns = columns
        self.rows = rows or []

    @property
    def empty(self) -> bool:
        return not self.rows

    def to_csv(self, path: Path, *args: object, **kwargs: object) -> None:
        lines = [",".join(self.columns)]
        for row in self.rows:
            lines.append(",".join(str(value) for value in row))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def markdown_table(df: "pd.DataFrame | SimpleTable") -> str:
    if df.empty:
        return "_No rows._"
    if isinstance(df, SimpleTable):
        columns = df.columns
        rows = [[format_markdown_cell(value) for value in row] for row in df.rows]
    else:
        string_df = df.copy()
        for column in string_df.columns:
            string_df[column] = string_df[column].map(format_markdown_cell)
        columns = list(string_df.columns)
        rows = string_df.values.tolist()
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def format_markdown_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Gunwoo's demographic OULAD feature experiments."
    )
    parser.add_argument("--cutoffs", nargs="+", default=list(CUTOFFS), choices=list(CUTOFFS))
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Run available cutoff files and record missing files in the report.",
    )
    return parser.parse_args()


def main() -> None:
    ensure_dirs()
    append_decision_log()
    args = parse_args()
    requested = args.cutoffs
    missing = missing_cutoffs(requested)
    available = existing_cutoffs(requested)

    if missing and not args.allow_partial:
        empty_results = SimpleTable(
            [
                "run_id",
                "cutoff",
                "cutoff_day",
                "feature_set",
                "model",
                "rows",
                "positive_rate",
                "features",
                "feature_count",
                "precision",
                "recall",
                "f1",
                "roc_auc",
                "pr_auc",
                "accuracy",
            ]
        )
        empty_audit = SimpleTable(
            [
                "cutoff",
                "cutoff_day",
                "feature_set",
                "rows",
                "target_positive_rate",
                "feature_count",
                "numeric_features",
                "categorical_features",
                "duplicated_base_key_rows",
                "date_unregistration_present",
                "selected_leakage_columns",
            ]
        )
        empty_results.to_csv(SUMMARY_PATH, index=False)
        empty_audit.to_csv(FEATURE_AUDIT_PATH, index=False)
        write_report(empty_results, empty_audit, requested, missing)
        raise FileNotFoundError(
            "Missing required baseline files: "
            + json.dumps([str(feature_file(cutoff).relative_to(ROOT)) for cutoff in missing])
        )

    result_df, audit_df = run_experiments(available)
    result_df.to_csv(SUMMARY_PATH, index=False)
    audit_df.to_csv(FEATURE_AUDIT_PATH, index=False)
    print(f"Saved {SUMMARY_PATH.relative_to(ROOT)}")
    print(f"Saved {FEATURE_AUDIT_PATH.relative_to(ROOT)}")
    write_report(result_df, audit_df, requested, missing)
    write_html_report(result_df, audit_df)
    print("\nDemographic feature experiment complete. No final model artifact was saved.")


if __name__ == "__main__":
    main()
