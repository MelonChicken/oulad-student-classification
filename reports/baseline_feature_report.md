# Baseline Feature Report

## Scope

This report documents model-ready baseline feature CSV creation. No final models were trained.

## Decisions Applied

- `target_at_risk` is 1 for `final_result` in `{Withdrawn, Fail}` and 0 otherwise.
- `target_withdrawn` is preserved for auxiliary analysis and must be excluded from predictors.
- `date_unregistration` is not present in baseline outputs.
- VLE key duplicates are aggregated with mean `sum_click` at `code_module`, `code_presentation`, `id_student`, `id_site`, `date` before student-level summaries.
- Existing `_sum_strategy` and `_max_strategy` click columns are replaced by `_mean_strategy` columns.
- Assessment summaries exclude all `studentAssessment` rows whose `id_assessment` has missing `assessments.date`.
- `on_time_submission_count_until_cutoff` and `avg_days_before_due_until_cutoff` are derived from clean due-date assessment rows.
- `is_retake` is derived as `num_of_prev_attempts > 0`.
- Missing flags are added before filling selected numeric values with 0 and categorical values with `Unknown`.

## Validation Summary

| cutoff | cutoff_day | path | rows | columns | date_unregistration_present | duplicated_base_key_rows | target_at_risk_positive_rate | missing_flag_columns | non_binary_missing_flags | after_cutoff_feature_violations | missing_final_features | is_retake_positive_rate | remaining_missing_cells |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| week5 | 35 | data\processed\features_week5_baseline.csv | 27244 | 66 | False | 0 | 0.435289 | 12 |  |  |  | 0.126633 | 0 |
| week7 | 49 | data\processed\features_week7_baseline.csv | 26776 | 66 | False | 0 | 0.425418 | 12 |  |  |  | 0.126195 | 0 |
| week10 | 70 | data\processed\features_week10_baseline.csv | 26069 | 66 | False | 0 | 0.409835 | 12 |  |  |  | 0.12559 | 0 |
