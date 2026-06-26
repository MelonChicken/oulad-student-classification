"""Streamlit app for the OULAD early at-risk prediction portfolio demo."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
import plotly.express as px
import streamlit as st


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "processed"
APP_DATA_DIR = ROOT / "data" / "app"
MODEL_DIR = ROOT / "models"

APP_KEY = ["code_module", "code_presentation", "anon_id"]
WEEKS = ["week5", "week7", "week10"]
WEEK_LABELS = {"week5": "Week 5", "week7": "Week 7", "week10": "Week 10"}

FEATURE_FILES = {
    "week5": APP_DATA_DIR / "app_features_week5.csv",
    "week7": APP_DATA_DIR / "app_features_week7.csv",
    "week10": APP_DATA_DIR / "app_features_week10.csv",
}
MODEL_FILES = {
    "week5": MODEL_DIR / "rf_week5.pkl",
    "week7": MODEL_DIR / "rf_week7.pkl",
    "week10": MODEL_DIR / "rf_week10.pkl",
}

TEST_STUDENTS_PATH = APP_DATA_DIR / "app_test_students.csv"
METRICS_PATH = MODEL_DIR / "metrics.json"
FEATURE_COLUMNS_PATH = MODEL_DIR / "feature_columns.json"

WHAT_IF_FEATURES = [
    "active_days_until_cutoff",
    "total_click_until_cutoff",
    "days_since_last_activity_at_cutoff",
    "assessment_count_until_cutoff",
    "mean_score_until_cutoff",
    "avg_days_before_due_until_cutoff",
]

COHORT_COMPARISON_FEATURES = [
    "active_days_until_cutoff",
    "total_click_until_cutoff",
    "used_site_count_until_cutoff",
    "avg_click_per_active_day_until_cutoff",
    "days_since_last_activity_at_cutoff",
    "assessment_count_until_cutoff",
    "mean_score_until_cutoff",
    "avg_days_before_due_until_cutoff",
]

FEATURE_LABELS = {
    "active_days_until_cutoff": "Active days",
    "total_click_until_cutoff": "Total clicks",
    "used_site_count_until_cutoff": "Learning resources used",
    "avg_click_per_active_day_until_cutoff": "Clicks per active day",
    "days_since_last_activity_at_cutoff": "Days since last activity",
    "assessment_count_until_cutoff": "Submitted assessments",
    "mean_score_until_cutoff": "Mean assessment score",
    "avg_days_before_due_until_cutoff": "Avg. days before due date",
    "highest_education_encoded": "Education level",
    "credits_bin": "Credit load",
}

RISK_DIRECTION = {
    "active_days_until_cutoff": "below",
    "total_click_until_cutoff": "below",
    "used_site_count_until_cutoff": "below",
    "avg_click_per_active_day_until_cutoff": "below",
    "days_since_last_activity_at_cutoff": "above",
    "assessment_count_until_cutoff": "below",
    "mean_score_until_cutoff": "below",
    "avg_days_before_due_until_cutoff": "below",
}


st.set_page_config(
    page_title="OULAD At-Risk Prediction",
    layout="wide",
)


def require_paths(paths: list[Path]) -> None:
    """Stop the app with a clear message if an artifact is missing."""
    missing = [str(path.relative_to(ROOT)) for path in paths if not path.exists()]
    if missing:
        st.error(
            "Missing required artifacts. Run `python src\\build_features.py` and "
            "`python src\\train_model.py` first.\n\n" + "\n".join(missing)
        )
        st.stop()


@st.cache_data(show_spinner=False)
def load_feature_columns() -> list[str]:
    """Load the exact feature column list used during model training."""
    require_paths([FEATURE_COLUMNS_PATH])
    payload = json.loads(FEATURE_COLUMNS_PATH.read_text(encoding="utf-8"))
    return payload["features"]


@st.cache_data(show_spinner=False)
def load_metrics() -> pd.DataFrame:
    """Load model metrics from JSON into a display table."""
    require_paths([METRICS_PATH])
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    rows = []
    for week, values in metrics.items():
        row = {"week": week, "label": WEEK_LABELS.get(week, week)}
        row.update(values)
        rows.append(row)
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def load_features() -> dict[str, pd.DataFrame]:
    """Load processed feature files for all weeks."""
    require_paths(list(FEATURE_FILES.values()))
    frames = {week: pd.read_csv(path) for week, path in FEATURE_FILES.items()}
    for path, frame in zip(FEATURE_FILES.values(), frames.values()):
        if "id_student" in frame.columns:
            st.error(f"{path.relative_to(ROOT)} exposes an internal student identifier. Run `python -m src.anonymize`.")
            st.stop()
    return frames


@st.cache_data(show_spinner=False)
def load_test_students() -> pd.DataFrame:
    """Load anonymized held-out test rows for display."""
    require_paths([TEST_STUDENTS_PATH])
    test_students = pd.read_csv(TEST_STUDENTS_PATH)
    if "id_student" in test_students.columns:
        st.error("App test data exposes an internal student identifier. Run `python -m src.anonymize`.")
        st.stop()
    return test_students


@st.cache_resource(show_spinner=False)
def load_models() -> dict[str, object]:
    """Load trained RandomForest pipelines."""
    require_paths(list(MODEL_FILES.values()))
    return {week: joblib.load(path) for week, path in MODEL_FILES.items()}


def key_mask(df: pd.DataFrame, key_row: pd.Series) -> pd.Series:
    """Return rows matching a student-module-presentation key."""
    mask = pd.Series(True, index=df.index)
    for column in APP_KEY:
        mask &= df[column].eq(key_row[column])
    return mask


def selected_test_row(test_students: pd.DataFrame) -> pd.Series:
    """Render the held-out Student Profile selector."""
    display_df = test_students.sort_values(APP_KEY).reset_index(drop=True)
    labels = [
        f"Student Profile {row.anon_id}"
        for row in display_df.itertuples()
    ]
    selected = st.selectbox("Student Profile", labels)
    return display_df.iloc[labels.index(selected)]


def feature_label(feature: str) -> str:
    """Return a human-readable label for a model feature."""
    return FEATURE_LABELS.get(feature, feature)


def target_label(value: int) -> str:
    """Convert the binary target into a readable label."""
    return "At-risk" if int(value) == 1 else "Success"


def risk_level(probability: float) -> str:
    """Bucket an at-risk probability for interpretation cards."""
    if probability < 0.35:
        return "Low"
    if probability < 0.65:
        return "Medium"
    return "High"


def risk_trend(probability_df: pd.DataFrame) -> str:
    """Summarize risk movement from first to last available week."""
    values = probability_df.dropna(subset=["risk_probability"])["risk_probability"].tolist()
    if len(values) < 2:
        return "Not enough data"
    delta = values[-1] - values[0]
    if delta > 0.03:
        return "Increasing"
    if delta < -0.03:
        return "Decreasing"
    return "Stable"


def get_week_row(features: dict[str, pd.DataFrame], week: str, key_row: pd.Series) -> pd.Series | None:
    """Return one feature row if the selected Student Profile is active in the given week."""
    matches = features[week].loc[key_mask(features[week], key_row)]
    if matches.empty:
        return None
    return matches.iloc[0]


def predict_probability(model: object, row: pd.Series, feature_columns: list[str]) -> float:
    """Predict at-risk probability for a single feature row."""
    return float(model.predict_proba(pd.DataFrame([row[feature_columns]]))[0, 1])


def probabilities_by_week(
    key_row: pd.Series,
    features: dict[str, pd.DataFrame],
    models: dict[str, object],
    feature_columns: list[str],
) -> pd.DataFrame:
    """Predict probabilities across all available weeks for the selected row."""
    rows = []
    for week in WEEKS:
        row = get_week_row(features, week, key_row)
        if row is None:
            rows.append({"week": week, "label": WEEK_LABELS[week], "risk_probability": None})
            continue
        rows.append(
            {
                "week": week,
                "label": WEEK_LABELS[week],
                "risk_probability": predict_probability(models[week], row, feature_columns),
            }
        )
    return pd.DataFrame(rows)


def feature_table_by_week(
    key_row: pd.Series,
    features: dict[str, pd.DataFrame],
    feature_columns: list[str],
) -> pd.DataFrame:
    """Build a selected Student Profile feature table across weeks."""
    rows = []
    for week in WEEKS:
        row = get_week_row(features, week, key_row)
        if row is None:
            rows.append({"week": WEEK_LABELS[week], "status": "Not active at cutoff"})
            continue
        rows.append({"week": WEEK_LABELS[week], "status": "Active", **row[feature_columns].to_dict()})
    table = pd.DataFrame(rows)
    return table.rename(columns={feature: feature_label(feature) for feature in feature_columns})


def cohort_comparison(
    row: pd.Series,
    week_df: pd.DataFrame,
    features_to_compare: list[str] = COHORT_COMPARISON_FEATURES,
) -> pd.DataFrame:
    """Compare a selected row against cohort averages for numeric features."""
    rows = []
    for feature in features_to_compare:
        if feature not in week_df.columns or feature not in row.index:
            continue
        cohort_average = float(week_df[feature].mean())
        student_value = float(row[feature])
        ratio = None if cohort_average == 0 else student_value / cohort_average
        rows.append(
            {
                "feature": feature,
                "Feature": feature_label(feature),
                "Student value": student_value,
                "Cohort average": cohort_average,
                "Ratio to cohort average": ratio,
                "Deviation from cohort average": student_value - cohort_average,
            }
        )
    return pd.DataFrame(rows)


def source_feature_importance(model: object) -> pd.DataFrame:
    """Aggregate transformed pipeline importances back to source feature names."""
    preprocessor = model.named_steps["preprocessor"]
    forest = model.named_steps["model"]
    transformed_names = preprocessor.get_feature_names_out()
    raw_importances = pd.DataFrame(
        {"transformed_feature": transformed_names, "importance": forest.feature_importances_}
    )

    source_names = []
    for transformed in raw_importances["transformed_feature"]:
        source = transformed
        for original in preprocessor.feature_names_in_:
            if transformed == original or transformed.endswith(f"__{original}") or f"__{original}_" in transformed:
                source = original
                break
        source_names.append(source)

    raw_importances["feature"] = source_names
    importance = (
        raw_importances.groupby("feature", as_index=False)["importance"]
        .sum()
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )
    importance["Feature"] = importance["feature"].map(feature_label)
    return importance


def risk_deviation_text(comparison: pd.DataFrame) -> str:
    """Summarize the largest risk-related deviations from the cohort average."""
    if comparison.empty:
        return "No cohort comparison is available for this week."

    rows = []
    for _, item in comparison.iterrows():
        feature = item["feature"]
        label = item["Feature"]
        student_value = item["Student value"]
        cohort_average = item["Cohort average"]
        direction = RISK_DIRECTION.get(feature)
        if direction == "below" and student_value < cohort_average:
            rows.append((label, student_value, cohort_average, abs(student_value - cohort_average)))
        elif direction == "above" and student_value > cohort_average:
            rows.append((label, student_value, cohort_average, abs(student_value - cohort_average)))
    if not rows:
        return "The selected behavioral features are not worse than the cohort average in the expected risk direction."

    rows = sorted(rows, key=lambda value: value[3], reverse=True)[:3]
    pieces = [f"{label}: {student:.2f} vs cohort {mean:.2f}" for label, student, mean, _ in rows]
    return "Main risk-related deviations: " + "; ".join(pieces) + "."


def interpretation_text(
    probability: float | None,
    actual_label: str,
    target_at_risk: int,
    comparison: pd.DataFrame,
) -> str:
    """Generate a short portfolio-friendly interpretation paragraph."""
    if probability is None:
        return "The selected Student Profile is not active in this cutoff, so no at-risk probability is shown."
    if probability >= 0.7:
        risk_text = "high"
    elif probability >= 0.4:
        risk_text = "moderate"
    else:
        risk_text = "low"
    return (
        f"Risk level: {risk_text}. The selected cutoff at-risk probability is {probability:.1%}. "
        f"Actual outcome: {actual_label}; target label: {target_label(target_at_risk)}. "
        f"{risk_deviation_text(comparison)} This is model interpretation, not causal explanation."
    )


def metric_value(probability_df: pd.DataFrame, week: str) -> str:
    """Format a week probability for metric cards."""
    value = probability_df.loc[probability_df["week"].eq(week), "risk_probability"]
    if value.empty or pd.isna(value.iloc[0]):
        return "N/A"
    return f"{float(value.iloc[0]):.1%}"


def best_metric(metrics: pd.DataFrame, column: str) -> float:
    """Return the best metric value across cutoffs."""
    return float(metrics[column].max())


def best_cutoff(metrics: pd.DataFrame, column: str) -> str:
    """Return the label for the best-performing cutoff by metric."""
    row = metrics.loc[metrics[column].idxmax()]
    return str(row["label"])


def overview_page(test_students: pd.DataFrame, metrics: pd.DataFrame, feature_columns: list[str]) -> None:
    """Render the project overview page."""
    st.title("OULAD Early At-Risk Prediction")
    st.write(
        "A portfolio demo for estimating whether an anonymized Student Profile is at risk "
        "of Fail or Withdrawn using only learning behavior available at Week 5, Week 7, and Week 10."
    )
    st.info(
        "This demo is for portfolio and research exploration only, not for real student intervention decisions."
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Held-out Student Profiles", f"{test_students['anon_id'].nunique():,}")
    col2.metric("Model features", len(feature_columns))
    col3.metric("Best ROC-AUC", f"{best_metric(metrics, 'roc_auc'):.3f}")
    col4.metric("Best F1", f"{best_metric(metrics, 'f1'):.3f}")

    st.subheader("What this demo shows")
    st.markdown(
        """
