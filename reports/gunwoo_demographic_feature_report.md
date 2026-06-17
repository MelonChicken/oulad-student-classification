# Gunwoo Demographic Feature Report

## Problem Definition

This analysis evaluates whether basic student demographic information can support early prediction of students at risk of withdrawal or failure in OULAD.

The focused research question is: how much predictive signal is contained in `gender`, `region`, and `age_band`, and how much does performance change when the two reviewed base activity features are added?

This problem is important because demographic features are available before the cutoff weeks and can be used as a low-cost comparison point against behavior-based features. At the same time, they need careful interpretation because they can reflect structural differences rather than actionable individual behavior.

## Data Collection & Preprocessing

- Source: Kaggle OULAD-derived baseline feature files created by the reviewed project pipeline.
- Expected inputs: `data/processed/features_week5_baseline.csv`, `data/processed/features_week7_baseline.csv`, and `data/processed/features_week10_baseline.csv`.
- Base unit: one row per `code_module`, `code_presentation`, `id_student` from `student_info`.
- Raw `?` values are parsed as missing before feature generation; raw CSV files are not overwritten.
- Target: `target_at_risk = 1` for `Withdrawn` or `Fail`, otherwise `0`.
- Leakage guard: `date_unregistration`, `final_result`, `target_withdrawn`, and `target_at_risk` are excluded from predictors.
- Categorical preprocessing: `gender`, `region`, and `age_band` are one-hot encoded inside the model pipeline with `handle_unknown='ignore'`.
- Numeric preprocessing: logistic regression standardizes base numeric features; tree models use raw numeric values.

## Feature Sets

- `demographic_only`: `gender`, `region`, `age_band`.
- `base_demographic`: `active_days_until_cutoff`, `total_click_until_cutoff_mean_strategy`, `gender`, `region`, `age_band`.

## Methodology & Model Justification

- Logistic regression is used as an interpretable linear baseline for sparse one-hot demographic variables.
- Decision tree is used to check simple non-linear splits and interactions between categorical groups.
- Random forest is used as a stronger non-linear benchmark while keeping the experiment lightweight.
- All reported metrics use stratified 5-fold cross-validation. No final production model artifact is saved.

## Results & Interpretation

### Key Findings

- Demographic-only models have weak but nonzero signal, with best ROC-AUC staying around 0.55 across week 5, week 7, and week 10.
- Adding the two reviewed base activity features gives a large and consistent lift over demographics alone.
- By week 10, the best `base_demographic` model reaches F1=0.6215 and ROC-AUC=0.7193, compared with F1=0.5025 and ROC-AUC=0.5550 for `demographic_only`.
- The practical implication is that demographic fields are useful as a baseline/context signal, but early LMS activity explains much more of the actionable withdrawal/failure risk.

### Best Model by Feature Set

| cutoff | feature_set | model | precision | recall | f1 | roc_auc | pr_auc | accuracy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| week5 | base_demographic | logistic_regression | 0.5547 | 0.6863 | 0.6135 | 0.6860 | 0.6335 | 0.6237 |
| week5 | demographic_only | random_forest | 0.4677 | 0.6011 | 0.5261 | 0.5552 | 0.4795 | 0.5287 |
| week7 | base_demographic | logistic_regression | 0.5546 | 0.6926 | 0.6159 | 0.7017 | 0.6439 | 0.6326 |
| week7 | demographic_only | random_forest | 0.4574 | 0.5944 | 0.5170 | 0.5544 | 0.4679 | 0.5276 |
| week10 | base_demographic | logistic_regression | 0.5549 | 0.7062 | 0.6215 | 0.7193 | 0.6552 | 0.6475 |
| week10 | demographic_only | random_forest | 0.4400 | 0.5856 | 0.5025 | 0.5550 | 0.4539 | 0.5247 |

### Base Feature Lift

| cutoff | model_demographic_only | f1_demographic_only | roc_auc_demographic_only | model_base_demographic | f1_base_demographic | roc_auc_base_demographic | f1_gain_from_base | roc_auc_gain_from_base |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| week10 | random_forest | 0.5025 | 0.5550 | logistic_regression | 0.6215 | 0.7193 | 0.1190 | 0.1643 |
| week5 | random_forest | 0.5261 | 0.5552 | logistic_regression | 0.6135 | 0.6860 | 0.0874 | 0.1308 |
| week7 | random_forest | 0.5170 | 0.5544 | logistic_regression | 0.6159 | 0.7017 | 0.0990 | 0.1473 |

The results show that `gender`, `region`, and `age_band` alone can separate risk groups only weakly. Performance improves substantially once `active_days_until_cutoff` and `total_click_until_cutoff_mean_strategy` are added, so the model is mostly learning from early engagement behavior rather than from static personal information.

## Limitations & Implications

- Demographic features are coarse and may encode social or institutional context, so they should not be used alone for high-stakes student decisions.
- Stratified cross-validation may place the same student in multiple folds across different module presentations; future evaluation should consider grouped validation by `id_student`.
- The experiment depends on the baseline feature files and inherits their reviewed VLE duplicate strategy and cohort rules.
- Future work should compare this part with the behavior and student-background branches using the same cutoffs, target, and validation policy.

## Execution Status

- Requested cutoffs: week5, week7, week10.
- Missing input files: none.
- Result table: `reports/tables/gunwoo_demographic_model_summary.csv`.
- Feature audit table: `reports/tables/gunwoo_demographic_feature_audit.csv`.
