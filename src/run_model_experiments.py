from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, make_scorer, precision_score, recall_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
RESULT_DIR = ROOT / "data" / "report_tables" / "model_results"
REPORT_DIR = ROOT / "reports"
REPORT_TABLE_DIR = REPORT_DIR / "tables"

ALL_RESULTS_PATH = RESULT_DIR / "feature_engineering_grid_results.csv"
BEST_RESULTS_PATH = RESULT_DIR / "feature_engineering_best_results.csv"
REPORT_PATH = REPORT_DIR / "model_experiment_logging_report.md"

RANDOM_STATE = 724
CUTOFFS = ["week5", "week7", "week10"]
STRATEGY = "mean"
TARGET_COL = "target_at_risk"
POSITIVE_CLASS_NAME = "at_risk"

BASE_KEY = ["code_module", "code_presentation", "id_student"]
ALWAYS_EXCLUDE = {
    *BASE_KEY,
    "final_result",
    "target_withdrawn",
    "target_at_risk",
    "date_unregistration",
}
CATEGORICAL_COLUMNS = {
    "gender",
    "region",
    "highest_education",
    "imd_band",
    "age_band",
    "disability",
    "code_module",
    "code_presentation",
}

METRIC_NAMES = ["precision", "recall", "f1", "roc_auc"]

FEATURE_ALIAS = {
    "total_click_until_cutoff_mean_strategy": "vle_click_total",
    "active_days_until_cutoff": "vle_active_days",
    "used_site_count_until_cutoff": "vle_site_count",
    "first_activity_date_until_cutoff": "vle_first_day",
    "last_activity_date_until_cutoff": "vle_last_day",
    "avg_click_per_active_day_until_cutoff_mean_strategy": "vle_click_per_day",
    "days_since_last_activity_at_cutoff": "vle_recency_days",
    "days_since_last_activity_at_cutoff_missing": "vle_recency_missing",
    "first_activity_date_until_cutoff_missing": "vle_first_day_missing",
    "last_activity_date_until_cutoff_missing": "vle_last_day_missing",
    "assessment_count_until_cutoff": "asm_count",
    "mean_score_until_cutoff": "asm_score_mean",
    "min_score_until_cutoff": "asm_score_min",
    "max_score_until_cutoff": "asm_score_max",
    "submitted_late_count_until_cutoff": "asm_late_count",
    "on_time_submission_count_until_cutoff": "asm_ontime_count",
    "avg_days_before_due_until_cutoff": "asm_days_early_mean",
    "assessment_rows_missing_due_date_until_cutoff": "asm_due_date_missing_rows",
    "scored_assessment_count_until_cutoff": "asm_scored_count",
    "weighted_score_until_cutoff": "asm_score_weighted",
    "mean_score_until_cutoff_missing": "asm_score_mean_missing",
    "min_score_until_cutoff_missing": "asm_score_min_missing",
    "max_score_until_cutoff_missing": "asm_score_max_missing",
    "weighted_score_until_cutoff_missing": "asm_score_weighted_missing",
    "scored_assessment_count_until_cutoff_missing": "asm_scored_count_missing",
    "avg_days_before_due_until_cutoff_missing": "asm_days_early_missing",
    "num_of_prev_attempts": "stu_prev_attempts",
    "studied_credits": "stu_credits",
    "date_registration": "stu_reg_day",
    "is_registered_before_start": "stu_reg_before_start",
    "is_retake": "stu_retake",
    "date_registration_missing": "stu_reg_day_missing",
    "is_registered_before_start_missing": "stu_reg_before_start_missing",
    "imd_band_missing": "stu_imd_band_missing",
    "gender": "stu_gender",
    "region": "stu_region",
    "highest_education": "stu_education",
    "imd_band": "stu_imd_band",
    "age_band": "stu_age_band",
    "disability": "stu_disability",
    "code_module": "ctx_module",
    "code_presentation": "ctx_presentation",
}

