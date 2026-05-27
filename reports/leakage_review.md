# Leakage Review

## Scope

This review covers leakage rules for early withdrawal prediction at these candidate cutoffs:

| cutoff | day |
| --- | ---: |
| week 5 | 35 |
| week 7 | 49 |
| week 10 | 70 |

Target candidate: `Withdrawn = 1`, `Pass / Fail / Distinction = 0`.

No features were built. No models were trained. No raw data was modified.

## Integrity Context Used

The data integrity report found that `student_vle` has duplicate key rows after exact duplicate removal and that all remaining duplicated key groups have different `sum_click` values. Any future VLE feature work must resolve that before click features are finalized.

The integrity report also found unmatched keys in referential checks:

| check | both | left_only | right_only |
| --- | ---: | ---: | ---: |
| `student_info` to `student_registration` | 32593 | 0 | 0 |
| `student_vle` to `student_info` | 29228 | 0 | 3365 |
| `student_assessment` to `assessments` | 188 | 0 | 18 |
| `student_vle` to `vle` | 6268 | 0 | 96 |

These are join-integrity risks, not leakage rules by themselves, but they affect whether future feature joins can be trusted.

## Leakage Risk Table

| table | variable or derived value | classification | rule |
| --- | --- | --- | --- |
| `studentInfo` | `final_result` | Always unsafe as predictor | Use only to define/evaluate the target. Never include in model inputs. |
| `studentRegistration` | `date_unregistration` | Always unsafe as predictor | This directly reveals withdrawal timing. Use only for cohort and evaluation design. |
| `studentVle` | rows where `date > cutoff_day` | Always unsafe for that cutoff | Exclude before any aggregation or click summary. |
| `studentAssessment` | rows where `date_submitted > cutoff_day` | Always unsafe for that cutoff | Exclude before any assessment summary. |
| derived | full-course total clicks | Always unsafe | Includes future VLE activity after the cutoff. |
| derived | full-course assessment summaries | Always unsafe | Includes future submissions and scores after the cutoff. |
| `studentAssessment` | `score` | Safe if filtered by cutoff date | Use only where `date_submitted <= cutoff_day`; missing scores need documented handling. |
| `studentAssessment` | `date_submitted` | Safe if filtered by cutoff date | Use only for submissions already observed by the cutoff. |
| `studentAssessment` | `is_banked` | Conditionally safe | Safe only for already observed submissions and if the meaning is reviewed; may encode prior-course credit behavior. |
| `assessments` | `date` | Conditionally safe | Due dates may be known in advance, but missing dates must not be imputed silently. If used to validate submission timing, missing dates are unresolved. |
| `assessments` | `weight` | Conditionally safe | Usually schedule metadata, but only safe if known to students before the cutoff and not used to infer future completion. |
| `assessments` | `assessment_type` | Conditionally safe | Usually static assessment design; safe only as metadata, not as a proxy for future submissions. |
| `studentVle` | `sum_click` | Safe if filtered by cutoff date | Use only where `date <= cutoff_day`, and only after the duplicate treatment is reviewed. |
| `studentVle` | `date` | Safe if filtered by cutoff date | Use for temporal filtering. Future rows are unsafe. |
| `vle` | `activity_type` | Conditionally safe | Static content metadata, but only for joined VLE rows that survive cutoff filtering. |
| `vle` | `week_from`, `week_to` | Conditionally safe | Many values are missing. Treat as content-release metadata only; do not infer unobserved future activity. |
| `studentRegistration` | `date_registration` | Conditionally safe | Can describe enrollment timing known by cutoff, but students not registered by cutoff need an explicit cohort rule. |
| `studentInfo` | `gender`, `region`, `highest_education`, `imd_band`, `age_band`, `num_of_prev_attempts`, `studied_credits`, `disability` | Safe static variables | Usually available before/at registration. Missing handling, especially `imd_band`, must be documented. |
| `courses` | `module_presentation_length` | Safe static variable | Course metadata, assumed known before the course; do not use it to justify future activity windows. |
| keys | `code_module`, `code_presentation`, `id_student`, `id_site`, `id_assessment` | Not predictors by default | Use for joins and grouping. Do not use student IDs as predictive variables. |

