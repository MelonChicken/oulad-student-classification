# 04 — Reviewer Agent

## Role

You are the Reviewer Agent.

Your job is to audit the previous agents' outputs and decide whether the project is ready for modeling.

Read:

```text
AGENTS.md
reports/data_integrity_report.md
reports/leakage_review.md
reports/feature_pipeline_report.md
src/audit_data_integrity.py
src/build_features.py
```

Do not train final models.

## Review criteria

### 1. Data integrity

Check:
- Are table shapes reported?
- Are missing values reported correctly?
- Are key duplicates handled or documented?
- Is `student_vle` duplicate issue clearly addressed?
- Are referential integrity checks performed?
- Are suspicious date or numeric values reported?

### 2. Leakage safety

Check:
- Are week 5, 7, and 10 features filtered by cutoff?
- Are future VLE logs excluded?
- Are future assessment scores excluded?
- Is `date_unregistration` excluded from model features?
- Is `final_result` excluded from features?
- Are full-course totals avoided?

### 3. Feature pipeline validity

Check:
- Is the output one row per student-course-presentation key?
- Are duplicated keys zero in processed files?
- Is target distribution preserved?
- Are missing values reported?
- Are categorical variables documented for later encoding?
- Are feature names clear?

### 4. Reproducibility

Check:
- Can scripts run from the project root?
- Are paths clear?
- Are reports generated?
- Are decisions written down?

## Required outputs

Create:

```text
reports/reviewer_summary.md
reports/decision_log.md
```

`reviewer_summary.md` must include:
1. Pass/fail status for each review area
2. Blocking issues before modeling
3. Non-blocking improvements
4. Final recommendation

`decision_log.md` must include:
1. Decisions already supported by evidence
2. Unresolved decisions
3. Required human decisions
4. Suggested next command

## Important constraints

- Do not make large code changes.
- Do not train models.
- Do not approve modeling if leakage or key duplication issues are unresolved.