FEATURE_SET_ALIAS = {
    "smoke_vle": "vle_min",
    "vle_core": "vle_core",
    "assessment_core": "asm_core",
    "static_numeric": "stu_num",
    "static_categorical": "stu_cat",
    "static_mixed": "stu_all",
    "vle_assessment_core": "vle_asm",
    "vle_assessment_static_mixed": "vle_asm_stu",
    "all_numeric_candidate": "num_all",
    "all_modeling_candidate": "full_all",
    "vle_activity_clicks": "vle_activity",
    "minimal_behavior": "min_behavior",
    "beh_early": "beh_early",
    "beh_count": "beh_count",
    "beh_last": "beh_last",
    "beh_early_count": "beh_early_count",
    "beh_early_last": "beh_early_last",
    "beh_count_last": "beh_count_last",
    "beh_all3": "beh_all3",
    "base_beh_early": "base_beh_early",
    "base_beh_count": "base_beh_count",
    "base_beh_last": "base_beh_last",
    "base_beh_early_count": "base_beh_early_count",
    "base_beh_early_last": "base_beh_early_last",
    "base_beh_count_last": "base_beh_count_last",
    "base_beh_all3": "base_beh_all3",
}

FEATURE_SET_DESCRIPTION = {
    "minimal_behavior": "Minimal behavior set: average days early before due date, assessment submission count, and last VLE activity day.",
    "beh_early": "Behavior 3C1: submission earliness only.",
    "beh_count": "Behavior 3C1: assessment submission count only.",
    "beh_last": "Behavior 3C1: last VLE activity day only.",
    "beh_early_count": "Behavior 3C2: submission earliness plus assessment submission count.",
    "beh_early_last": "Behavior 3C2: submission earliness plus last VLE activity day.",
    "beh_count_last": "Behavior 3C2: assessment submission count plus last VLE activity day.",
    "beh_all3": "Behavior 3C3: all three minimal behavior features.",
    "base_beh_early": "Base features plus behavior 3C1: submission earliness.",
    "base_beh_count": "Base features plus behavior 3C1: assessment submission count.",
    "base_beh_last": "Base features plus behavior 3C1: last VLE activity day.",
    "base_beh_early_count": "Base features plus behavior 3C2: submission earliness and assessment submission count.",
    "base_beh_early_last": "Base features plus behavior 3C2: submission earliness and last VLE activity day.",
    "base_beh_count_last": "Base features plus behavior 3C2: assessment submission count and last VLE activity day.",
    "base_beh_all3": "Base features plus behavior 3C3: all three minimal behavior features.",
    "smoke_vle": "Paper-replication minimum: total VLE clicks and active VLE days only.",
    "vle_core": "Core VLE behavior: click volume, activity breadth, click intensity, and recency.",
    "assessment_core": "Assessment behavior: submission counts, score summaries, lateness, and assessment missing flags.",
    "static_numeric": "Student static numeric/background fields and related missing flags.",
    "static_categorical": "Student demographic categories plus module and presentation context.",
    "static_mixed": "All student static numeric and categorical background/context features.",
    "vle_assessment_core": "Behavior-only set combining core VLE and assessment features.",
    "vle_assessment_static_mixed": "Behavior plus student/background/context features.",
    "all_numeric_candidate": "Every eligible numeric modeling feature after excluding keys, targets, leakage, and categorical columns.",
    "all_modeling_candidate": "All numeric candidates plus eligible categorical candidates.",
    "vle_activity_clicks": "Core VLE behavior plus activity-type-level click totals.",
}


def ensure_dirs() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_TABLE_DIR.mkdir(parents=True, exist_ok=True)


def build_scoring() -> dict[str, object]:
    return {
        "precision": make_scorer(precision_score, pos_label=1, zero_division=0),
        "recall": make_scorer(recall_score, pos_label=1, zero_division=0),
        "f1": make_scorer(f1_score, pos_label=1, zero_division=0),
        "roc_auc": "roc_auc",
        "pr_auc": "average_precision",
        "accuracy": "accuracy",
    }


