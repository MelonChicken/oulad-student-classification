from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import (
    GroupShuffleSplit,
    StratifiedGroupKFold,
    StratifiedKFold,
)
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
RESULT_DIR = ROOT / "result"
REPORT_DIR = ROOT / "reports"
FIGURE_DIR = REPORT_DIR / "figures"

RANDOM_STATE = 42
TARGET = "target_at_risk"
GROUP = "id_student"
CUTOFFS = ("week5", "week7", "week10")
EXPECTED_ROWS = {"week5": 27250, "week7": 26788, "week10": 26082}
ROW_TOLERANCE = 100

LEAKAGE_COLUMNS = {
    "date_unregistration",
    "final_result",
    "target_withdrawn",
    "target_at_risk",
    "id_student",
}

CATEGORICAL_COLUMNS = {
    "gender",
    "region",
    "highest_education",
    "age_band",
    "imd_band",
    "disability",
    "credits_bin",
    "prev_attempts_cat",
    "studied_credits_cat",
    "edu_x_attempts",
}

MODEL_ORDER = [
    "DecisionTree",
    "GaussianNB",
    "KNN",
    "LogisticRegression",
    "RandomForest",
    "SVC",
]

FEATURE_SET_ORDER = ["D", "A", "B", "D+A", "D+B", "A+B", "ALL"]

DOMAIN_EXPECTED = {
    "B": [
        "vle_active_days",
        "vle_click_total",
        "asm_count",
        "asm_days_early_mean",
        "vle_disengage",
    ],
    "A": [
        "highest_education",
        "num_of_prev_attempts",
        "credits_bin",
    ],
    "D": ["gender", "region", "age_band"],
}

CONCEPT_TO_COLUMN = {
    "vle_active_days": "active_days_until_cutoff",
    "vle_click_total": "total_click_until_cutoff_mean_strategy",
    "vle_disengage": "days_since_last_activity_at_cutoff",
    "asm_count": "assessment_count_until_cutoff",
    "asm_days_early_mean": "avg_days_before_due_until_cutoff",
    "engagement_rate": "avg_click_per_active_day_until_cutoff_mean_strategy",
    "clicks_per_day": "avg_click_per_active_day_until_cutoff_mean_strategy",
    "mean_score_until_cutoff": "mean_score_until_cutoff",
    "highest_education": "highest_education",
    "num_of_prev_attempts": "num_of_prev_attempts",
    "prev_attempts_cat": "prev_attempts_cat",
    "credits_bin": "credits_bin",
    "studied_credits_cat": "studied_credits_cat",
    "edu_x_attempts": "edu_x_attempts",
    "gender": "gender",
    "region": "region",
    "age_band": "age_band",
    "imd_band": "imd_band",
    "disability": "disability",
}


@dataclass(frozen=True)
class ModelSpec:
    estimator: object
    scale_numeric: bool


def one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def ensure_dirs() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)


def load_cutoff(cutoff: str) -> pd.DataFrame:
    path = PROCESSED_DIR / f"features_{cutoff}_baseline.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path.relative_to(ROOT)}. data/preprocessed was empty; "
            "this script uses existing data/processed baseline CSVs."
        )
    df = pd.read_csv(path)
    df = add_derived_features(df)
    print(f"[LOAD] {path.relative_to(ROOT)} rows={len(df):,} cols={len(df.columns):,}")
    print(f"[COLUMNS:{cutoff}] {list(df.columns)}")
    return df


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    if "studied_credits" in result.columns:
        bins = [-np.inf, 30, 60, 90, 120, np.inf]
        labels = ["<=30", "31-60", "61-90", "91-120", ">120"]
        result["credits_bin"] = pd.cut(result["studied_credits"], bins=bins, labels=labels)
        result["credits_bin"] = result["credits_bin"].astype("object").fillna("Unknown")
        result["studied_credits_cat"] = result["credits_bin"]
    if "num_of_prev_attempts" in result.columns:
        attempts = result["num_of_prev_attempts"].fillna(0)
        result["prev_attempts_cat"] = np.select(
            [
                attempts <= 0,
                attempts == 1,
                attempts == 2,
                attempts >= 3,
            ],
            ["0", "1", "2", "3+"],
            default="Unknown",
        )
    if {"highest_education", "num_of_prev_attempts"}.issubset(result.columns):
        if "prev_attempts_cat" in result.columns:
            attempts = result["prev_attempts_cat"].astype(str)
        else:
            attempts = result["num_of_prev_attempts"].fillna(0).astype(int).astype(str)
        result["edu_x_attempts"] = (
            result["highest_education"].fillna("Unknown").astype(str) + "_attempts_" + attempts
        )
    return result


