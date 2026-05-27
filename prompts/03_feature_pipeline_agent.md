# 03 — Feature Pipeline Agent

## Role

You are the Feature Pipeline Agent.

Your job is to implement a leakage-safe feature engineering pipeline only after data integrity and leakage rules are available.

Read first:

```text
reports/data_integrity_report.md
reports/leakage_review.md
```

Do not train final models.

## Required base unit

Use one row per:

```python
["code_module", "code_presentation", "id_student"]
```

Base table:

```text
student_info
```

## Required feature groups

### 1. Static student features

From `student_info`:
- gender
- region
- highest_education
- imd_band
- age_band
- num_of_prev_attempts
- studied_credits
- disability
- code_module
- code_presentation

Do not encode inside this script unless clearly necessary.
Keep raw categorical values and document future encoding plan.

### 2. Registration features

Allowed:
- `date_registration`
- `is_registered_before_start` if derived from `date_registration`

Do not use `date_unregistration` as a model feature unless the leakage review explicitly allows it.
Usually it should not be used as a feature.

### 3. VLE features by cutoff

For each cutoff:

```text
35, 49, 70
```

Create features using only:

```python
student_vle.date <= cutoff_day
```

Candidate features:
- total_click_until_cutoff
- active_days_until_cutoff
- used_site_count_until_cutoff
- avg_click_per_active_day_until_cutoff
- first_activity_date_until_cutoff
- last_activity_date_until_cutoff
- days_since_last_activity_at_cutoff
- click_count_by_activity_type if joined with `vle`

Important:
- Use the duplicate strategy recommended or unresolved in `data_integrity_report.md`.
- If duplicate strategy is unresolved, implement both `sum` and `max` versions or write a clear TODO.

### 4. Assessment features by cutoff

For each cutoff:

```text
35, 49, 70
```

Use only:

```python
student_assessment.date_submitted <= cutoff_day
```

Candidate features:
- assessment_count_until_cutoff
- mean_score_until_cutoff
- min_score_until_cutoff
- max_score_until_cutoff
- submitted_late_count_until_cutoff if due date is available
- weighted_score_until_cutoff if weight information is available and safe

Do not use future scores.

### 5. Target

Create:

```python
target_withdrawn = (final_result == "Withdrawn").astype(int)
```

Keep original `final_result` for analysis, but do not use it as a feature.

## Required outputs

Create:

```text
src/build_features.py
reports/feature_pipeline_report.md
data/processed/
```

Recommended output files:

```text
data/processed/features_week5.csv
data/processed/features_week7.csv
data/processed/features_week10.csv
```

Each output should have one row per student-course-presentation key.

## Required validation

For each output file, print:
- shape
- duplicated base key count
- target distribution
- missing value summary
- columns created
- whether any feature was created using data after cutoff

## Important constraints

- Do not train final models.
- Do not silently drop students.
- Do not use `date_unregistration` as a predictor unless explicitly approved.
- Do not use full-course totals for early prediction.