def alias_feature_name(feature_name: str) -> str:
    if feature_name in FEATURE_ALIAS:
        return FEATURE_ALIAS[feature_name]
    prefix = "clicks_activity_"
    suffix = "_until_cutoff_mean_strategy"
    if feature_name.startswith(prefix) and feature_name.endswith(suffix):
        activity_name = feature_name[len(prefix) : -len(suffix)]
        return f"vle_act_{activity_name}"
    return feature_name


def alias_feature_list(feature_list: list[str]) -> list[str]:
    return [alias_feature_name(feature) for feature in feature_list]


def alias_feature_set_name(feature_set_name: str) -> str:
    return FEATURE_SET_ALIAS.get(feature_set_name, feature_set_name)


def split_stored_features(value: object) -> list[str]:
    if pd.isna(value):
        return []
    text = str(value)
    separator = ";" if ";" in text else ","
    return [feature.strip() for feature in text.split(separator) if feature.strip()]


def add_alias_columns_to_results(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    result = df.copy()
    if "feature_set_raw" not in result.columns:
        result["feature_set_raw"] = result["feature_set"]
    if "features_raw" not in result.columns:
        result["features_raw"] = result["features"]
    result["feature_set_alias"] = result["feature_set_raw"].map(alias_feature_set_name)
    result["features_alias"] = result["features_raw"].map(
        lambda value: ";".join(alias_feature_list(split_stored_features(value)))
    )
    result["feature_count"] = result["features_raw"].map(
        lambda value: len(split_stored_features(value))
    )
    return result


def build_model_specs() -> dict[str, dict[str, object]]:
    return {
        "GaussianNB": {
            "estimator": GaussianNB(),
            "scale_numeric": False,
            "param_grid": {"model__var_smoothing": [1e-12, 1e-10, 1e-9, 1e-8]},
        },
        "LogisticRegression": {
            "estimator": LogisticRegression(
                max_iter=3000,
                random_state=RANDOM_STATE,
            ),
            "scale_numeric": True,
            "param_grid": [
                {
                    "model__C": [0.01, 0.1, 1, 10],
                    "model__penalty": ["l1", "l2"],
                    "model__solver": ["liblinear"],
                    "model__class_weight": [None, "balanced"],
                },
                {
                    "model__C": [0.01, 0.1, 1, 10],
                    "model__penalty": ["l2"],
                    "model__solver": ["lbfgs"],
                    "model__class_weight": [None, "balanced"],
                },
            ],
        },
        "DecisionTreeClassifier": {
            "estimator": DecisionTreeClassifier(random_state=RANDOM_STATE),
            "scale_numeric": False,
            "param_grid": {
                "model__criterion": ["gini", "entropy"],
                "model__max_depth": [3, 5, 10, None],
                "model__min_samples_split": [2, 10, 30],
                "model__min_samples_leaf": [1, 5, 10],
                "model__ccp_alpha": [0.0, 0.001, 0.01],
            },
        },
        "RandomForestClassifier": {
            "estimator": RandomForestClassifier(
                random_state=RANDOM_STATE,
                n_jobs=-1,
            ),
            "scale_numeric": False,
            "param_grid": {
                "model__n_estimators": [100, 300],
                "model__max_depth": [5, 10, None],
                "model__min_samples_split": [2, 10],
                "model__min_samples_leaf": [1, 5],
                "model__class_weight": [None, "balanced"],
            },
        },
        "KNeighborsClassifier": {
            "estimator": KNeighborsClassifier(),
            "scale_numeric": True,
            "param_grid": {
                "model__n_neighbors": [5, 11, 21],
                "model__weights": ["uniform", "distance"],
                "model__metric": ["euclidean", "manhattan"],
            },
        },
        "SVC": {
            "estimator": SVC(random_state=RANDOM_STATE),
            "scale_numeric": True,
            "param_grid": {
                "model__C": [0.1, 1, 10],
                "model__kernel": ["rbf", "linear"],
                "model__gamma": ["scale", "auto"],
                "model__class_weight": [None, "balanced"],
            },
        },
    }


def categorical_candidate_columns(df: pd.DataFrame) -> list[str]:
    excluded = ALWAYS_EXCLUDE
    return [
        col
        for col in df.columns
        if col not in excluded
        and col in CATEGORICAL_COLUMNS
        and (
            pd.api.types.is_object_dtype(df[col])
            or pd.api.types.is_string_dtype(df[col])
            or pd.api.types.is_categorical_dtype(df[col])
        )
    ]


def numeric_candidate_columns(df: pd.DataFrame) -> list[str]:
    excluded = ALWAYS_EXCLUDE | CATEGORICAL_COLUMNS
    return [
        col
        for col in df.columns
        if col not in excluded and pd.api.types.is_numeric_dtype(df[col])
    ]


def build_feature_sets(df: pd.DataFrame) -> dict[str, list[str]]:
    # Base paper-replication features: total VLE clicks and active VLE days.
    base_features = [
        "total_click_until_cutoff_mean_strategy",
        "active_days_until_cutoff",
    ]

    behavior_early = ["avg_days_before_due_until_cutoff"]
    behavior_count = ["assessment_count_until_cutoff"]
    behavior_last = ["last_activity_date_until_cutoff"]

    # Minimal behavior set requested for the focused experiment.
    minimal_behavior = behavior_early + behavior_count + behavior_last

    # VLE behavior summary: amount of LMS activity, site breadth, intensity, and recency.
    vle_core = [
        "total_click_until_cutoff_mean_strategy",
        "active_days_until_cutoff",
        "used_site_count_until_cutoff",
        "avg_click_per_active_day_until_cutoff_mean_strategy",
        "days_since_last_activity_at_cutoff",
        "days_since_last_activity_at_cutoff_missing",
    ]

    # Assessment behavior: observed submissions, scores, lateness, and score/due-date missingness.
    assessment_core = [
        "assessment_count_until_cutoff",
        "mean_score_until_cutoff",
        "submitted_late_count_until_cutoff",
        "on_time_submission_count_until_cutoff",
        "avg_days_before_due_until_cutoff",
        "scored_assessment_count_until_cutoff",
        "weighted_score_until_cutoff",
        "mean_score_until_cutoff_missing",
        "weighted_score_until_cutoff_missing",
        "avg_days_before_due_until_cutoff_missing",
    ]

    # Student background numeric fields available before or at registration.
    static_numeric = [
        "num_of_prev_attempts",
        "studied_credits",
        "date_registration",
        "is_registered_before_start",
        "is_retake",
        "date_registration_missing",
        "is_registered_before_start_missing",
        "imd_band_missing",
    ]

    # Student/context categorical fields; these are one-hot encoded inside the pipeline.
    static_categorical = [
        "gender",
        "region",
        "highest_education",
        "imd_band",
        "age_band",
        "disability",
        "code_module",
        "code_presentation",
    ]

    # Activity-type VLE click features, such as forum, quiz, homepage, and resource clicks.
    activity_clicks = [
        col
        for col in df.columns
        if col.startswith("clicks_activity_") and col.endswith("_mean_strategy")
    ]
    all_numeric = numeric_candidate_columns(df)
    all_categorical = categorical_candidate_columns(df)

    feature_sets = {
        # Behavior-only 3C1 combinations.
        "beh_early": behavior_early,
        "beh_count": behavior_count,
        "beh_last": behavior_last,
        # Behavior-only 3C2 combinations.
        "beh_early_count": behavior_early + behavior_count,
        "beh_early_last": behavior_early + behavior_last,
        "beh_count_last": behavior_count + behavior_last,
        # Behavior-only 3C3 combination.
        "beh_all3": minimal_behavior,
        # Base + behavior 3C1 combinations.
        "base_beh_early": base_features + behavior_early,
        "base_beh_count": base_features + behavior_count,
        "base_beh_last": base_features + behavior_last,
        # Base + behavior 3C2 combinations.
        "base_beh_early_count": base_features + behavior_early + behavior_count,
        "base_beh_early_last": base_features + behavior_early + behavior_last,
        "base_beh_count_last": base_features + behavior_count + behavior_last,
        # Base + behavior 3C3 combination.
        "base_beh_all3": base_features + minimal_behavior,
        # Focused three-feature behavior experiment:
        # assignment earliness, assignment submission count, and last access day.
        "minimal_behavior": minimal_behavior,
        # Minimum paper-replication baseline: total clicks plus active days only.
        "smoke_vle": base_features,
        # VLE-only behavioral summary.
        "vle_core": vle_core,
        # Assessment-only behavioral summary.
        "assessment_core": assessment_core,
        # Student numeric/background-only feature set.
        "static_numeric": static_numeric,
        # Student/context categorical-only feature set.
        "static_categorical": static_categorical,
        # Student numeric + categorical background/context.
        "static_mixed": static_numeric + static_categorical,
        # Behavior-only combination without student background/context.
        "vle_assessment_core": vle_core + assessment_core,
        # Main expanded set: behavior + student background/context.
        "vle_assessment_static_mixed": vle_core
        + assessment_core
        + static_numeric
        + static_categorical,
        # Broad numeric candidate set for exploratory comparison.
        "all_numeric_candidate": all_numeric,
        # Broad numeric + categorical candidate set for exploratory comparison.
        "all_modeling_candidate": all_numeric + all_categorical,
    }
    if activity_clicks:
        # VLE summary plus detailed click totals by VLE activity type.
        feature_sets["vle_activity_clicks"] = vle_core + activity_clicks

    return {
        name: keep_existing_unique(columns, df.columns)
        for name, columns in feature_sets.items()
    }


def keep_existing_unique(columns: list[str], available_columns: pd.Index) -> list[str]:
    seen = set()
    result = []
    for col in columns:
        if col in available_columns and col not in seen:
            result.append(col)
            seen.add(col)
    return result


def read_feature_frame(cutoff: str) -> pd.DataFrame:
    path = PROCESSED_DIR / f"features_{cutoff}_baseline.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing baseline feature file: {path.relative_to(ROOT)}")
    df = pd.read_csv(path)
    print(f"Loaded {path.relative_to(ROOT)} shape={df.shape}")
    return df


