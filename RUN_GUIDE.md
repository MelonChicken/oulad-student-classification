# Minimal Codex Agent Run Guide

This version keeps only the essential and effective agents.

## Why only four agents?

The project does not need many agents. The useful split is:

1. Data Integrity Agent
2. Leakage Guard Agent
3. Feature Pipeline Agent
4. Reviewer Agent

The main Codex session acts as the orchestrator. A separate Orchestrator Agent is unnecessary.

---

## Recommended first command

Run from the project root:

```powershell
cd C:\Users\osca0\Dev\studyDataMining\teamproject
```

Then:

```powershell
codex --ask-for-approval on-request "Read AGENTS.md. Do not edit files. Summarize the project goal, known risks, and required workflow."
```

---

## Stage 1 — Data integrity

```powershell
codex --ask-for-approval on-request "Read AGENTS.md and prompts/01_data_integrity_agent.md. Complete only this agent task. Do not build features or train models."
```

Expected outputs:

```text
src/audit_data_integrity.py
reports/data_integrity_report.md
reports/tables/
```

---

## Stage 2 — Leakage review

```powershell
codex --ask-for-approval on-request "Read AGENTS.md, reports/data_integrity_report.md, and prompts/02_leakage_guard_agent.md. Complete only this agent task. Do not build features or train models."
```

Expected output:

```text
reports/leakage_review.md
```

---

## Stage 3 — Feature pipeline

Only run this after Stage 1 and Stage 2 are complete.

```powershell
codex --ask-for-approval on-request "Read AGENTS.md, reports/data_integrity_report.md, reports/leakage_review.md, and prompts/03_feature_pipeline_agent.md. Complete only this agent task. Do not train final models."
```

Expected outputs:

```text
src/build_features.py
reports/feature_pipeline_report.md
data/processed/
```

---

## Stage 4 — Reviewer

```powershell
codex --ask-for-approval on-request "Read AGENTS.md, reports/data_integrity_report.md, reports/leakage_review.md, reports/feature_pipeline_report.md, and prompts/04_reviewer_agent.md. Review the work and write final recommendations. Do not train models."
```

Expected outputs:

```text
reports/reviewer_summary.md
reports/decision_log.md
```

---

## Optional parallel version

If Codex subagents are available and you want parallel inspection:

```text
Read AGENTS.md.

Use two read-only subagents in parallel:
1. Data Integrity Agent using prompts/01_data_integrity_agent.md
2. Leakage Guard Agent using prompts/02_leakage_guard_agent.md

Wait for both results.
Do not run feature engineering.
Summarize conflicts and unresolved decisions.
```

Do not run Feature Pipeline Agent in parallel with the first two agents.
Feature creation must wait until integrity and leakage rules are known.