def validate_frame(df: pd.DataFrame, cutoff: str) -> None:
    missing = [col for col in [TARGET, GROUP] if col not in df.columns]
    if missing:
        raise ValueError(f"{cutoff} missing required columns: {missing}")
    duplicates = int(
        df.duplicated(subset=["code_module", "code_presentation", "id_student"]).sum()
    )
    if duplicates:
        raise ValueError(f"{cutoff} has duplicated student-module-presentation rows: {duplicates}")
    expected = EXPECTED_ROWS[cutoff]
    delta = len(df) - expected
    status = "OK" if abs(delta) <= ROW_TOLERANCE else "CHECK"
    print(
        f"[SANITY:{cutoff}] rows={len(df):,}, expected~{expected:,}, "
        f"delta={delta:+,}, status={status}"
    )
    target_rate = df[TARGET].mean()
    print(f"[TARGET:{cutoff}] at_risk_rate={target_rate:.4f} counts={df[TARGET].value_counts().to_dict()}")


def map_domain_features(df: pd.DataFrame) -> tuple[dict[str, list[str]], list[dict[str, str]]]:
    domains: dict[str, list[str]] = {}
    rows: list[dict[str, str]] = []
    for domain, concepts in DOMAIN_EXPECTED.items():
        mapped: list[str] = []
        for concept in concepts:
            column = CONCEPT_TO_COLUMN[concept]
            status = "found" if column in df.columns else "missing"
            if status == "found":
                mapped.append(column)
            rows.append(
                {
                    "domain": domain,
                    "concept": concept,
                    "column": column,
                    "status": status,
                    "note": "derived in script" if concept in {"credits_bin", "edu_x_attempts"} else "",
                }
            )
        domains[domain] = unique(mapped)
    print("[MAPPING] concept to actual column")
    print(pd.DataFrame(rows).to_string(index=False))
    return domains, rows


def unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def companion_missing_flags(df: pd.DataFrame, features: Iterable[str]) -> list[str]:
    flags = []
    for feature in features:
        flag = f"{feature}_missing"
        if flag in df.columns:
            flags.append(flag)
    return flags


def build_preprocessor(df: pd.DataFrame, features: list[str], scale_numeric: bool) -> ColumnTransformer:
    numeric = [col for col in features if pd.api.types.is_numeric_dtype(df[col])]
    categorical = [col for col in features if col not in numeric]
    transformers = []
    if numeric:
        steps = [("imputer", SimpleImputer(strategy="constant", fill_value=0))]
        if scale_numeric:
            steps.append(("scaler", StandardScaler()))
        transformers.append(("numeric", Pipeline(steps), numeric))
    if categorical:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="constant", fill_value="Unknown")),
                        ("onehot", one_hot_encoder()),
                    ]
                ),
                categorical,
            )
        )
    return ColumnTransformer(transformers=transformers, remainder="drop")


def make_pipeline(df: pd.DataFrame, features: list[str], spec: ModelSpec) -> Pipeline:
    leaked = sorted(set(features) & LEAKAGE_COLUMNS)
    if leaked:
        raise ValueError(f"Leakage columns selected as predictors: {leaked}")
    return Pipeline(
        [
            ("preprocess", build_preprocessor(df, features, spec.scale_numeric)),
            ("model", clone(spec.estimator)),
        ]
    )


def model_specs() -> dict[str, ModelSpec]:
    return {
        "DecisionTree": ModelSpec(
            DecisionTreeClassifier(max_depth=5, min_samples_leaf=20, random_state=RANDOM_STATE),
            False,
        ),
        "GaussianNB": ModelSpec(GaussianNB(), False),
        "KNN": ModelSpec(KNeighborsClassifier(n_neighbors=21), True),
        "LogisticRegression": ModelSpec(
            LogisticRegression(
                max_iter=2000,
                class_weight="balanced",
                solver="lbfgs",
                random_state=RANDOM_STATE,
            ),
            True,
        ),
        "RandomForest": ModelSpec(
            RandomForestClassifier(
                n_estimators=200,
                min_samples_leaf=5,
                max_features="sqrt",
                class_weight="balanced",
                n_jobs=-1,
                random_state=RANDOM_STATE,
            ),
            False,
        ),
        "SVC": ModelSpec(
            SVC(kernel="linear", C=1.0, class_weight="balanced", random_state=RANDOM_STATE),
            True,
        ),
    }