def validate_experiment_input(
    df: pd.DataFrame,
    selected_features: list[str],
    target_col: str,
    cutoff: str,
    feature_set_name: str,
) -> None:
    if not selected_features:
        raise ValueError(f"No features selected for {cutoff} / {feature_set_name}")

    missing_features = [col for col in selected_features if col not in df.columns]
    if missing_features:
        raise ValueError(
            f"Missing features in {cutoff} / {feature_set_name}: {missing_features}"
        )
    if target_col not in df.columns:
        raise ValueError(f"Target column does not exist: {target_col}")

    numeric_features = [
        col for col in selected_features if pd.api.types.is_numeric_dtype(df[col])
    ]
    categorical_features = [
        col
        for col in selected_features
        if col in CATEGORICAL_COLUMNS and col not in numeric_features
    ]
    unsupported_features = [
        col
        for col in selected_features
        if col not in numeric_features and col not in categorical_features
    ]
    if unsupported_features:
        raise ValueError(
            "Selected features must be numeric or approved categorical columns: "
            f"{unsupported_features}"
        )

    numeric_missing_cells = int(df[numeric_features + [target_col]].isna().sum().sum())
    if numeric_missing_cells:
        raise ValueError(
            f"Experiment numeric matrix has missing cells for {cutoff} / "
            f"{feature_set_name}: {numeric_missing_cells}"
        )

    y_values = set(df[target_col].dropna().astype(int).unique())
    if not y_values.issubset({0, 1}):
        raise ValueError(f"Target must be binary 0/1, found: {sorted(y_values)}")


