# Minimal Behavior Experiment Notebook Guidelines

## Scope

Use `notebooks/model_experiment_feature_summary.ipynb` for the focused experiment.

This experiment uses three student behavior features and their combinations:

| Alias | Raw column | Meaning |
| --- | --- | --- |
| `asm_days_early_mean` | `avg_days_before_due_until_cutoff` | How early submissions were made relative to due dates |
| `asm_count` | `assessment_count_until_cutoff` | Number of assessment submissions observed by cutoff |
| `vle_last_day` | `last_activity_date_until_cutoff` | Last observed VLE access/activity day by cutoff |

The experiment plan has two stages:

1. Behavior-only combinations: `3C1 + 3C2 + 3C3`
2. The same combinations with base features added

Base features:

| Alias | Raw column | Meaning |
| --- | --- | --- |
| `vle_click_total` | `total_click_until_cutoff_mean_strategy` | Total VLE clicks by cutoff |
| `vle_active_days` | `active_days_until_cutoff` | Active VLE days by cutoff |

Do not add wider feature sets unless a new decision is documented.

## Inputs

Required files:

```text
data/processed/features_week5_baseline.csv
data/processed/features_week7_baseline.csv
data/processed/features_week10_baseline.csv
src/run_model_experiments.py
```

## Notebook Flow

Run the notebook in this order:

1. Setup
2. Experiment configuration
3. Feature definition check
4. Input validation summary
5. Experiment plan
6. Completed combination check
7. Run modeling
8. Load results
9. Evaluation table
10. Best model by cutoff
11. Interpretation notes

## Execution Rule

Keep this until the plan and validation tables look correct:

```python
RUN_EXPERIMENTS = False
```

To run models:

```python
RUN_EXPERIMENTS = True
SKIP_COMPLETED = True
```

`SKIP_COMPLETED = True` prevents rerunning combinations already saved in `best_results`.

## Experiment Cases

The notebook runs:

```text
3 cutoffs x 1 feature set x selected models
```

Default cutoffs:

```text
week5, week7, week10
```

Default feature sets:

```text
beh_early
beh_count
beh_last
beh_early_count
beh_early_last
beh_count_last
beh_all3
base_beh_early
base_beh_count
base_beh_last
base_beh_early_count
base_beh_early_last
base_beh_count_last
base_beh_all3
```

Default models:

```text
GaussianNB
LogisticRegression
DecisionTreeClassifier
RandomForestClassifier
KNeighborsClassifier
SVC
```

## Outputs

Results are stored in:

```text
data/report_tables/model_results/feature_engineering_grid_results.csv
data/report_tables/model_results/feature_engineering_best_results.csv
```

`grid_results` stores every parameter combination.

`best_results` stores the best F1 row for each:

```text
cutoff x feature_combination x model
```

## Interpretation Rules

Use these points when writing the analysis:

- This is a controlled feature-combination experiment, not a full feature engineering search.
- `asm_days_early_mean` captures submission timing behavior.
- `asm_count` captures participation in assessments.
- `vle_last_day` captures recentness of LMS activity.
- `3C1` identifies the strongest single behavior signal.
- `3C2` tests whether two behavior signals are complementary.
- `3C3` tests whether all three behavior signals are useful together.
- `base_beh_*` vs `beh_*` tests whether total clicks and active days add explanatory value.
- If performance improves from week5 to week10, behavior signals become clearer over time.
- If recall is low, the model may miss at-risk students even when F1 looks acceptable.
- If precision is low, the model may over-flag students.
- Accuracy is secondary because the goal is at-risk detection.

## Stop Conditions

Stop before modeling if:

- any of the three selected features is missing
- selected feature numeric cells have missing values
- `id_student` is selected as a predictor
- `date_unregistration` is selected as a predictor
- result CSV rows duplicate unintentionally

## Final Reminder

This notebook performs tuning experiments only. It does not select or save a final production model.
