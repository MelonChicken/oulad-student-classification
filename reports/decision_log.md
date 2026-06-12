# Decision Log

## Feature Pipeline Agent

- Decision: Raw data files were not modified.
- Decision: Feature outputs are written to `data/processed/` as derived artifacts.
- Decision: `studentInfo.csv` is the base table, using one row per `code_module`, `code_presentation`, `id_student`.
- Decision: `date_unregistration` is excluded from feature outputs because the leakage review marks it unsafe as a predictor.
- Decision: VLE rows are filtered by cutoff before aggregation.
- Decision: Assessment rows are filtered by cutoff before aggregation.
- Decision: Exact duplicate rows in `studentVle.csv` are removed inside the feature script before VLE aggregation. This is a derived-pipeline step only; raw data is unchanged.
- Decision: Remaining `student_vle` key-duplicate treatment is unresolved, so both sum and max click aggregation variants are emitted.
- Decision: Count-like missing values after left joins are filled with 0 to preserve all base students while representing no observed cutoff activity.
- Superseded: Missing-value treatment for model-ready matrices was later finalized by the Baseline Feature Agent.
- Superseded: Final VLE duplicate strategy was later set to mean aggregation for the first baseline.
- Superseded: Active-at-cutoff cohort treatment was later finalized by the Cohort Revision Agent.

## Reviewer Agent

### Decisions Already Supported by Evidence

- Decision: The project is not ready for final modeling.
- Decision: The generated feature files preserve one row per `code_module`, `code_presentation`, `id_student` with zero duplicated base-key rows.
- Decision: `date_unregistration` is excluded from processed feature outputs and must remain excluded from predictors.
- Decision: Cutoff-specific VLE features are based on `studentVle.date <= cutoff_day`.
- Decision: Cutoff-specific assessment features are based on `studentAssessment.date_submitted <= cutoff_day`.
- Decision: Raw categorical values are retained for later encoding.
- Decision: `final_result` is analysis-only and must not be used as a predictor.

### Unresolved Decisions

- Superseded: Final `student_vle` duplicate strategy was later set to mean aggregation for the first baseline.
- Superseded: Active-at-cutoff cohort design was later finalized by the Cohort Revision Agent.
- Superseded: Target was later set to `target_at_risk`, where `Withdrawn` or `Fail` is positive.
- Superseded: Missing-value treatment for model-ready inputs was later finalized by the Baseline Feature Agent.
- Unresolved: Final categorical encoding plan is not chosen.
- Unresolved: Conditional feature approval is not complete for weighted score, late submission counts, `is_banked`, VLE release-week metadata, and course-length metadata.

### Required Human Decisions

- Choose the final VLE duplicate strategy: sum, max, or another reviewed rule.
- Choose whether to exclude students already withdrawn by each cutoff from the modeling risk set.
- Choose how to handle 93 withdrawn records with missing `date_unregistration`.
- Choose how to handle non-withdrawn records with `date_unregistration`.
- Choose missing-value and categorical-encoding rules for model-ready matrices.
- Approve or reject conditional assessment and metadata features before modeling.

### Suggested Next Command

```powershell
python src\build_features.py
```

After the required human decisions are made, add a separate validation or modeling-prep script that creates an explicit predictor-column manifest. Do not train final models until that manifest is reviewed.

## Baseline Feature Agent

- Decision: Created `data/processed/features_week{5,7,10}_baseline.csv` from cohort feature files without modifying raw data.
- Decision: `target_at_risk = 1` when `final_result` is `Withdrawn` or `Fail`; otherwise `0`.
- Decision: `final_result`, `target_withdrawn`, `target_at_risk`, `id_student`, and `date_unregistration` must be excluded from predictor matrices. `code_module` and `code_presentation` may be used as categorical predictors depending on the modeling goal.
- Decision: VLE duplicate handling uses key-level mean `sum_click` from original `studentVle.csv`; existing `_sum_strategy` and `_max_strategy` click columns are replaced by `_mean_strategy` columns.
- Decision: Assessment rows for the 11 missing-due-date `assessment_id` values are excluded before computing cutoff assessment summaries.
- Decision: Selected missing-prone fields get `{column}_missing` indicators before numeric zero fill or categorical `Unknown` fill.
- Decision: `date_unregistration` remains excluded from baseline outputs.
- Unresolved: Whether to use banked assessment metadata, VLE release-week metadata, module-presentation length, grouped activity dimensions, or alternate score imputations remains deferred until after first baseline review.

## Cohort Revision Agent

- Decision: Active-at-cutoff cohort now requires registration on or before each cutoff, unless `date_registration` is missing.
- Decision: Active-at-cutoff cohort retains rows only when `date_registration <= cutoff_day` or missing, and `date_unregistration > cutoff_day` or missing.
- Decision: `date_unregistration` is used only for cohort construction and is not written to cohort or baseline outputs.
- Decision: Rows with missing `date_registration` are retained in the baseline cohort with missing flags because the count is small and registration status cannot be confirmed.

## Model Experiment Logging Agent

- Decision: Grid-search experiment outputs are appended to `data/report_tables/model_results/feature_engineering_grid_results.csv`.
- Decision: F1-selected best rows are appended to `data/report_tables/model_results/feature_engineering_best_results.csv`.
- Decision: Tuning runs use stratified 5-fold cross-validation with `RANDOM_STATE = 724` and save precision, recall, F1, ROC-AUC, PR-AUC, and accuracy.
- Decision: `id_student`, `final_result`, `target_withdrawn`, `target_at_risk`, and `date_unregistration` are excluded from automatic predictor feature sets.
- Decision: Reviewed categorical predictors can be included through pipeline-only one-hot encoding; raw feature CSV files are not modified.
- Decision: Categorical missing values are encoded as `Unknown` inside the experiment pipeline.
- Decision: Experiment result CSVs keep raw feature names and add shorter alias columns for reporting readability.
- Unresolved: Final categorical feature approval and final model selection remain open; these tuning outputs are not final model artifacts.