def build_preprocessor(
    df: pd.DataFrame,
    selected_features: list[str],
    scale_numeric: bool,
) -> ColumnTransformer:
    numeric_features = [
        col for col in selected_features if pd.api.types.is_numeric_dtype(df[col])
    ]
    categorical_features = [col for col in selected_features if col not in numeric_features]

    transformers = []
    if numeric_features:
        numeric_transformer = StandardScaler() if scale_numeric else "passthrough"
        transformers.append(("numeric", numeric_transformer, numeric_features))
    if categorical_features:
        categorical_transformer = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="constant", fill_value="Unknown")),
                (
                    "onehot",
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                ),
            ]
        )
        transformers.append(("categorical", categorical_transformer, categorical_features))

    return ColumnTransformer(transformers=transformers, remainder="drop")


def collect_grid_results(
    grid_search: GridSearchCV,
    run_id: str,
    cutoff: str,
    strategy: str,
    feature_set_name: str,
    model_name: str,
    n_rows: int,
    positive_rate: float,
    target_col: str,
    selected_features: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cv_results = pd.DataFrame(grid_search.cv_results_)
    all_rows = []
    feature_set_alias = alias_feature_set_name(feature_set_name)
    features_raw = ";".join(selected_features)
    features_alias = ";".join(alias_feature_list(selected_features))

    for _, row in cv_results.iterrows():
        params = row["params"]
        result_row = {
            "run_id": run_id,
            "created_at_utc": run_id,
            "cutoff": cutoff,
            "strategy": strategy,
            "feature_set": feature_set_name,
            "feature_set_raw": feature_set_name,
            "feature_set_alias": feature_set_alias,
            "model": model_name,
            "n_rows": n_rows,
            "positive_class": POSITIVE_CLASS_NAME,
            "positive_rate": positive_rate,
            "target": target_col,
            "n_features": len(selected_features),
            "feature_count": len(selected_features),
            "features": features_raw,
            "features_raw": features_raw,
            "features_alias": features_alias,
            "params": json.dumps(params, ensure_ascii=False, default=str),
            "rank_test_f1": row.get("rank_test_f1", np.nan),
            "valid_result": not pd.isna(row.get("mean_test_f1", np.nan)),
        }
        for metric in METRIC_NAMES:
            result_row[f"{metric}_mean"] = row.get(f"mean_test_{metric}", np.nan)
            result_row[f"{metric}_std"] = row.get(f"std_test_{metric}", np.nan)
        all_rows.append(result_row)

    all_rows_df = pd.DataFrame(all_rows)
    best_index = grid_search.best_index_
    best_params = grid_search.best_params_

    best_row = {
        "run_id": run_id,
        "created_at_utc": run_id,
        "cutoff": cutoff,
        "strategy": strategy,
        "feature_set": feature_set_name,
        "feature_set_raw": feature_set_name,
        "feature_set_alias": feature_set_alias,
        "model": model_name,
        "n_rows": n_rows,
        "positive_class": POSITIVE_CLASS_NAME,
        "positive_rate": positive_rate,
        "target": target_col,
        "n_features": len(selected_features),
        "feature_count": len(selected_features),
        "features": features_raw,
        "features_raw": features_raw,
        "features_alias": features_alias,
        "best_params": json.dumps(best_params, ensure_ascii=False, default=str),
        "selected_by": "f1",
    }
    for metric in METRIC_NAMES:
        best_row[f"{metric}_mean"] = grid_search.cv_results_[f"mean_test_{metric}"][
            best_index
        ]
        best_row[f"{metric}_std"] = grid_search.cv_results_[f"std_test_{metric}"][
            best_index
        ]

    return all_rows_df, pd.DataFrame([best_row])


def save_result_csv(new_all_results: pd.DataFrame, new_best_results: pd.DataFrame) -> None:
    new_all_results = add_alias_columns_to_results(new_all_results)
    new_best_results = add_alias_columns_to_results(new_best_results)

    if ALL_RESULTS_PATH.exists():
        old_all_results = pd.read_csv(ALL_RESULTS_PATH)
        old_all_results = add_alias_columns_to_results(old_all_results)
        all_results = pd.concat([old_all_results, new_all_results], ignore_index=True)
    else:
        all_results = new_all_results.copy()

    if BEST_RESULTS_PATH.exists():
        old_best_results = pd.read_csv(BEST_RESULTS_PATH)
        old_best_results = add_alias_columns_to_results(old_best_results)
        best_results = pd.concat([old_best_results, new_best_results], ignore_index=True)
    else:
        best_results = new_best_results.copy()

    all_results.to_csv(ALL_RESULTS_PATH, index=False)
    best_results.to_csv(BEST_RESULTS_PATH, index=False)
    print(f"Saved all grid results to: {ALL_RESULTS_PATH.relative_to(ROOT)}")
    print(f"Saved best results to: {BEST_RESULTS_PATH.relative_to(ROOT)}")


def refresh_result_aliases() -> None:
    refreshed_any = False
    for path in [ALL_RESULTS_PATH, BEST_RESULTS_PATH]:
        if not path.exists():
            print(f"Skip missing result file: {path.relative_to(ROOT)}")
            continue
        result_df = pd.read_csv(path)
        result_df = add_alias_columns_to_results(result_df)
        result_df.to_csv(path, index=False)
        refreshed_any = True
        print(f"Refreshed alias columns in: {path.relative_to(ROOT)}")
    if not refreshed_any:
        print("No result CSV files were found to refresh.")


def run_one_experiment(
    df: pd.DataFrame,
    model_specs: dict[str, dict[str, object]],
    scoring: dict[str, object],
    cv: StratifiedKFold,
    run_id: str,
    cutoff: str,
    strategy: str,
    feature_set_name: str,
    selected_features: list[str],
    model_name: str,
    target_col: str = TARGET_COL,
    n_jobs: int = -1,
) -> tuple[GridSearchCV, pd.DataFrame, pd.DataFrame]:
    validate_experiment_input(df, selected_features, target_col, cutoff, feature_set_name)

    X = df[selected_features].copy()
    y = df[target_col].astype(int).copy()
    n_rows = len(df)
    positive_rate = float(y.mean())

    pipeline = Pipeline(
        steps=[
            (
                "preprocessor",
                build_preprocessor(
                    df=df,
                    selected_features=selected_features,
                    scale_numeric=bool(model_specs[model_name]["scale_numeric"]),
                ),
            ),
            ("model", model_specs[model_name]["estimator"]),
        ]
    )
    param_grid = model_specs[model_name]["param_grid"]

    grid_search = GridSearchCV(
        estimator=pipeline,
        param_grid=param_grid,
        scoring=scoring,
        refit="f1",
        cv=cv,
        n_jobs=n_jobs,
        return_train_score=False,
        error_score=np.nan,
    )

    print(
        "Running: "
        f"cutoff={cutoff}, feature_set={feature_set_name} "
        f"({alias_feature_set_name(feature_set_name)}), model={model_name}, "
        f"n_rows={n_rows}, positive_rate={positive_rate:.4f}, "
        f"n_features={len(selected_features)}"
    )
    grid_search.fit(X, y)

    all_rows_df, best_row_df = collect_grid_results(
        grid_search=grid_search,
        run_id=run_id,
        cutoff=cutoff,
        strategy=strategy,
        feature_set_name=feature_set_name,
        model_name=model_name,
        n_rows=n_rows,
        positive_rate=positive_rate,
        target_col=target_col,
        selected_features=selected_features,
    )
    save_result_csv(all_rows_df, best_row_df)
    print(
        "Best F1: "
        f"{best_row_df.loc[0, 'f1_mean']:.6f} "
        f"params={best_row_df.loc[0, 'best_params']}"
    )
    return grid_search, all_rows_df, best_row_df


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run reviewed OULAD CV tuning experiments and save grid/best CSVs."
    )
    parser.add_argument("--cutoffs", nargs="+", default=["week5"], choices=CUTOFFS)
    parser.add_argument(
        "--feature-sets",
        nargs="+",
        default=["smoke_vle"],
        help="Feature set names. Use --list-feature-sets to inspect available names.",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=["GaussianNB"],
        help="Model names. Use --list-models to inspect available names.",
    )
    parser.add_argument("--target-col", default=TARGET_COL)
    parser.add_argument("--n-splits", type=int, default=5)
    parser.add_argument("--n-jobs", type=int, default=-1)
    parser.add_argument("--list-models", action="store_true")
    parser.add_argument("--list-feature-sets", action="store_true")
    parser.add_argument(
        "--refresh-result-aliases",
        action="store_true",
        help="Add or refresh alias columns in existing result CSV files without running models.",
    )
    return parser.parse_args()


