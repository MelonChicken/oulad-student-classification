# Modeling-Ready Dashboard Plan

## Purpose

This dashboard is for researchers who need to understand the processed OULAD data before modeling.

The dashboard should cover two related views:

1. Processing dashboard: how raw data became modeling-ready baseline CSVs.
2. Statistical feature dashboard: how features, target labels, missing flags, and cutoff trends behave before modeling.

The primary modeling-ready files are:

```text
data/processed/features_week5_baseline.csv
data/processed/features_week7_baseline.csv
data/processed/features_week10_baseline.csv
```

These three files are enough for the statistical dashboard. Raw CSVs are only required if the dashboard must re-validate the full raw-to-processed pipeline.

## Correct Current Data State

| cutoff | file | rows | columns | target |
|---|---|---:|---:|---|
| week5 | `features_week5_baseline.csv` | 27,229 | 66 | `target_at_risk` |
| week7 | `features_week7_baseline.csv` | 26,767 | 66 | `target_at_risk` |
| week10 | `features_week10_baseline.csv` | 26,062 | 66 | `target_at_risk` |

Current validation status:

| check | status |
|---|---|
| Raw files modified | No |
| `date_unregistration` in baseline CSVs | No |
| duplicated base key rows | 0 |
| missing cells after final fill | 0 |
| rows with `date_registration > cutoff_day` | 0 |
| missing due-date assessment rows inside week5/week7/week10 cutoff windows | 0 |

## Final Decisions Before Modeling

| Issue | Final Decision |
|---|---|
| Project framing | Early academic at-risk prediction, not only withdrawal prediction |
| Target | `target_at_risk = 1` if `final_result` is `Withdrawn` or `Fail`; otherwise 0 |
| Cohort | Active-at-cutoff students only |
| Cohort condition | Keep rows where `date_registration <= cutoff_day` or missing, and `date_unregistration > cutoff_day` or missing |
| Missing `date_registration` | Retain rows and preserve uncertainty with missing flags |
| VLE duplicate | Use mean strategy for duplicated `code_module`, `code_presentation`, `id_student`, `id_site`, `date` keys |
| Missing values | Add missing flag first, then fill numeric with 0 and categorical with `"Unknown"` |
| No VLE activity | Keep students; encode activity counts as 0 and use missing flags for date-based activity features |
| `date_unregistration` | Use only for cohort construction; exclude from predictors |
| Assessment due-date missing rows | No effect for week5/week7/week10; later cutoffs need more careful handling |
| Predictor exclusion | Always exclude `id_student`, `final_result`, `target_withdrawn`, `target_at_risk`, `date_unregistration` |
| Optional predictors | `code_module`, `code_presentation` may be used depending on modeling goal |
| Split validation | Stratified split for first baseline; group-based split by `id_student` recommended for robustness |

## Recommended Input Files

### Minimum Files

Use these for the statistical feature dashboard:

```text
data/processed/features_week5_baseline.csv
data/processed/features_week7_baseline.csv
data/processed/features_week10_baseline.csv
```

### Recommended Context Files

Use these to populate pipeline explanations and decisions:

```text
data/processed/FEATURES.name
reports/cohort_report.md
reports/baseline_feature_report.md
reports/decision_log.md
data/report_tables/model_results/paper_replication_baseline_results.csv
```

### Raw Files, Only If Re-validating Full Pipeline

Use raw files only when the dashboard must directly re-check raw row counts, joins, VLE duplicate handling, or cutoff filtering:

```text
data/kaggle_oulad/studentInfo.csv
data/kaggle_oulad/studentRegistration.csv
data/kaggle_oulad/studentVle.csv
data/kaggle_oulad/vle.csv
data/kaggle_oulad/studentAssessment.csv
data/kaggle_oulad/assessments.csv
data/kaggle_oulad/courses.csv
```

## Dashboard Structure

## 1. Overview

Show the final baseline files and readiness checks.

Metrics:

