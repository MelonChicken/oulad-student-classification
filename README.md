# Early At-Risk Student Prediction with OULAD

## Summary

This project builds an end-to-end educational data mining demo for early at-risk student prediction using the Open University Learning Analytics Dataset (OULAD). It creates cutoff-specific behavioral features, trains one Random Forest model for each early prediction week, anonymizes app-facing data, and serves the result through a Streamlit portfolio app.

This project reframes educational data mining as a behavior-based state prediction problem.

## Motivation

Many educational prediction projects focus on final outcomes after substantial evidence has already accumulated. This project instead asks whether early behavioral signals can describe a student's current risk state at Week 5, Week 7, and Week 10.

The goal is not to make real intervention decisions. The goal is to demonstrate a careful, leakage-aware modeling pipeline that can be inspected through an interactive app.

## Why Behavior-Based Prediction?

The model intentionally focuses on learning behavior available before each cutoff:

- VLE activity volume
- active learning days
- site usage breadth
- recency of activity
- assessment participation
- assessment score and submission timing

These features describe how a student is engaging with the course up to a specific point in time. This makes the demo more aligned with early state monitoring than with static profiling.

## Dataset

The project uses raw OULAD CSV files placed in `data/raw/`.

Required files:

```text
assessments.csv
courses.csv
studentAssessment.csv
studentInfo.csv
studentRegistration.csv
studentVle.csv
vle.csv
```

The pipeline currently reads:

```text
assessments.csv
studentAssessment.csv
studentInfo.csv
studentRegistration.csv
studentVle.csv
```

## Target Definition

The binary target is:

- `target_at_risk = 1` if `final_result` is `Fail` or `Withdrawn`
- `target_at_risk = 0` if `final_result` is `Pass` or `Distinction`

The app therefore uses the term **At-risk probability**, not fail probability.

## Feature Design

Feature files are generated for three cutoffs:

- Week 5: day 35
- Week 7: day 49
- Week 10: day 70

Selected model features:

```text
active_days_until_cutoff
total_click_until_cutoff
used_site_count_until_cutoff
avg_click_per_active_day_until_cutoff
days_since_last_activity_at_cutoff
assessment_count_until_cutoff
mean_score_until_cutoff
avg_days_before_due_until_cutoff
highest_education_encoded
credits_bin
```

Leakage controls:

- Uses only `studentVle.date <= cutoff_day`.
- Uses only `studentAssessment.date_submitted <= cutoff_day`.
- Removes students with `date_unregistration <= cutoff_day`.
- Aggregates duplicate `studentVle` rows by averaging `sum_click` over `code_module`, `code_presentation`, `id_student`, `id_site`, and `date`.
- Excludes `final_result`, `date_unregistration`, `target_at_risk`, and `target_withdrawn` from model features.

## Why Demographic Features Are Excluded

The deployed model feature list excludes direct demographic columns:

```text
gender
region
age_band
```

This is a portfolio and research demo, not an intervention system. Excluding these fields keeps the app focused on behavior-based state prediction and reduces the risk of presenting demographic profiling as actionable prediction.

## Pipeline

Main source files:

```text
src/config.py
src/data_loader.py
src/build_features.py
src/train_model.py
src/anonymize.py
src/audit_outputs.py
app.py
```

Pipeline steps:

```powershell
python -m src.build_features
python -m src.train_model
python -m src.anonymize
python -m src.audit_outputs
```

App-facing data is written to `data/app/` and uses `anon_id` only. The Streamlit app does not read raw CSV files.

## Model

The project trains one `RandomForestClassifier` per cutoff:

- `models/rf_week5.pkl`
- `models/rf_week7.pkl`
- `models/rf_week10.pkl`

Training uses `GroupShuffleSplit` grouped by `id_student` so that held-out profiles are unseen during training.

Configuration:

```text
n_estimators=300
max_depth=None
min_samples_leaf=5
class_weight="balanced"
random_state=724
n_jobs=-1
```

Metrics are saved to `models/metrics.json`.

## Streamlit App

Run:

```powershell
streamlit run app.py
```

Pages:

- Project Overview
- Student Explorer
- What-if Simulator
- Model Performance

The app uses anonymized `Student Profile` labels and does not expose `id_student`. The What-if Simulator is explicitly described as model sensitivity, not causal inference.

## Local Setup

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run the full local workflow:

```powershell
python -m src.build_features
python -m src.train_model
python -m src.anonymize
python -m src.audit_outputs
streamlit run app.py
```

## Streamlit Cloud Deployment

Before deployment:

- Do not upload `data/raw/`.
- Do not upload private student mapping files.
- Upload only app-facing anonymized data in `data/app/`.
- Confirm `python -m src.audit_outputs` passes.
- Confirm model file sizes fit the deployment environment.
- Confirm `app.py` does not read raw CSV files.

The current model pickle files are each under 100 MB locally, but together they are about 231 MB. Deployment limits should be checked before publishing.

## Limitations

- Predictions are model estimates, not intervention recommendations.
- The target combines `Fail` and `Withdrawn`, which are related but not identical outcomes.
- The What-if Simulator is not causal.
- Random Forest feature importance is global and approximate.
- The app is designed for portfolio review and research exploration, not operational student support.

## Future Work

- Add model compression or smaller deployment artifacts.
- Compare calibrated probabilities.
- Evaluate additional behavior-only feature sets.
- Add validation across module and presentation groups.
- Add richer non-causal explanations while preserving privacy.

## Research Direction Relevance

This demo supports a research direction where educational data mining is framed around observable behavioral state rather than static student identity. It emphasizes temporal cutoff discipline, leakage control, anonymized presentation, and behavior-based interpretation.