def main_cv(df: pd.DataFrame):
    return StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE).split(
        df, df[TARGET], groups=df[GROUP]
    )


def replication_cv(df: pd.DataFrame):
    return StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE).split(
        df, df[TARGET]
    )


def robustness_cv(df: pd.DataFrame):
    return GroupShuffleSplit(
        n_splits=5, test_size=0.2, random_state=RANDOM_STATE
    ).split(df, df[TARGET], groups=df[GROUP])


def score_vector(estimator: Pipeline, x_test: pd.DataFrame) -> np.ndarray:
    if hasattr(estimator, "predict_proba"):
        return estimator.predict_proba(x_test)[:, 1]
    if hasattr(estimator, "decision_function"):
        return estimator.decision_function(x_test)
    return estimator.predict(x_test)


def fold_metrics(y_true: pd.Series, y_pred: np.ndarray, y_score: np.ndarray) -> dict[str, float]:
    return {
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "f1_macro": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "roc_auc": roc_auc_score(y_true, y_score),
        "pr_auc": average_precision_score(y_true, y_score),
        "accuracy": accuracy_score(y_true, y_pred),
    }


def evaluate_cv(
    df: pd.DataFrame,
    features: list[str],
    model_name: str,
    split_name: str,
    splits,
) -> dict[str, float | str | int]:
    spec = model_specs()[model_name]
    x = df[features]
    y = df[TARGET].astype(int)
    fold_rows = []
    for fold_idx, (train_idx, test_idx) in enumerate(splits, start=1):
        estimator = make_pipeline(df, features, spec)
        estimator.fit(x.iloc[train_idx], y.iloc[train_idx])
        y_pred = estimator.predict(x.iloc[test_idx])
        y_score = score_vector(estimator, x.iloc[test_idx])
        metrics = fold_metrics(y.iloc[test_idx], y_pred, y_score)
        metrics["fold"] = fold_idx
        fold_rows.append(metrics)
    fold_df = pd.DataFrame(fold_rows)
    row: dict[str, float | str | int] = {
        "split": split_name,
        "model": model_name,
        "n_features": len(features),
        "features": ";".join(features),
    }
    for metric in ["precision", "recall", "f1", "f1_macro", "roc_auc", "pr_auc", "accuracy"]:
        row[f"{metric}_mean"] = float(fold_df[metric].mean())
        row[f"{metric}_std"] = float(fold_df[metric].std(ddof=1))
    return row


def cohen_d_numeric(series: pd.Series, target: pd.Series) -> float:
    x0 = series[target == 0].dropna().astype(float)
    x1 = series[target == 1].dropna().astype(float)
    if len(x0) < 2 or len(x1) < 2:
        return np.nan
    pooled = np.sqrt(((len(x0) - 1) * x0.var(ddof=1) + (len(x1) - 1) * x1.var(ddof=1)) / (len(x0) + len(x1) - 2))
    if pooled == 0 or np.isnan(pooled):
        return np.nan
    return float((x1.mean() - x0.mean()) / pooled)