| metric | calculation |
|---|---|
| row count | `len(df)` |
| column count | `df.shape[1]` |
| target positive rate | `df["target_at_risk"].mean()` |
| missing cells | `df.isna().sum().sum()` |
| duplicate base key rows | `df.duplicated(["code_module", "code_presentation", "id_student"]).sum()` |
| late registration rows | `(df["date_registration"] > cutoff_day).sum()` |

Expected row counts:

| cutoff | expected rows |
|---|---:|
| week5 | 27,229 |
| week7 | 26,767 |
| week10 | 26,062 |

## 2. Pipeline & Decisions

Explain the pipeline:

```text
raw 7 CSVs
-> integrity/leakage review
-> cutoff feature files
-> active-at-cutoff cohort
-> baseline/model-ready CSVs
```

Include:

- Raw files are not modified.
- Cutoffs are week5/day35, week7/day49, week10/day70.
- VLE rows are filtered with `studentVle.date <= cutoff_day`.
- Assessment rows are filtered with `studentAssessment.date_submitted <= cutoff_day`.
- `date_unregistration` is used only for cohort construction.
- Baseline VLE duplicate strategy is mean aggregation.
- Missing values are represented with missing flags before filling.

## 3. Cohort Summary

Use `reports/cohort_report.md` or recompute from the final files.

Required table:

| cutoff | input rows | output rows | excluded rows | late-registration excluded | pre-cutoff unregistration excluded | missing registration retained |
|---|---:|---:|---:|---:|---:|---:|
| week5 | 32,593 | 27,229 | 5,364 | 15 | 5,349 | 7 |
| week7 | 32,593 | 26,767 | 5,826 | 9 | 5,817 | 7 |
| week10 | 32,593 | 26,062 | 6,531 | 7 | 6,524 | 7 |

## 4. Target Distribution

Target:

```text
target_at_risk = 1 for final_result in {Withdrawn, Fail}
target_at_risk = 0 for final_result in {Pass, Distinction}
```

Show:

- cutoff별 target count
- cutoff별 at-risk rate
- final_result composition inside each cutoff

Suggested charts:

- stacked bar: `target_at_risk` by cutoff
- stacked bar: `final_result` by cutoff

## 5. Feature Inventory

Group columns into:

| Feature group | Examples |
|---|---|
| target/audit | `final_result`, `target_withdrawn`, `target_at_risk` |
| key/identity | `id_student`, `code_module`, `code_presentation` |
| demographic | `gender`, `region`, `highest_education`, `imd_band`, `age_band`, `disability` |
| registration | `date_registration`, `is_registered_before_start` |
| VLE aggregate | `total_click_until_cutoff_mean_strategy`, `active_days_until_cutoff`, `days_since_last_activity_at_cutoff` |
| VLE activity type | `clicks_activity_*_until_cutoff_mean_strategy` |
| assessment | score/count/late/on-time/weighted features |
| missing flag | `*_missing` |

Important modeling note:

```text
id_student is always excluded.
code_module and code_presentation are optional categorical predictors.
```

## 6. Missingness Summary

The final baseline files have 0 missing cells. Therefore, missingness should be analyzed through missing flag rates.

Calculate:

```python
missing_flag_cols = [c for c in df.columns if c.endswith("_missing")]
flag_rate = df[missing_flag_cols].mean()
```

Show cutoff trend for important flags:

- `mean_score_until_cutoff_missing`
- `weighted_score_until_cutoff_missing`
- `first_activity_date_until_cutoff_missing`
- `last_activity_date_until_cutoff_missing`
- `days_since_last_activity_at_cutoff_missing`
- `imd_band_missing`
- `date_registration_missing`

## 7. Feature-Target Dependency

This is the most important modeling-readiness section.

### Numeric Features

For each numeric predictor candidate:

| statistic | meaning |
|---|---|
| mean for target 0 | non-risk average |
| mean for target 1 | at-risk average |
| mean difference | direct target group difference |
| standardized difference | scale-adjusted group difference |
| correlation with target | linear association with target |

Recommended numeric features to highlight:

