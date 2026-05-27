# Feature Pipeline Report

## Scope

This report documents the leakage-safe feature pipeline outputs. No final models were trained.

## Output Files
| cutoff | cutoff_day | path | rows | columns | duplicated_base_key_rows | target_distribution | missing_columns_nonzero | forbidden_columns_present | after_cutoff_feature_violations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| week5 | 35 | data\processed\features_week5.csv | 32593 | 68 | 0 | 0: 22437, 1: 10156 | 12 |  |  |
| week7 | 49 | data\processed\features_week7.csv | 32593 | 68 | 0 | 0: 22437, 1: 10156 | 12 |  |  |
| week10 | 70 | data\processed\features_week10.csv | 32593 | 70 | 0 | 0: 22437, 1: 10156 | 12 |  |  |

## Feature Rules Applied

- Base unit is one row per `code_module`, `code_presentation`, `id_student` from `studentInfo.csv`.
- `final_result` is retained for analysis and `target_withdrawn` is created from it.
- `final_result`, `target_withdrawn`, and key columns must be excluded from predictor columns by model-training code.
- `date_unregistration` is not included in any output file.
- VLE rows are filtered with `studentVle.date <= cutoff_day` before aggregation.
- Assessment rows are filtered with `studentAssessment.date_submitted <= cutoff_day` before aggregation.
- Full-course VLE totals and full-course assessment summaries are not used.
- Static categorical values are kept raw for future encoding.

## VLE Duplicate Strategy

The final treatment for `student_vle` key duplicates is unresolved. This script removes exact duplicate rows, then provides both key-level sum and key-level max click variants for VLE click features. Future review must choose one strategy before final modeling.

## Missing Handling

- Missing static values are retained.
- Count-like features are filled with 0 after left joins because absence of observed cutoff activity means no observed rows for that cutoff, not a dropped student.
- Score/date-derived numeric summaries remain missing where no qualifying observed row exists.
- `is_registered_before_start` remains missing when `date_registration` is missing.

## Columns By Output

### week5

- `code_module`
- `code_presentation`
- `id_student`
- `gender`
- `region`
- `highest_education`
- `imd_band`
- `age_band`
- `num_of_prev_attempts`
- `studied_credits`
- `disability`
- `final_result`
- `target_withdrawn`
- `date_registration`
- `is_registered_before_start`
- `total_click_until_cutoff_sum_strategy`
- `total_click_until_cutoff_max_strategy`
- `active_days_until_cutoff`
- `used_site_count_until_cutoff`
- `first_activity_date_until_cutoff`
- `last_activity_date_until_cutoff`
- `avg_click_per_active_day_until_cutoff_sum_strategy`
- `avg_click_per_active_day_until_cutoff_max_strategy`
- `days_since_last_activity_at_cutoff`
- `clicks_activity_dataplus_sum_strategy`
- `clicks_activity_dualpane_sum_strategy`
- `clicks_activity_externalquiz_sum_strategy`
- `clicks_activity_forumng_sum_strategy`
- `clicks_activity_glossary_sum_strategy`
- `clicks_activity_homepage_sum_strategy`
- `clicks_activity_htmlactivity_sum_strategy`
- `clicks_activity_oucollaborate_sum_strategy`
- `clicks_activity_oucontent_sum_strategy`
- `clicks_activity_ouelluminate_sum_strategy`
- `clicks_activity_ouwiki_sum_strategy`
- `clicks_activity_page_sum_strategy`
- `clicks_activity_questionnaire_sum_strategy`
- `clicks_activity_quiz_sum_strategy`
- `clicks_activity_resource_sum_strategy`
- `clicks_activity_sharedsubpage_sum_strategy`
- `clicks_activity_subpage_sum_strategy`
- `clicks_activity_url_sum_strategy`
- `clicks_activity_dataplus_max_strategy`
- `clicks_activity_dualpane_max_strategy`
- `clicks_activity_externalquiz_max_strategy`
- `clicks_activity_forumng_max_strategy`
- `clicks_activity_glossary_max_strategy`
- `clicks_activity_homepage_max_strategy`
- `clicks_activity_htmlactivity_max_strategy`
- `clicks_activity_oucollaborate_max_strategy`
- `clicks_activity_oucontent_max_strategy`
- `clicks_activity_ouelluminate_max_strategy`
- `clicks_activity_ouwiki_max_strategy`
- `clicks_activity_page_max_strategy`
- `clicks_activity_questionnaire_max_strategy`
- `clicks_activity_quiz_max_strategy`
- `clicks_activity_resource_max_strategy`
- `clicks_activity_sharedsubpage_max_strategy`
- `clicks_activity_subpage_max_strategy`
- `clicks_activity_url_max_strategy`
- `assessment_count_until_cutoff`
- `mean_score_until_cutoff`
- `min_score_until_cutoff`
- `max_score_until_cutoff`
- `submitted_late_count_until_cutoff`
- `assessment_rows_missing_due_date_until_cutoff`
- `scored_assessment_count_until_cutoff`
- `weighted_score_until_cutoff`