def pearson_numeric(series: pd.Series, target: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce")
    if values.nunique(dropna=True) < 2:
        return np.nan
    return float(values.corr(target))


def single_feature_auc(df: pd.DataFrame, feature: str) -> float:
    row = evaluate_cv(
        df,
        [feature],
        "LogisticRegression",
        "selection_week10_main",
        main_cv(df),
    )
    return float(row["roc_auc_mean"])


def select_domain_features(
    df: pd.DataFrame, domain_candidates: dict[str, list[str]]
) -> tuple[dict[str, list[str]], pd.DataFrame, pd.DataFrame]:
    metric_rows: list[dict[str, object]] = []
    forward_rows: list[dict[str, object]] = []
    selected: dict[str, list[str]] = {}
    y = df[TARGET].astype(int)

    for domain, candidates in domain_candidates.items():
        print(f"[SELECT:{domain}] candidates={candidates}")
        for feature in candidates:
            is_numeric = pd.api.types.is_numeric_dtype(df[feature])
            row = {
                "domain": domain,
                "feature": feature,
                "cohen_d": cohen_d_numeric(df[feature], y) if is_numeric else np.nan,
                "abs_pearson": abs(pearson_numeric(df[feature], y)) if is_numeric else np.nan,
                "single_feature_roc_auc": single_feature_auc(df, feature),
            }
            metric_rows.append(row)

        remaining = candidates.copy()
        chosen: list[str] = []
        baseline_auc = 0.5
        while remaining:
            trials = []
            for feature in remaining:
                trial_features = chosen + [feature]
                auc = float(
                    evaluate_cv(
                        df,
                        trial_features,
                        "LogisticRegression",
                        "forward_week10_main",
                        main_cv(df),
                    )["roc_auc_mean"]
                )
                trials.append((feature, auc, auc - baseline_auc))
            best_feature, best_auc, delta = max(trials, key=lambda item: item[1])
            accepted = delta >= 0.005
            forward_rows.append(
                {
                    "domain": domain,
                    "step": len(chosen) + 1,
                    "feature": best_feature,
                    "roc_auc": best_auc,
                    "delta_auc": delta,
                    "accepted": accepted,
                }
            )
            print(
                f"[FORWARD:{domain}] step={len(chosen)+1} feature={best_feature} "
                f"auc={best_auc:.4f} delta={delta:.4f} accepted={accepted}"
            )
            remaining.remove(best_feature)
            if not accepted:
                break
            chosen.append(best_feature)
            baseline_auc = best_auc

        final = candidates.copy()
        selected[domain] = final
        print(f"[SELECT:{domain}] fixed_selected={final}")

    return selected, pd.DataFrame(metric_rows), pd.DataFrame(forward_rows)


def feature_sets_from_domains(selected: dict[str, list[str]]) -> dict[str, list[str]]:
    return {
        "D": selected["D"],
        "A": selected["A"],
        "B": selected["B"],
        "D+A": unique(selected["D"] + selected["A"]),
        "D+B": unique(selected["D"] + selected["B"]),
        "A+B": unique(selected["A"] + selected["B"]),
        "ALL": unique(selected["D"] + selected["A"] + selected["B"]),
    }


def run_ablation(
    frames: dict[str, pd.DataFrame],
    feature_sets: dict[str, list[str]],
    smoke_only: bool,
    skip_svc: bool,
) -> pd.DataFrame:
    rows = []
    print("[SMOKE] week10 ALL RandomForest MAIN")
    smoke = evaluate_cv(
        frames["week10"],
        feature_sets["ALL"],
        "RandomForest",
        "MAIN",
        main_cv(frames["week10"]),
    )
    smoke.update({"cutoff": "week10", "feature_set": "ALL"})
    rows.append(smoke)
    print(f"[SMOKE] roc_auc={smoke['roc_auc_mean']:.4f} f1={smoke['f1_mean']:.4f}")
    if smoke_only:
        return pd.DataFrame(rows)

    models = [m for m in MODEL_ORDER if not (skip_svc and m == "SVC")]
    for cutoff in CUTOFFS:
        for feature_set_name in FEATURE_SET_ORDER:
            features = feature_sets[feature_set_name]
            for model_name in models:
                if cutoff == "week10" and feature_set_name == "ALL" and model_name == "RandomForest":
                    continue
                print(f"[MAIN] cutoff={cutoff} set={feature_set_name} model={model_name}")
                row = evaluate_cv(
                    frames[cutoff],
                    features,
                    model_name,
                    "MAIN",
                    main_cv(frames[cutoff]),
                )
                row.update({"cutoff": cutoff, "feature_set": feature_set_name})
                rows.append(row)

    main_df = pd.DataFrame(rows)
    top_main = (
        main_df[main_df["split"] == "MAIN"]
        .sort_values(["roc_auc_mean", "f1_mean"], ascending=False)
        .head(1)
        .iloc[0]
    )
    extra_jobs = [
        ("REPLICATION", top_main["cutoff"], top_main["feature_set"], top_main["model"]),
        ("ROBUSTNESS", top_main["cutoff"], top_main["feature_set"], top_main["model"]),
        ("REPLICATION", "week10", "ALL", "RandomForest"),
        ("ROBUSTNESS", "week10", "ALL", "RandomForest"),
    ]
    for split_name, cutoff, feature_set_name, model_name in unique_tuples(extra_jobs):
        print(f"[{split_name}] cutoff={cutoff} set={feature_set_name} model={model_name}")
        split_iter = (
            replication_cv(frames[cutoff])
            if split_name == "REPLICATION"
            else robustness_cv(frames[cutoff])
        )
        row = evaluate_cv(
            frames[cutoff],
            feature_sets[feature_set_name],
            model_name,
            split_name,
            split_iter,
        )
        row.update({"cutoff": cutoff, "feature_set": feature_set_name})
        rows.append(row)
    return pd.DataFrame(rows)


def unique_tuples(values: Iterable[tuple]) -> list[tuple]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def make_summary(results: pd.DataFrame) -> pd.DataFrame:
    main = results[results["split"] == "MAIN"].copy()
    return (
        main.sort_values(["feature_set", "cutoff", "roc_auc_mean", "f1_mean"], ascending=[True, True, False, False])
        .groupby(["feature_set", "cutoff"], as_index=False)
        .head(1)
        .sort_values(["cutoff", "feature_set"])
    )


def make_paper_comparison(results: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "model",
        "paper",
        "paper_week7_roc_auc",
        "our_week7_best_feature_set",
        "our_week7_roc_auc_mean",
        "our_week7_roc_auc_std",
        "delta_roc_auc",
    ]
    paper_roc = {
        "DecisionTree": 0.68,
        "GaussianNB": 0.66,
        "RandomForest": 0.77,
        "SVC": 0.72,
        "KNN": 0.64,
    }
    rows = []
    week7 = results[(results["split"] == "MAIN") & (results["cutoff"] == "week7")]
    for model, paper_value in paper_roc.items():
        ours = week7[week7["model"] == model].sort_values(
            ["roc_auc_mean", "f1_mean"], ascending=False
        )
        if ours.empty:
            continue
        best = ours.iloc[0]
        rows.append(
            {
                "model": model,
                "paper": "Staneviciene 2024 week7",
                "paper_week7_roc_auc": paper_value,
                "our_week7_best_feature_set": best["feature_set"],
                "our_week7_roc_auc_mean": best["roc_auc_mean"],
                "our_week7_roc_auc_std": best["roc_auc_std"],
                "delta_roc_auc": best["roc_auc_mean"] - paper_value,
            }
        )
    return pd.DataFrame(rows, columns=columns)


def write_permutation_importance(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    model_name = "RandomForest"
    estimator = make_pipeline(df, features, model_specs()[model_name])
    x = df[features]
    y = df[TARGET].astype(int)
    estimator.fit(x, y)
    importance = permutation_importance(
        estimator,
        x,
        y,
        scoring="roc_auc",
        n_repeats=5,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    result = pd.DataFrame(
        {
            "cutoff": "week10",
            "feature_set": "ALL",
            "model": model_name,
            "feature": features,
            "importance_mean": importance.importances_mean,
            "importance_std": importance.importances_std,
        }
    ).sort_values("importance_mean", ascending=False)
    result.to_csv(RESULT_DIR / "feature_importance.csv", index=False)
    return result


def write_selected_json(
    selected: dict[str, list[str]],
    mapping_rows: list[dict[str, str]],
    metrics: pd.DataFrame,
    forward: pd.DataFrame,
) -> None:
    payload = {
        "random_state": RANDOM_STATE,
        "selection_data": "week10",
        "selection_split": "StratifiedGroupKFold by id_student",
        "rule": "Domain feature sets fixed by team decision; week10 Cohen's D, Pearson correlation, single-feature ROC-AUC, and forward-selection metrics are recorded as supporting evidence.",
        "selected_features": selected,
        "concept_mapping": mapping_rows,
        "single_feature_metrics": metrics.to_dict(orient="records"),
        "forward_selection": forward.to_dict(orient="records"),
    }
    (RESULT_DIR / "selected_features.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def write_report(results: pd.DataFrame, selected: dict[str, list[str]], importance: pd.DataFrame) -> None:
    main = results[results["split"] == "MAIN"].sort_values(
        ["roc_auc_mean", "f1_mean"], ascending=False
    )
    best = main.iloc[0]
    top_features = ", ".join(importance.head(5)["feature"].tolist()) if not importance.empty else "not computed"
    lines = [
        "# Integrated Domain Ablation Report",
        "",
        "- The unit of prediction is a student-module-presentation registration. Since some students appear in multiple module presentations, the main evaluation uses student-level grouped splitting to prevent the same student from appearing in both training and test sets.",
        f"- Best MAIN result by ROC-AUC: {best['model']} / {best['feature_set']} / {best['cutoff']} with ROC-AUC {best['roc_auc_mean']:.3f} +/- {best['roc_auc_std']:.3f} and F1 {best['f1_mean']:.3f}.",
        f"- Selected demographic features: {', '.join(selected['D'])}.",
        f"- Selected academic-background features: {', '.join(selected['A'])}.",
        f"- Selected behavioral features: {', '.join(selected['B'])}.",
        f"- Week10 ALL permutation importance is led by: {top_features}.",
        "- Recommended model should prioritize ROC-AUC first and F1 second; use MAIN split values for presentation and REPLICATION/ROBUSTNESS only as supporting checks.",
        "- Limitation: SVC uses a linear kernel for tractable repeated grouped CV on this data size; no final production model artifact is saved.",
        "",
    ]
    (REPORT_DIR / "integrated_report.md").write_text("\n".join(lines), encoding="utf-8")


def write_plot(results: pd.DataFrame) -> None:
    main = results[results["split"] == "MAIN"].copy()
    if main.empty:
        return
    best_by_set = (
        main.sort_values(["cutoff", "feature_set", "roc_auc_mean", "f1_mean"], ascending=[True, True, False, False])
        .groupby(["cutoff", "feature_set"], as_index=False)
        .head(1)
    )
    order_index = {name: i for i, name in enumerate(FEATURE_SET_ORDER)}
    plt.figure(figsize=(10, 5))
    for cutoff in CUTOFFS:
        part = best_by_set[best_by_set["cutoff"] == cutoff].copy()
        part["order"] = part["feature_set"].map(order_index)
        part = part.sort_values("order")
        plt.plot(part["feature_set"], part["roc_auc_mean"], marker="o", label=cutoff)
    plt.xlabel("Feature set")
    plt.ylabel("Best MAIN ROC-AUC")
    plt.ylim(0.5, 1.0)
    plt.grid(axis="y", alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "domain_ablation_roc_auc.png", dpi=160)
    plt.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Integrated OULAD domain feature selection and ablation.")
    parser.add_argument("--smoke-only", action="store_true", help="Run only week10 ALL RandomForest MAIN.")
    parser.add_argument("--skip-svc", action="store_true", help="Skip SVC in the full matrix if runtime is constrained.")
    parser.add_argument("--no-importance", action="store_true", help="Skip permutation importance.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_dirs()
    frames = {cutoff: load_cutoff(cutoff) for cutoff in CUTOFFS}
    for cutoff, df in frames.items():
        validate_frame(df, cutoff)

    domain_candidates, mapping_rows = map_domain_features(frames["week10"])
    selected, metrics, forward = select_domain_features(frames["week10"], domain_candidates)
    metrics.to_csv(RESULT_DIR / "feature_selection_metrics_week10.csv", index=False)
    forward.to_csv(RESULT_DIR / "feature_forward_selection_week10.csv", index=False)
    write_selected_json(selected, mapping_rows, metrics, forward)

    feature_sets = feature_sets_from_domains(selected)
    for name, features in feature_sets.items():
        leaked = sorted(set(features) & LEAKAGE_COLUMNS)
        if leaked:
            raise ValueError(f"{name} contains leakage predictors: {leaked}")
        print(f"[FEATURE_SET] {name}: {features}")

    results = run_ablation(frames, feature_sets, args.smoke_only, args.skip_svc)
    results = results.sort_values(["split", "cutoff", "feature_set", "model"])
    results.to_csv(RESULT_DIR / "results_integrated.csv", index=False)
    summary = make_summary(results)
    summary.to_csv(RESULT_DIR / "domain_ablation_summary.csv", index=False)
    comparison = make_paper_comparison(results)
    comparison.to_csv(RESULT_DIR / "paper_comparison_week7.csv", index=False)

    importance = pd.DataFrame()
    if not args.no_importance and not args.smoke_only:
        importance = write_permutation_importance(frames["week10"], feature_sets["ALL"])
    elif not args.no_importance:
        print("[IMPORTANCE] skipped because --smoke-only was used")

    write_plot(results)
    write_report(results, selected, importance)
    print(f"[DONE] wrote outputs under {RESULT_DIR.relative_to(ROOT)} and {REPORT_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
