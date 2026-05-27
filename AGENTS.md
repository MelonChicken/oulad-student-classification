# AGENTS.md — OULAD Data Mining Project

## Project goal

Build a reliable data mining pipeline for the OULAD project.

Current goal:
- Early prediction of student withdrawal
- Candidate prediction cutoffs: week 5, week 7, week 10
- Main data source: Kaggle OULAD, checked against official OULAD
- Main risk areas:
  - `student_vle` duplicate structure
  - data leakage from future activity, scores, and unregistration information
  - incorrect table joins

## Non-negotiable rules

1. Do not train final models until data integrity, leakage rules, and feature rules are reviewed.
2. Do not overwrite raw data files.
3. Do not silently drop rows.
4. Every data-cleaning decision must be written to `reports/decision_log.md`.
5. Every script must print enough evidence to support the report.
6. Prefer small, reproducible scripts over large notebooks.
7. Use `student_info` as the base student-course-presentation unit:
   - `code_module`
   - `code_presentation`
   - `id_student`

## Required folders

Create these if missing:

```text
src/
reports/
reports/tables/
```

## Coding style

- Use Python, pandas, numpy, matplotlib/seaborn only unless necessary.
- Keep scripts runnable from the project root.
- Use clear file names.
- Do not create hidden assumptions.
- Report unresolved issues explicitly.

## Known issue already found

`student_vle` has duplicate problems.

Observed:

```text
total rows: 10,655,280
exact duplicated rows: 787,170
duplicated by key: 2,195,960
```

Key used:

```python
["code_module", "code_presentation", "id_student", "id_site", "date"]
```

After exact duplicate removal, remaining key duplicates still exist and often have different `sum_click` values.

This must not be ignored when building click-based features.
