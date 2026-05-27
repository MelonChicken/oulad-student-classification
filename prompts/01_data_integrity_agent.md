# 01 — Data Integrity Agent

## Role

You are the Data Integrity Agent.

Your job is to verify whether the OULAD tables can be safely used and merged.

Do not create final features.
Do not train models.
Do not overwrite raw data.

## Inputs

Use the project data files already available in the repository.

Expected tables:

```text
courses.csv
assessments.csv
vle.csv
studentInfo.csv
studentRegistration.csv
studentAssessment.csv
studentVle.csv
```

## Required checks

### 1. Table shape check

Print and report the shape of each table.

### 2. Missing value check

For each table, report:
- missing count
- missing ratio
- columns with nonzero missing values only

Pay special attention to:
- `assessments.date`
- `vle.week_from`
- `vle.week_to`
- `student_info.imd_band`
- `student_registration.date_registration`
- `student_registration.date_unregistration`
- `student_assessment.score`

### 3. Key uniqueness check

Check these keys:

```python
{
    "courses": ["code_module", "code_presentation"],
    "assessments": ["id_assessment"],
    "vle": ["id_site"],
    "student_info": ["code_module", "code_presentation", "id_student"],
    "student_registration": ["code_module", "code_presentation", "id_student"],
    "student_assessment": ["id_assessment", "id_student"],
    "student_vle": ["code_module", "code_presentation", "id_student", "id_site", "date"]
}
```

For each table, report duplicated count.

### 4. `student_vle` duplicate analysis

Use:

```python
vle_key = ["code_module", "code_presentation", "id_student", "id_site", "date"]
```

Report:
- total rows
- exact duplicate rows
- key duplicate rows
- rows after exact duplicate removal
- remaining key duplicates after exact duplicate removal
- number of duplicated key groups
- distribution of duplicated group sizes
- whether duplicated key groups have different `sum_click` values

Do not decide final treatment yet.
Only provide evidence and options.

Compare:
- raw total clicks
- total clicks after exact duplicate removal
- total clicks after key aggregation by `sum`
- total clicks after key aggregation by `max`

### 5. Referential integrity check

Check:
- `student_info` → `student_registration` on student-course-presentation key
- `student_vle` → `student_info` on student-course-presentation key
- `student_assessment` → `assessments` on `id_assessment`
- `student_vle` → `vle` on `id_site`

Report `both`, `left_only`, `right_only` counts where applicable.

### 6. Date and numeric range check

Report descriptive statistics for:
- `student_registration.date_registration`
- `student_registration.date_unregistration`
- `student_assessment.date_submitted`
- `student_assessment.score`
- `student_vle.date`
- `student_vle.sum_click`
- `assessments.date`
- `assessments.weight`

Flag impossible or suspicious values.

### 7. Target distribution

Report:
- overall `final_result` counts and ratios
- `final_result` by `code_module`
- `final_result` by `code_presentation`
- `final_result` by module-presentation pair

## Required outputs

Create:

```text
src/audit_data_integrity.py
reports/data_integrity_report.md
reports/tables/
```

The report must include:

1. Findings
2. Evidence tables or printed values
3. Risks
4. Recommended next checks
5. Unresolved decisions

## Important constraints

- Do not drop rows permanently.
- Do not save cleaned data yet.
- Do not perform modeling.
- Do not make unsupported claims.
