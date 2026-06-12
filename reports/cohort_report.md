# Cohort Report

## Scope

This report documents active-at-cutoff cohort construction. Raw data files were not modified.

## Cohort Rule

Rows are retained when:

```python
(date_registration.isna() or date_registration <= cutoff_day) and
(date_unregistration.isna() or date_unregistration > cutoff_day)
```

`date_unregistration` is used only for cohort construction and is not written to cohort outputs.
Rows with missing `date_registration` are retained because registration status cannot be confirmed and the count is small; downstream baseline outputs keep missing flags.

## Output Files

| cutoff | cutoff_day | input_rows | output_rows | excluded_rows | late_registration_excluded | pre_cutoff_unregistration_excluded | both_late_and_unregistered_excluded | missing_date_registration_retained | date_unregistration_present | duplicated_base_key_rows | target_distribution | path |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| week5 | 35 | 32593 | 27229 | 5364 | 15 | 5349 | 0 | 7 | False | 0 | Distinction: 3024, Fail: 7037, Pass: 12356, Withdrawn: 4812 | data\processed\features_week5_cohort.csv |
| week7 | 49 | 32593 | 26767 | 5826 | 9 | 5817 | 0 | 7 | False | 0 | Distinction: 3024, Fail: 7039, Pass: 12358, Withdrawn: 4346 | data\processed\features_week7_cohort.csv |
| week10 | 70 | 32593 | 26062 | 6531 | 7 | 6524 | 0 | 7 | False | 0 | Distinction: 3024, Fail: 7040, Pass: 12359, Withdrawn: 3639 | data\processed\features_week10_cohort.csv |
