# Reviewer Summary

## Final Recommendation

Status: **Not ready for final modeling**.

The project has a usable audit trail and a reproducible cutoff-based feature pipeline, but modeling should remain blocked until the unresolved leakage and data-treatment decisions below are made. This is consistent with `AGENTS.md`: final models must not be trained until data integrity, leakage rules, and feature rules are reviewed and unresolved decisions are closed.

## Review Area Status

| area | status | review |
| --- | --- | --- |
| Data integrity | Pass with blockers | Required table shapes, missing values, key checks, `student_vle` duplicate analysis, referential integrity checks, date/numeric range checks, and target distributions are reported. Modeling remains blocked because `student_vle` key-duplicate treatment is unresolved and referential mismatches remain documented but not resolved. |
| Leakage safety | Pass with blockers | Cutoff rules for days 35, 49, and 70 are defined. `date_unregistration` is marked unsafe as a predictor. Future VLE and assessment rows are excluded in the feature script. Modeling remains blocked because active-at-cutoff cohort design and target timing are unresolved. |
| Feature pipeline validity | Pass with blockers | Outputs have one row per `code_module`, `code_presentation`, `id_student`; duplicated base keys are zero; target distribution is preserved; missing values are reported; categorical values are kept raw for later encoding. Modeling remains blocked because `final_result` is retained in the processed files for analysis and must be explicitly excluded by a predictor manifest before any training script is allowed. |
| Reproducibility | Pass | Scripts are runnable from the project root, paths are explicit, reports are generated, and feature decisions are logged in `reports/decision_log.md`. |

## Blocking Issues Before Modeling

1. `student_vle` duplicate strategy is unresolved.
   - Evidence: after exact duplicate removal, `1,408,790` duplicate key rows remain across `1,179,074` duplicated key groups.
   - All duplicated key groups after exact duplicate removal have differing `sum_click` values.
   - The feature pipeline emits both sum and max strategy variants, which is appropriate for analysis, but final modeling must choose one reviewed strategy or define a model comparison plan that treats the strategy as an experimental condition.

2. Target timing and cohort definition are unresolved.
   - Evidence: withdrawn students already unregistered by cutoff: `5,341` by day 35, `5,809` by day 49, and `6,516` by day 70.
   - A prospective early-warning model should not train on already-withdrawn students as ordinary at-risk examples without an explicit design choice.
   - Human decision required: model "eventual withdrawal among active-at-cutoff students" or "withdrawal after cutoff only".

3. `date_unregistration` must remain excluded from predictors.
   - The feature outputs correctly omit `date_unregistration`.
   - It may be used only to define cohorts/evaluation timing.

4. `final_result` is present in processed outputs for analysis.
   - This is allowed by the feature prompt, but it is unsafe as a predictor.
   - Before modeling, create a predictor-column manifest or training script guard that excludes `final_result`, `target_withdrawn`, base keys, and any non-predictor analysis columns from `X`.

5. Missing-value treatment is unresolved.
   - Missing values remain for `imd_band`, `date_registration`, `is_registered_before_start`, score summaries, weighted score, and activity-date summaries.
   - This is acceptable for the current feature pipeline stage, but modeling requires an explicit imputation/encoding plan.

6. Assessment due-date and weighted-score assumptions need approval.
   - `submitted_late_count_until_cutoff` depends on available `assessments.date`.
   - `weighted_score_until_cutoff` assumes `assessments.weight` is safe static course metadata.
   - These assumptions should be approved before treating those columns as final predictors.

7. Referential mismatches remain unresolved.
   - `student_vle -> student_info` has `3,365` right-only student-course-presentation keys in the audit framing.
   - `student_assessment -> assessments` has `18` right-only assessment IDs.
   - `student_vle -> vle` has `96` right-only site IDs.
   - These are not necessarily leakage, but final modeling should document whether unmatched metadata affects selected features.

## Non-Blocking Improvements

- Add a small validation script that loads each processed CSV and asserts:
  - zero duplicated base keys,
  - no `date_unregistration`,
  - no future VLE or assessment evidence,
  - expected target distribution,
  - predictor manifest excludes leakage columns.
- Add model-ready schema files for each cutoff listing:
  - key columns,
  - analysis-only columns,
  - target column,
  - allowed predictor columns.
- Compare Kaggle and official OULAD row counts and key sets for all tables, then decide whether Kaggle-only outputs are acceptable.
- Add explicit missing-value indicators where analytically justified, especially for `imd_band`, no VLE activity by cutoff, and no assessment submissions by cutoff.
- Add cohort-count reports for active-at-cutoff rows once the target timing decision is made.

## Evidence Reviewed

- `reports/data_integrity_report.md`
- `reports/leakage_review.md`
- `reports/feature_pipeline_report.md`
- `src/audit_data_integrity.py`
- `src/build_features.py`

## Modeling Gate

Do not train final models yet.

Modeling can start only after:

1. VLE duplicate strategy is approved.
2. Active-at-cutoff cohort and target timing are approved.
3. Missing-value and categorical-encoding rules are approved.
4. Predictor manifest excludes leakage and analysis-only columns.
5. Any selected conditional features, such as weighted scores or late-submission counts, are explicitly approved.