def write_report() -> None:
    lines = [
        "# Model Experiment Logging Report",
        "",
        "## Scope",
        "",
        "This script adds repeatable cross-validation experiment logging. It does not train or save a final production model.",
        "",
        "## Output Files",
        "",
        f"- `{ALL_RESULTS_PATH.relative_to(ROOT)}` stores every cutoff, feature set, model, and parameter-combination CV result.",
        f"- `{BEST_RESULTS_PATH.relative_to(ROOT)}` stores the F1-selected best parameter row for each executed experiment.",
        "",
        "## Metrics",
        "",
        "- precision",
        "- recall",
        "- f1",
        "- roc_auc",
        "- pr_auc",
        "- accuracy",
        "",
        "## Guardrails",
        "",
        "- `id_student`, `final_result`, `target_withdrawn`, `target_at_risk`, and `date_unregistration` are excluded from automatic predictor sets.",
        "- Mixed feature sets one-hot encode reviewed categorical columns inside the model pipeline only.",
        "- Categorical missing values are encoded as `Unknown` inside the pipeline; raw feature CSVs are not modified.",
        "- Result CSVs retain raw feature names and add shorter alias columns for tables and reports.",
        "- Results are appended with a UTC `run_id`, so repeated runs remain auditable.",
        "- Selection uses `GridSearchCV(refit='f1')`; this is a tuning comparison, not a final model artifact.",
        "",
        "## Feature Set Aliases",
        "",
        "| raw name | alias |",
        "| --- | --- |",
        *[
            f"| `{raw_name}` | `{alias_name}` |"
            for raw_name, alias_name in FEATURE_SET_ALIAS.items()
        ],
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REPORT_PATH.relative_to(ROOT)}")