## Safe Variables by Cutoff

The same rule applies at each cutoff: include only information available on or before the cutoff day.

| cutoff | allowed `student_vle` rows | allowed `student_assessment` rows | allowed `assessments` rows | allowed `student_registration` use |
| --- | --- | --- | --- | --- |
| week 5, day 35 | `student_vle.date <= 35` | `studentAssessment.date_submitted <= 35` | Assessment metadata may be joined for already observed submissions; due-date use must handle missing `assessments.date` | `date_registration` may support cohort checks; `date_unregistration` is not a feature |
| week 7, day 49 | `student_vle.date <= 49` | `studentAssessment.date_submitted <= 49` | Assessment metadata may be joined for already observed submissions; due-date use must handle missing `assessments.date` | `date_registration` may support cohort checks; `date_unregistration` is not a feature |
| week 10, day 70 | `student_vle.date <= 70` | `studentAssessment.date_submitted <= 70` | Assessment metadata may be joined for already observed submissions; due-date use must handle missing `assessments.date` | `date_registration` may support cohort checks; `date_unregistration` is not a feature |

Timing evidence from the raw Kaggle tables:

| cutoff_day | `student_vle` allowed rows | `student_vle` future rows | `student_assessment` allowed rows | `student_assessment` future rows | assessment due-date allowed | assessment due-date future | assessment due-date missing |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 35 | 3253906 | 7401374 | 30533 | 143379 | 22 | 173 | 11 |
| 49 | 3982172 | 6673108 | 41507 | 132405 | 29 | 166 | 11 |
| 70 | 4880182 | 5775098 | 61445 | 112467 | 49 | 146 | 11 |

## Unsafe Variables

These must not enter the model input matrix:

- `final_result`
- `date_unregistration`
- Any flag derived from `date_unregistration`, such as "already withdrawn by cutoff", if used as a predictor
- `student_vle` rows after the cutoff
- `student_assessment` rows after the cutoff
- Scores from submissions after the cutoff
- Full-course total clicks
- Full-course assessment counts, means, pass rates, missing-submission counts, or any summary computed without cutoff filtering
- Raw `id_student` as a predictive variable

## Conditional Variables

These may be usable only with explicit rules:

| variable | condition |
| --- | --- |
| `score` | Use only for submissions with `date_submitted <= cutoff_day`. Missing `score` must be reported and handled by a documented rule. |
| `is_banked` | Use only after reviewing whether banked assessment status is available at or before the cutoff and whether it encodes previous-course transfer behavior. |
| `assessments.date` | Do not silently fill 11 missing dates. If due date is needed, either exclude due-date-derived logic for missing rows or define a reviewed missing-date rule. |
| `assessments.weight` | Safe only as known course design metadata. Do not use future submission outcomes attached to it. |
| `vle.week_from`, `vle.week_to` | Treat as metadata only. Missingness is high, so any use must be documented and reviewed. |
| `date_registration` | Safe only for cohort design and registration-timing features known by cutoff. Students with registration after cutoff need a rule. |
| `imd_band` | Static, but 1111 missing values require documented missing handling. |
| `student_vle.sum_click` | Must first filter `student_vle.date <= cutoff_day`, then resolve duplicate treatment before aggregating. |

## Target Timing Issue

`date_unregistration` shows that many `Withdrawn` outcomes occurred before each cutoff:

| cutoff_day | withdrawn total | withdrawn on or before cutoff | withdrawn after cutoff | withdrawn missing `date_unregistration` | non-withdrawn with unregistration on or before cutoff | active at cutoff if pre-cutoff unregistrations are excluded |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 35 | 10156 | 5341 | 4722 | 93 | 8 | 27244 |
| 49 | 10156 | 5809 | 4254 | 93 | 8 | 26776 |
| 70 | 10156 | 6516 | 3547 | 93 | 8 | 26069 |

For an early warning model run at a cutoff, students who already withdrew on or before that cutoff are no longer a prospective prediction case. Including them as positive examples while also using cutoff-time behavioral data can turn the task into recognizing an event that has already happened.