- `active_days_until_cutoff`
- `days_since_last_activity_at_cutoff`
- `total_click_until_cutoff_mean_strategy`
- `assessment_count_until_cutoff`
- `mean_score_until_cutoff`
- `weighted_score_until_cutoff`
- `avg_days_before_due_until_cutoff`

### Categorical Features

For categorical features, show category-level at-risk rate:

| feature | category | count | at-risk rate |
|---|---|---:|---:|
| `code_module` | module value | count | rate |
| `highest_education` | category value | count | rate |
| `imd_band` | category value | count | rate |

Association strength can be shown with Cramer's V. To stay within the project dependency constraints, compute it with pandas/numpy from a contingency table rather than adding scipy unless explicitly approved.

## 8. Feature-Feature Dependency

Focus on redundancy and obvious duplicate signal.

Numeric-numeric:

- Pearson correlation heatmap
- Spearman correlation heatmap

Pairs to inspect:

- `total_click_until_cutoff_mean_strategy` vs `active_days_until_cutoff`
- `mean_score_until_cutoff` vs `weighted_score_until_cutoff`
- `assessment_count_until_cutoff` vs `scored_assessment_count_until_cutoff`
- VLE activity-type click columns against each other

Categorical-categorical:

- Use Cramer's V for compact association summaries.
- Useful pairs: `code_module` vs `code_presentation`, `region` vs `imd_band`, `highest_education` vs `age_band`.

## 9. Cutoff Trend

Compare week5, week7, and week10.

Track:

| item | expected behavior |
|---|---|
| row count | decreases as later cutoffs exclude more pre-cutoff withdrawals |
| `assessment_count_until_cutoff` | usually increases |
| score availability | usually increases |
| `active_days_until_cutoff` | usually increases |
| `days_since_last_activity_at_cutoff` | may be higher for at-risk students |
| `target_at_risk` rate | changes because the active-at-cutoff cohort changes |

Suggested charts:

- line plot: cutoff별 numeric feature mean
- bar chart: cutoff별 target rate
- box plot: target별 numeric feature distribution

## 10. Modeling Guide

Required target:

```python
target_col = "target_at_risk"
```

Always exclude:

```python
always_drop_cols = [
    "target_at_risk",
    "target_withdrawn",
    "final_result",
    "id_student",
    "date_unregistration",
]
```

Optional categorical predictors:

```python
optional_cols = [
    "code_module",
    "code_presentation",
]
```

Notes:

- `date_unregistration` should not appear in the final baseline files, but keep it in the drop list as a guard.
- `code_module` and `code_presentation` may improve within-distribution prediction but can reduce claims about generalization to unseen modules or presentations.
- The current first baseline uses a strict two-feature setup:

```text
total_click_until_cutoff_mean_strategy
active_days_until_cutoff
```

## Split Strategy

Use two levels of validation:

| stage | split | purpose |
|---|---|---|
| first baseline | stratified split or `StratifiedKFold` | quick comparable baseline |
| robustness check | group split by `id_student` | generalization to unseen students |

Because some students appear in multiple rows, group-based validation should be added before making strong claims about performance on new students.

## Implementation Recommendation

Recommended artifact:

```text
notebooks/06_data_dashboard.ipynb
reports/modeling_ready_dashboard.html
```

Recommended libraries under current project rules:

```python
pandas
numpy
matplotlib
seaborn
```

Use `scikit-learn` only if mutual information or model-based checks are explicitly needed. Avoid adding new dependencies for the dashboard unless necessary.

## Deliverables

The dashboard work should produce:

```text
notebooks/06_data_dashboard.ipynb
reports/modeling_ready_dashboard.html
reports/modeling_dashboard_plan.md
```

The dashboard should make it possible for another researcher to answer:

1. What data file should I model from?
2. What is the target?
3. Which columns must be dropped?
4. How was the active-at-cutoff cohort defined?
5. What missingness was preserved through flags?
6. Which features show strong target dependency?
7. Which features may be redundant?
8. How do feature distributions change from week5 to week10?
9. What split strategy is appropriate for the modeling claim?
