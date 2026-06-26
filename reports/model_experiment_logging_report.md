# Model Experiment Logging Report

## Scope

This script adds repeatable cross-validation experiment logging. It does not train or save a final production model.

## Output Files

- `data\report_tables\model_results\feature_engineering_grid_results.csv` stores every cutoff, feature set, model, and parameter-combination CV result.
- `data\report_tables\model_results\feature_engineering_best_results.csv` stores the F1-selected best parameter row for each executed experiment.

## Metrics

- precision
- recall
- f1
- roc_auc
- pr_auc
- accuracy

## Guardrails

- `id_student`, `final_result`, `target_withdrawn`, `target_at_risk`, and `date_unregistration` are excluded from automatic predictor sets.
- Mixed feature sets one-hot encode reviewed categorical columns inside the model pipeline only.
- Categorical missing values are encoded as `Unknown` inside the pipeline; raw feature CSVs are not modified.
- Result CSVs retain raw feature names and add shorter alias columns for tables and reports.
- Results are appended with a UTC `run_id`, so repeated runs remain auditable.
- Selection uses `GridSearchCV(refit='f1')`; this is a tuning comparison, not a final model artifact.

## Feature Set Aliases

| raw name | alias |
| --- | --- |
| `smoke_vle` | `vle_min` |
| `vle_core` | `vle_core` |
| `assessment_core` | `asm_core` |
| `static_numeric` | `stu_num` |
| `static_categorical` | `stu_cat` |
| `static_mixed` | `stu_all` |
| `vle_assessment_core` | `vle_asm` |
| `vle_assessment_static_mixed` | `vle_asm_stu` |
| `all_numeric_candidate` | `num_all` |
| `all_modeling_candidate` | `full_all` |
| `vle_activity_clicks` | `vle_activity` |
| `minimal_behavior` | `min_behavior` |
| `beh_early` | `beh_early` |
| `beh_count` | `beh_count` |
| `beh_last` | `beh_last` |
| `beh_early_count` | `beh_early_count` |
| `beh_early_last` | `beh_early_last` |
| `beh_count_last` | `beh_count_last` |
| `beh_all3` | `beh_all3` |
| `base_beh_early` | `base_beh_early` |
| `base_beh_count` | `base_beh_count` |
| `base_beh_last` | `base_beh_last` |
| `base_beh_early_count` | `base_beh_early_count` |
| `base_beh_early_last` | `base_beh_early_last` |
| `base_beh_count_last` | `base_beh_count_last` |
| `base_beh_all3` | `base_beh_all3` |