### week7

- `code_module`
- `code_presentation`
- `id_student`
- `gender`
- `region`
- `highest_education`
- `imd_band`
- `age_band`
- `num_of_prev_attempts`
- `studied_credits`
- `disability`
- `final_result`
- `target_withdrawn`
- `date_registration`
- `is_registered_before_start`
- `total_click_until_cutoff_sum_strategy`
- `total_click_until_cutoff_max_strategy`
- `active_days_until_cutoff`
- `used_site_count_until_cutoff`
- `first_activity_date_until_cutoff`
- `last_activity_date_until_cutoff`
- `avg_click_per_active_day_until_cutoff_sum_strategy`
- `avg_click_per_active_day_until_cutoff_max_strategy`
- `days_since_last_activity_at_cutoff`
- `clicks_activity_dataplus_sum_strategy`
- `clicks_activity_dualpane_sum_strategy`
- `clicks_activity_externalquiz_sum_strategy`
- `clicks_activity_forumng_sum_strategy`
- `clicks_activity_glossary_sum_strategy`
- `clicks_activity_homepage_sum_strategy`
- `clicks_activity_htmlactivity_sum_strategy`
- `clicks_activity_oucollaborate_sum_strategy`
- `clicks_activity_oucontent_sum_strategy`
- `clicks_activity_ouelluminate_sum_strategy`
- `clicks_activity_ouwiki_sum_strategy`
- `clicks_activity_page_sum_strategy`
- `clicks_activity_questionnaire_sum_strategy`
- `clicks_activity_quiz_sum_strategy`
- `clicks_activity_resource_sum_strategy`
- `clicks_activity_sharedsubpage_sum_strategy`
- `clicks_activity_subpage_sum_strategy`
- `clicks_activity_url_sum_strategy`
- `clicks_activity_dataplus_max_strategy`
- `clicks_activity_dualpane_max_strategy`
- `clicks_activity_externalquiz_max_strategy`
- `clicks_activity_forumng_max_strategy`
- `clicks_activity_glossary_max_strategy`
- `clicks_activity_homepage_max_strategy`
- `clicks_activity_htmlactivity_max_strategy`
- `clicks_activity_oucollaborate_max_strategy`
- `clicks_activity_oucontent_max_strategy`
- `clicks_activity_ouelluminate_max_strategy`
- `clicks_activity_ouwiki_max_strategy`
- `clicks_activity_page_max_strategy`
- `clicks_activity_questionnaire_max_strategy`
- `clicks_activity_quiz_max_strategy`
- `clicks_activity_resource_max_strategy`
- `clicks_activity_sharedsubpage_max_strategy`
- `clicks_activity_subpage_max_strategy`
- `clicks_activity_url_max_strategy`
- `assessment_count_until_cutoff`
- `mean_score_until_cutoff`
- `min_score_until_cutoff`
- `max_score_until_cutoff`
- `submitted_late_count_until_cutoff`
- `assessment_rows_missing_due_date_until_cutoff`
- `scored_assessment_count_until_cutoff`
- `weighted_score_until_cutoff`