def main() -> None:
    ensure_dirs()
    args = parse_args()
    model_specs = build_model_specs()
    scoring = build_scoring()

    if args.list_models:
        print("\n".join(model_specs.keys()))
        return

    if args.refresh_result_aliases:
        refresh_result_aliases()
        write_report()
        return

    first_df = read_feature_frame(args.cutoffs[0])
    feature_sets = build_feature_sets(first_df)

    if args.list_feature_sets:
        for name, columns in feature_sets.items():
            print(
                f"{name} ({alias_feature_set_name(name)}): "
                f"{len(columns)} features"
            )
        return

    unknown_models = [model for model in args.models if model not in model_specs]
    if unknown_models:
        raise ValueError(f"Unknown models: {unknown_models}")
    unknown_feature_sets = [
        feature_set for feature_set in args.feature_sets if feature_set not in feature_sets
    ]
    if unknown_feature_sets:
        raise ValueError(f"Unknown feature sets: {unknown_feature_sets}")

    cv = StratifiedKFold(
        n_splits=args.n_splits,
        shuffle=True,
        random_state=RANDOM_STATE,
    )
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    write_report()
    for cutoff in args.cutoffs:
        df = first_df if cutoff == args.cutoffs[0] else read_feature_frame(cutoff)
        feature_sets = build_feature_sets(df)
        for feature_set_name in args.feature_sets:
            selected_features = feature_sets[feature_set_name]
            for model_name in args.models:
                run_one_experiment(
                    df=df,
                    model_specs=model_specs,
                    scoring=scoring,
                    cv=cv,
                    run_id=run_id,
                    cutoff=cutoff,
                    strategy=STRATEGY,
                    feature_set_name=feature_set_name,
                    selected_features=selected_features,
                    model_name=model_name,
                    target_col=args.target_col,
                    n_jobs=args.n_jobs,
                )

    print("\nExperiment run complete. No final model artifact was saved.")


if __name__ == "__main__":
    main()