Recommended target design:

- Define the risk set separately for each cutoff.
- Exclude students with `date_unregistration <= cutoff_day` from the prospective prediction cohort, or report them in a separate "already withdrawn before cutoff" cohort.
- Within the active-at-cutoff cohort, use `final_result == "Withdrawn"` as the candidate positive target, subject to resolving missing or inconsistent `date_unregistration`.
- Use `date_unregistration` only for cohort construction and evaluation design, never as a model feature.
- Build the feature matrix only after target/cohort labels are assigned outside the predictors, so the answer is not used as an input.

Unresolved target cases:

- 93 students have `final_result == "Withdrawn"` but missing `date_unregistration`.
- 8 non-withdrawn students have `date_unregistration <= cutoff_day` at each cutoff count above.
- The project must decide whether the target is "eventual final_result is Withdrawn among students active at cutoff" or "withdrawal after cutoff only". These are related but not identical.

## Assessment Feature Leakage Rules

For each cutoff, assessment evidence must satisfy:

```python
studentAssessment.date_submitted <= cutoff_day
```

Rules:

- Join `studentAssessment` to `assessments` by `id_assessment` only after checking unmatched assessment IDs.
- Do not use any `score` where `date_submitted > cutoff_day`.
- Do not create summaries over all course assessments unless the summary uses only submissions observed by the cutoff.
- If using assessment due dates, do not silently impute the 11 missing `assessments.date` values.
- Missing `score` values are not a reason to drop rows silently; they need a documented rule.

## VLE Feature Leakage Rules

For each cutoff, VLE evidence must satisfy:

```python
student_vle.date <= cutoff_day
```

Rules:

- Filter by cutoff before any aggregation.
- Full-course total clicks are unsafe.
- Joining `student_vle` to `vle` should be done after reviewing the `id_site` unmatched keys from the integrity report.
- Do not finalize click features until the `student_vle` duplicate treatment is decided. The integrity report shows exact duplicates and remaining key duplicates with differing `sum_click` values.

## Static Demographic Features

These are usually safe because they should be known at or before registration:

- `gender`
- `region`
- `highest_education`
- `imd_band`
- `age_band`
- `num_of_prev_attempts`
- `studied_credits`
- `disability`

Rules:

- Treat them as static candidate predictors.
- Do not drop missing demographic rows silently.
- Document missing handling before feature construction, especially for `imd_band`.
- Avoid using raw `id_student` as a predictor.

## Recommended Filtering Rules

For every cutoff-specific dataset in later stages:

1. Start from `studentInfo` as the base student-course-presentation unit.
2. Assign target and cohort labels outside the feature columns.
3. Apply the cutoff to event/activity tables before aggregation:
   - `studentVle.date <= cutoff_day`
   - `studentAssessment.date_submitted <= cutoff_day`
4. Never include `final_result` or `date_unregistration` in predictor columns.
5. Use `date_unregistration` only to define the active-at-cutoff risk set and evaluation timing.
6. Do not use full-course totals or summaries.
7. Do not drop rows because of missing values, unmatched joins, or duplicate VLE keys without a logged decision.
8. Keep separate outputs and checks for day 35, day 49, and day 70.

## Open Decisions

- Whether to exclude pre-cutoff withdrawals from each cutoff model or keep them in a separately reported cohort.
- Whether the positive target means "eventual `final_result == Withdrawn` among active-at-cutoff students" or strictly "withdrawal after the cutoff".
- How to handle 93 withdrawn records with missing `date_unregistration`.
- How to handle 8 non-withdrawn records with `date_unregistration` on or before the cutoff.
- How to handle missing `assessments.date`, missing `studentAssessment.score`, missing `date_registration`, and missing `imd_band`.
- How to treat `student_vle` exact duplicates and remaining key duplicates before any click aggregation.
- Whether `is_banked`, `vle.week_from`, and `vle.week_to` should be used at all.
- Whether course metadata such as `module_presentation_length` is allowed as a predictor or should remain descriptive only.
