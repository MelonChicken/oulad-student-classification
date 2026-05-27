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
- Unresolved: Missing-value treatment for model-ready matrices is not finalized.
- Unresolved: Final VLE duplicate strategy is not finalized.
- Unresolved: Active-at-cutoff cohort treatment is not finalized.

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

- Unresolved: Final `student_vle` duplicate strategy is not chosen.
- Unresolved: Active-at-cutoff cohort design is not chosen.
- Unresolved: Target timing definition is not chosen: eventual withdrawal among active-at-cutoff students versus withdrawal after cutoff only.
- Unresolved: Missing-value treatment for model-ready inputs is not chosen.
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