### week10

- `code_module`
- `code_presentation`
- `id_student`
- `gender`
- `region`
- `highest_education`
- `imd_band`
- `age_band`
- `num_of_prev_attempts`
- `studied_credits`
- `disability`
- `final_result`
- `target_withdrawn`
- `date_registration`
- `is_registered_before_start`
- `total_click_until_cutoff_sum_strategy`
- `total_click_until_cutoff_max_strategy`
- `active_days_until_cutoff`
- `used_site_count_until_cutoff`
- `first_activity_date_until_cutoff`
- `last_activity_date_until_cutoff`
- `avg_click_per_active_day_until_cutoff_sum_strategy`
- `avg_click_per_active_day_until_cutoff_max_strategy`
- `days_since_last_activity_at_cutoff`
- `clicks_activity_dataplus_sum_strategy`
- `clicks_activity_dualpane_sum_strategy`
- `clicks_activity_externalquiz_sum_strategy`
- `clicks_activity_forumng_sum_strategy`
- `clicks_activity_glossary_sum_strategy`
- `clicks_activity_homepage_sum_strategy`
- `clicks_activity_htmlactivity_sum_strategy`
- `clicks_activity_oucollaborate_sum_strategy`
- `clicks_activity_oucontent_sum_strategy`
- `clicks_activity_ouelluminate_sum_strategy`
- `clicks_activity_ouwiki_sum_strategy`
- `clicks_activity_page_sum_strategy`
- `clicks_activity_questionnaire_sum_strategy`
- `clicks_activity_quiz_sum_strategy`
- `clicks_activity_repeatactivity_sum_strategy`
- `clicks_activity_resource_sum_strategy`
- `clicks_activity_sharedsubpage_sum_strategy`
- `clicks_activity_subpage_sum_strategy`
- `clicks_activity_url_sum_strategy`
- `clicks_activity_dataplus_max_strategy`
- `clicks_activity_dualpane_max_strategy`
- `clicks_activity_externalquiz_max_strategy`
- `clicks_activity_forumng_max_strategy`
- `clicks_activity_glossary_max_strategy`
- `clicks_activity_homepage_max_strategy`
- `clicks_activity_htmlactivity_max_strategy`
- `clicks_activity_oucollaborate_max_strategy`
- `clicks_activity_oucontent_max_strategy`
- `clicks_activity_ouelluminate_max_strategy`
- `clicks_activity_ouwiki_max_strategy`
- `clicks_activity_page_max_strategy`
- `clicks_activity_questionnaire_max_strategy`
- `clicks_activity_quiz_max_strategy`
- `clicks_activity_repeatactivity_max_strategy`
- `clicks_activity_resource_max_strategy`
- `clicks_activity_sharedsubpage_max_strategy`
- `clicks_activity_subpage_max_strategy`
- `clicks_activity_url_max_strategy`
- `assessment_count_until_cutoff`
- `mean_score_until_cutoff`
- `min_score_until_cutoff`
- `max_score_until_cutoff`
- `submitted_late_count_until_cutoff`
- `assessment_rows_missing_due_date_until_cutoff`
- `scored_assessment_count_until_cutoff`
- `weighted_score_until_cutoff`

## Open Decisions

- Choose the final VLE duplicate strategy: sum, max, or another reviewed treatment.
- Decide cohort handling for students already withdrawn before each cutoff.
- Decide missing-value encoding/imputation rules for modeling.
- Decide whether `is_banked`, VLE `week_from/week_to`, and course length metadata should be used in later iterations.
- Decide final encoding plan for raw categorical variables.