1. Select an unseen Student Profile.
2. Track risk estimates over Week 5, Week 7, and Week 10.
3. Compare the Student Profile's behavior with the cohort average.
4. Run a what-if model sensitivity simulation.
"""
    )
    st.success(
        "The demo focuses on observable learning behavior rather than demographic attributes."
    )


def student_explorer_page(
    test_students: pd.DataFrame,
    features: dict[str, pd.DataFrame],
    models: dict[str, object],
    feature_columns: list[str],
) -> None:
    """Render the student explorer page."""
    st.title("Student Explorer")
    key_row = selected_test_row(test_students)
    st.caption(
        f"Student Profile {key_row['anon_id']} | {key_row['code_module']} / {key_row['code_presentation']}"
    )

    probability_df = probabilities_by_week(key_row, features, models, feature_columns)
    trend = risk_trend(probability_df)
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Actual outcome", str(key_row.get("final_result", "Unavailable")))
    col2.metric("Week 5 at-risk probability", metric_value(probability_df, "week5"))
    col3.metric("Week 7 at-risk probability", metric_value(probability_df, "week7"))
    col4.metric("Week 10 at-risk probability", metric_value(probability_df, "week10"))
    col5.metric("Risk trend", trend)

    chart_df = probability_df.dropna(subset=["risk_probability"])
    fig = px.line(
        chart_df,
        x="label",
        y="risk_probability",
        markers=True,
        range_y=[0, 1],
        labels={"label": "Cutoff", "risk_probability": "At-risk probability"},
    )
    fig.update_layout(height=340, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, width="stretch")

    with st.expander("View raw feature values by week"):
        st.dataframe(feature_table_by_week(key_row, features, feature_columns), width="stretch")

    st.subheader("Selected-week summary")
    selected_week = st.radio("Selected week for comparison", WEEKS, format_func=lambda week: WEEK_LABELS[week], horizontal=True)
    selected_row = get_week_row(features, selected_week, key_row)
    if selected_row is None:
        st.warning("This Student Profile is not active in the selected cutoff.")
        return

    comparison = cohort_comparison(selected_row, features[selected_week])
    selected_probability = probability_df.loc[
        probability_df["week"].eq(selected_week), "risk_probability"
    ].iloc[0]
    st.info(
        interpretation_text(
            probability=None if pd.isna(selected_probability) else float(selected_probability),
            actual_label=str(key_row.get("final_result", "Unavailable")),
            target_at_risk=int(key_row["target_at_risk"]),
            comparison=comparison,
        )
    )

    ratio_df = comparison.dropna(subset=["Ratio to cohort average"]).copy()
    ratio_df = ratio_df.sort_values("Ratio to cohort average", ascending=True)
    fig = px.bar(
        ratio_df,
        x="Ratio to cohort average",
        y="Feature",
        orientation="h",
        title="Student behavior relative to cohort average",
        labels={"Ratio to cohort average": "Ratio to cohort average", "Feature": ""},
    )
    fig.add_vline(x=1.0, line_dash="dash", line_color="gray")
    fig.update_layout(height=420, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, width="stretch")

    importance = source_feature_importance(models[selected_week]).head(5)
    fig = px.bar(
        importance.sort_values("importance", ascending=True),
        x="importance",
        y="Feature",
        orientation="h",
        title="Top 5 global feature importance",
        labels={"importance": "Importance", "Feature": ""},
    )
    fig.update_layout(height=320, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, width="stretch")

    with st.expander("View raw global feature importance table"):
        st.dataframe(importance[["Feature", "feature", "importance"]], width="stretch")


def slider_bounds(feature: str, original: float, week_df: pd.DataFrame) -> tuple[float, float]:
    """Create practical slider bounds from observed data."""
    observed_max = float(week_df[feature].quantile(0.95)) if feature in week_df else original
    upper = max(observed_max, original * 2, original + 1, 1.0)
    return 0.0, upper


def clamp(value: float, feature: str, week_df: pd.DataFrame) -> float:
    """Clamp a preset value to the slider bounds for a feature."""
    low, high = slider_bounds(feature, value, week_df)
    return max(low, min(float(value), high))


def apply_scenario_preset(row: pd.Series, preset: str, week_df: pd.DataFrame) -> dict[str, float]:
    """Return slider defaults for one What-if scenario preset."""
    defaults = {feature: float(row[feature]) for feature in WHAT_IF_FEATURES}
    if preset == "More engagement":
        defaults["active_days_until_cutoff"] *= 1.25
        defaults["total_click_until_cutoff"] *= 1.25
        defaults["days_since_last_activity_at_cutoff"] *= 0.5
    elif preset == "Lower engagement":
        defaults["active_days_until_cutoff"] *= 0.75
        defaults["total_click_until_cutoff"] *= 0.75
        defaults["days_since_last_activity_at_cutoff"] *= 1.5
    elif preset == "Better assessment performance":
        defaults["assessment_count_until_cutoff"] += 1
        defaults["mean_score_until_cutoff"] += 10
        defaults["avg_days_before_due_until_cutoff"] += 2
    elif preset == "Recent inactivity":
        defaults["days_since_last_activity_at_cutoff"] += 14

    return {
        feature: clamp(value, feature, week_df)
        for feature, value in defaults.items()
    }


def what_if_page(
    test_students: pd.DataFrame,
    features: dict[str, pd.DataFrame],
    models: dict[str, object],
    feature_columns: list[str],
) -> None:
    """Render the what-if simulator."""
    st.title("What-if Simulator")
    st.warning("This is a model-sensitivity simulation, not a causal estimate.")
    key_row = selected_test_row(test_students)
    week = st.radio("Week", WEEKS, format_func=lambda item: WEEK_LABELS[item], horizontal=True)
    original_row = get_week_row(features, week, key_row)
    if original_row is None:
        st.warning("This Student Profile is not active in the selected cutoff.")
        return

    simulated = original_row.copy()
    preset = st.selectbox(
        "Scenario preset",
        [
            "Original",
            "More engagement",
            "Lower engagement",
            "Better assessment performance",
            "Recent inactivity",
        ],
    )
    defaults = apply_scenario_preset(original_row, preset, features[week])
    cols = st.columns(2)
    for index, feature in enumerate(WHAT_IF_FEATURES):
        low, high = slider_bounds(feature, float(original_row[feature]), features[week])
        simulated[feature] = cols[index % 2].slider(
            feature_label(feature),
            min_value=low,
            max_value=high,
            value=float(defaults.get(feature, original_row[feature])),
            step=max((high - low) / 100, 0.1),
        )

    original_probability = predict_probability(models[week], original_row, feature_columns)
    simulated_probability = predict_probability(models[week], simulated, feature_columns)
    difference = simulated_probability - original_probability

    col1, col2, col3 = st.columns(3)
    col1.metric("Original risk estimate", f"{original_probability:.1%}")
    col2.metric("Simulated risk estimate", f"{simulated_probability:.1%}")
    col3.metric("Risk estimate difference", f"{difference:+.1%}")

    if difference < -0.005:
        st.success("The simulated profile is estimated as lower risk by the model.")
    elif difference > 0.005:
        st.warning("The simulated profile is estimated as higher risk by the model.")
    else:
        st.info("The simulated profile has a similar model risk estimate.")

    with st.expander("View original and simulated values"):
        details = pd.DataFrame(
            {
                "Feature": [feature_label(feature) for feature in WHAT_IF_FEATURES],
                "Original value": [original_row[feature] for feature in WHAT_IF_FEATURES],
                "Simulated value": [simulated[feature] for feature in WHAT_IF_FEATURES],
            }
        )
        st.dataframe(details, width="stretch")


def performance_page(metrics: pd.DataFrame, models: dict[str, object]) -> None:
    """Render model performance and importance summaries."""
    st.title("Model Performance")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Best ROC-AUC", f"{best_metric(metrics, 'roc_auc'):.3f}")
    col2.metric("Best F1", f"{best_metric(metrics, 'f1'):.3f}")
    col3.metric("Best cutoff by ROC-AUC", best_cutoff(metrics, "roc_auc"))
    col4.metric("Test split", "Grouped by student")

    display_columns = [
        "label",
        "precision",
        "recall",
        "f1",
        "roc_auc",
        "pr_auc",
        "accuracy",
        "train_rows",
        "test_rows",
    ]

    chart_df = metrics.melt(
        id_vars=["label"],
        value_vars=["roc_auc", "f1"],
        var_name="metric",
        value_name="score",
    )
    fig = px.line(
        chart_df,
        x="label",
        y="score",
        color="metric",
        markers=True,
        range_y=[0, 1],
        labels={"label": "Cutoff", "score": "Score", "metric": "Metric"},
    )
    fig.update_layout(height=360, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, width="stretch")

    with st.expander("View full metrics table"):
        st.dataframe(metrics[display_columns], width="stretch")

    st.subheader("Feature importance by week")
    selected_week = st.selectbox("Week", WEEKS, format_func=lambda week: WEEK_LABELS[week])
    importance = source_feature_importance(models[selected_week])
    fig = px.bar(
        importance.sort_values("importance", ascending=True),
        x="importance",
        y="Feature",
        orientation="h",
        labels={"importance": "Importance", "Feature": ""},
    )
    fig.update_layout(height=420, margin=dict(l=20, r=20, t=20, b=20), yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, width="stretch")

    st.info(
        "Limitations: historical OULAD data; not causal; not for real intervention without "
        "fairness and external validation; demographic features are excluded intentionally."
    )


def main() -> None:
    """Run the Streamlit app."""
    feature_columns = load_feature_columns()
    metrics = load_metrics()
    features = load_features()
    test_students = load_test_students()
    models = load_models()

    page = st.sidebar.radio(
        "Page",
        ["Project Overview", "Student Explorer", "What-if Simulator", "Model Performance"],
    )
    if page == "Project Overview":
        overview_page(test_students, metrics, feature_columns)
    elif page == "Student Explorer":
        student_explorer_page(test_students, features, models, feature_columns)
    elif page == "What-if Simulator":
        what_if_page(test_students, features, models, feature_columns)
    else:
        performance_page(metrics, models)


if __name__ == "__main__":
    main()
