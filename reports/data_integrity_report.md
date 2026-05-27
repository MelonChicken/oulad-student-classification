# Data Integrity Report

## Findings
- All expected Kaggle OULAD tables were loaded from data/kaggle_oulad.
- This audit does not drop rows, save cleaned data, create final features, or train models.
- At least one expected key is not unique; joins using those keys can multiply rows.
- student_vle still has duplicate key rows after exact duplicate removal.
- Some duplicated student_vle key groups have different sum_click values.
- Some referential integrity checks have left_only or right_only keys.

## Evidence Tables

### Table shapes
| table | rows | columns |
| --- | --- | --- |
| courses | 22 | 3 |
| assessments | 206 | 6 |
| vle | 6364 | 6 |
| student_info | 32593 | 12 |
| student_registration | 32593 | 5 |
| student_assessment | 173912 | 5 |
| student_vle | 10655280 | 6 |

### Missing values, nonzero only
| table | column | missing_count | missing_ratio |
| --- | --- | --- | --- |
| assessments | date | 11 | 0.0533981 |
| vle | week_from | 5243 | 0.823853 |
| vle | week_to | 5243 | 0.823853 |
| student_info | imd_band | 1111 | 0.0340871 |
| student_registration | date_registration | 45 | 0.00138066 |
| student_registration | date_unregistration | 22521 | 0.690977 |
| student_assessment | score | 173 | 0.000994756 |

### Key uniqueness
| table | key | rows | duplicated_rows_by_key | duplicated_key_groups |
| --- | --- | --- | --- | --- |
| courses | code_module, code_presentation | 22 | 0 | 0 |
| assessments | id_assessment | 206 | 0 | 0 |
| vle | id_site | 6364 | 0 | 0 |
| student_info | code_module, code_presentation, id_student | 32593 | 0 | 0 |
| student_registration | code_module, code_presentation, id_student | 32593 | 0 | 0 |
| student_assessment | id_assessment, id_student | 173912 | 0 | 0 |
| student_vle | code_module, code_presentation, id_student, id_site, date | 10655280 | 2195960 | 1614505 |

### student_vle duplicate summary
| metric | value |
| --- | --- |
| total_rows | 10655280 |
| exact_duplicate_rows | 787170 |
| key_duplicate_rows | 2195960 |
| rows_after_exact_duplicate_removal | 9868110 |
| remaining_key_duplicate_rows_after_exact_removal | 1408790 |
| duplicated_key_groups_after_exact_removal | 1179074 |
| all_key_groups_with_different_sum_click_after_exact_removal | 1179074 |
| duplicated_key_groups_with_different_sum_click_after_exact_removal | 1179074 |
| raw_total_clicks | 39605099 |
| total_clicks_after_exact_duplicate_removal | 38343063 |
| total_clicks_after_key_aggregation_sum | 38343063 |
| total_clicks_after_key_aggregation_max | 34402738 |

### student_vle duplicated group size distribution
| group_size | group_count |
| --- | --- |
| 2 | 997867 |
| 3 | 139730 |
| 4 | 35050 |
| 5 | 5880 |
| 6 | 500 |
| 7 | 36 |
| 8 | 11 |

### Referential integrity
| check | key | both | left_only | right_only |
| --- | --- | --- | --- | --- |
| student_info_to_student_registration | code_module, code_presentation, id_student | 32593 | 0 | 0 |
| student_vle_to_student_info | code_module, code_presentation, id_student | 29228 | 0 | 3365 |
| student_assessment_to_assessments | id_assessment | 188 | 0 | 18 |
| student_vle_to_vle | id_site | 6268 | 0 | 96 |

### Date and numeric range statistics
| table | column | count | mean | std | min | 1% | 5% | 25% | 50% | 75% | 95% | 99% | max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| student_registration | date_registration | 32548 | -69.4113 | 49.2605 | -322 | -207 | -156 | -100 | -57 | -29 | -15 | -2 | 167 |
| student_registration | date_unregistration | 10072 | 49.7576 | 82.4609 | -365 | -136 | -69.35 | -2 | 27 | 109 | 202 | 228.29 | 444 |
| student_assessment | date_submitted | 173912 | 116.033 | 71.4841 | -11 | -1 | 17 | 51 | 116 | 173 | 230 | 243 | 608 |
| student_assessment | score | 173739 | 75.7996 | 18.7981 | 0 | 15 | 40 | 65 | 80 | 90 | 100 | 100 | 100 |
| student_vle | date | 1.06553e+07 | 95.174 | 76.0713 | -25 | -17 | -4 | 25 | 86 | 156 | 226 | 240 | 269 |
| student_vle | sum_click | 1.06553e+07 | 3.71695 | 8.84905 | 1 | 1 | 1 | 1 | 2 | 3 | 12 | 34 | 6977 |
| assessments | date | 195 | 145.005 | 76.0011 | 12 | 18 | 19.7 | 71 | 152 | 222 | 240.3 | 241 | 261 |
| assessments | weight | 206 | 20.8738 | 30.3842 | 0 | 0 | 0 | 0 | 12.5 | 24.25 | 100 | 100 | 100 |

### Suspicious range flags
_No rows._

### Target distribution, overall
| final_result | count | ratio |
| --- | --- | --- |
| Pass | 12361 | 0.379253 |
| Withdrawn | 10156 | 0.311601 |
| Fail | 7052 | 0.216365 |
| Distinction | 3024 | 0.0927807 |

### Target distribution by module
| code_module | final_result | count | ratio_within_group |
| --- | --- | --- | --- |
| AAA | Pass | 487 | 0.65107 |
| AAA | Withdrawn | 126 | 0.168449 |
| AAA | Fail | 91 | 0.121658 |
| AAA | Distinction | 44 | 0.0588235 |
| BBB | Pass | 3077 | 0.38905 |
| BBB | Withdrawn | 2388 | 0.301935 |
| BBB | Fail | 1767 | 0.223416 |
| BBB | Distinction | 677 | 0.0855987 |
| CCC | Withdrawn | 1975 | 0.445422 |
| CCC | Pass | 1180 | 0.266125 |
| CCC | Fail | 781 | 0.176139 |
| CCC | Distinction | 498 | 0.112314 |
| DDD | Withdrawn | 2250 | 0.358737 |
| DDD | Pass | 2227 | 0.35507 |
| DDD | Fail | 1412 | 0.225128 |
| DDD | Distinction | 383 | 0.0610651 |
| EEE | Pass | 1294 | 0.441036 |
| EEE | Withdrawn | 722 | 0.24608 |
| EEE | Fail | 562 | 0.191547 |
| EEE | Distinction | 356 | 0.121336 |
| FFF | Pass | 2978 | 0.383664 |
| FFF | Withdrawn | 2403 | 0.309585 |
| FFF | Fail | 1711 | 0.220433 |
| FFF | Distinction | 670 | 0.086318 |
| GGG | Pass | 1118 | 0.4412 |
| GGG | Fail | 728 | 0.287293 |
| GGG | Distinction | 396 | 0.156275 |
| GGG | Withdrawn | 292 | 0.115233 |

### Target distribution by presentation
| code_presentation | final_result | count | ratio_within_group |
| --- | --- | --- | --- |
| 2013B | Pass | 1768 | 0.377455 |
| 2013B | Withdrawn | 1348 | 0.287788 |
| 2013B | Fail | 1241 | 0.264944 |
| 2013B | Distinction | 327 | 0.0698121 |
| 2013J | Pass | 3726 | 0.421255 |
| 2013J | Withdrawn | 2369 | 0.267835 |
| 2013J | Fail | 2001 | 0.22623 |
| 2013J | Distinction | 749 | 0.0846806 |
| 2014B | Withdrawn | 2613 | 0.334828 |
| 2014B | Pass | 2574 | 0.329831 |
| 2014B | Fail | 1833 | 0.23488 |
| 2014B | Distinction | 784 | 0.100461 |
| 2014J | Pass | 4293 | 0.381261 |
| 2014J | Withdrawn | 3826 | 0.339787 |
| 2014J | Fail | 1977 | 0.175577 |
| 2014J | Distinction | 1164 | 0.103375 |

### Target distribution by module-presentation
| code_module | code_presentation | final_result | count | ratio_within_group |
| --- | --- | --- | --- | --- |
| AAA | 2013J | Pass | 258 | 0.673629 |
| AAA | 2013J | Withdrawn | 60 | 0.156658 |
| AAA | 2013J | Fail | 45 | 0.117493 |
| AAA | 2013J | Distinction | 20 | 0.0522193 |
| AAA | 2014J | Pass | 229 | 0.627397 |
| AAA | 2014J | Withdrawn | 66 | 0.180822 |
| AAA | 2014J | Fail | 46 | 0.126027 |
| AAA | 2014J | Distinction | 24 | 0.0657534 |
| BBB | 2013B | Pass | 648 | 0.366723 |
| BBB | 2013B | Withdrawn | 505 | 0.285795 |
| BBB | 2013B | Fail | 459 | 0.259762 |
| BBB | 2013B | Distinction | 155 | 0.0877193 |
| BBB | 2013J | Pass | 896 | 0.400536 |
| BBB | 2013J | Withdrawn | 644 | 0.287886 |
| BBB | 2013J | Fail | 521 | 0.232901 |
| BBB | 2013J | Distinction | 176 | 0.0786768 |
| BBB | 2014B | Pass | 561 | 0.347799 |
| BBB | 2014B | Withdrawn | 490 | 0.303782 |
| BBB | 2014B | Fail | 396 | 0.245505 |
| BBB | 2014B | Distinction | 166 | 0.102914 |
| BBB | 2014J | Pass | 972 | 0.424084 |
| BBB | 2014J | Withdrawn | 749 | 0.326789 |
| BBB | 2014J | Fail | 391 | 0.170593 |
| BBB | 2014J | Distinction | 180 | 0.078534 |
| CCC | 2014B | Withdrawn | 898 | 0.463843 |
| CCC | 2014B | Pass | 471 | 0.243285 |
| CCC | 2014B | Fail | 375 | 0.193698 |
| CCC | 2014B | Distinction | 192 | 0.0991736 |
| CCC | 2014J | Withdrawn | 1077 | 0.431145 |
| CCC | 2014J | Pass | 709 | 0.283827 |
| CCC | 2014J | Fail | 406 | 0.16253 |
| CCC | 2014J | Distinction | 306 | 0.122498 |
| DDD | 2013B | Pass | 456 | 0.349962 |
| DDD | 2013B | Withdrawn | 432 | 0.331543 |
| DDD | 2013B | Fail | 361 | 0.277053 |
| DDD | 2013B | Distinction | 54 | 0.0414428 |
| DDD | 2013J | Pass | 731 | 0.377193 |
| DDD | 2013J | Withdrawn | 681 | 0.351393 |
| DDD | 2013J | Fail | 428 | 0.220846 |
| DDD | 2013J | Distinction | 98 | 0.0505676 |
| DDD | 2014B | Withdrawn | 490 | 0.399023 |
| DDD | 2014B | Pass | 360 | 0.29316 |
| DDD | 2014B | Fail | 259 | 0.210912 |
| DDD | 2014B | Distinction | 119 | 0.0969055 |
| DDD | 2014J | Pass | 680 | 0.377149 |
| DDD | 2014J | Withdrawn | 647 | 0.358846 |
| DDD | 2014J | Fail | 364 | 0.201886 |
| DDD | 2014J | Distinction | 112 | 0.0621187 |
| EEE | 2013J | Pass | 482 | 0.458175 |
| EEE | 2013J | Withdrawn | 243 | 0.230989 |
| EEE | 2013J | Fail | 200 | 0.190114 |
| EEE | 2013J | Distinction | 127 | 0.120722 |
| EEE | 2014B | Pass | 285 | 0.410663 |
| EEE | 2014B | Withdrawn | 173 | 0.24928 |
| EEE | 2014B | Fail | 164 | 0.236311 |
| EEE | 2014B | Distinction | 72 | 0.103746 |
| EEE | 2014J | Pass | 527 | 0.443603 |
| EEE | 2014J | Withdrawn | 306 | 0.257576 |
| EEE | 2014J | Fail | 198 | 0.166667 |
| EEE | 2014J | Distinction | 157 | 0.132155 |
| FFF | 2013B | Pass | 664 | 0.4114 |
| FFF | 2013B | Fail | 421 | 0.260843 |
| FFF | 2013B | Withdrawn | 411 | 0.254647 |
| FFF | 2013B | Distinction | 118 | 0.0731103 |
| FFF | 2013J | Pass | 908 | 0.397722 |
| FFF | 2013J | Withdrawn | 675 | 0.295664 |
| FFF | 2013J | Fail | 513 | 0.224704 |
| FFF | 2013J | Distinction | 187 | 0.0819098 |
| FFF | 2014B | Pass | 547 | 0.364667 |
| FFF | 2014B | Withdrawn | 462 | 0.308 |
| FFF | 2014B | Fail | 384 | 0.256 |
| FFF | 2014B | Distinction | 107 | 0.0713333 |
| FFF | 2014J | Pass | 859 | 0.363214 |
| FFF | 2014J | Withdrawn | 855 | 0.361522 |
| FFF | 2014J | Fail | 393 | 0.166173 |
| FFF | 2014J | Distinction | 258 | 0.109091 |
| GGG | 2013J | Pass | 451 | 0.473739 |
| GGG | 2013J | Fail | 294 | 0.308824 |
| GGG | 2013J | Distinction | 141 | 0.148109 |
| GGG | 2013J | Withdrawn | 66 | 0.0693277 |
| GGG | 2014B | Pass | 350 | 0.420168 |
| GGG | 2014B | Fail | 255 | 0.306122 |
| GGG | 2014B | Distinction | 128 | 0.153661 |
| GGG | 2014B | Withdrawn | 100 | 0.120048 |
| GGG | 2014J | Pass | 317 | 0.423231 |
| GGG | 2014J | Fail | 179 | 0.238985 |
| GGG | 2014J | Distinction | 127 | 0.169559 |
| GGG | 2014J | Withdrawn | 126 | 0.168224 |

## Risks
- At least one expected key is not unique; joins using those keys can multiply rows.
- student_vle still has duplicate key rows after exact duplicate removal.
- Some duplicated student_vle key groups have different sum_click values.
- Some referential integrity checks have left_only or right_only keys.


## Recommended Next Checks
- Review leakage rules for unregistration dates, assessment dates/scores, and VLE activity after each prediction cutoff.
- Decide how to treat student_vle exact duplicates and remaining key duplicates before creating click-based features.
- Validate join plans from student_info as the student-course-presentation base unit before feature engineering.
- Compare Kaggle tables against official OULAD where file-level discrepancies may matter.

## Unresolved Decisions
- No final treatment has been chosen for student_vle duplicates.
- No missing-value imputation or row exclusion rule has been chosen.
- No cutoff-specific leakage boundary has been finalized.
- No final feature construction or modeling has been performed.

## Generated CSV Evidence
- reports/tables/data_preprocessing/date_numeric_range_flags.csv
- reports/tables/data_preprocessing/date_numeric_range_stats.csv
- reports/tables/data_preprocessing/key_duplicates.csv
- reports/tables/data_preprocessing/missing_values_nonzero.csv
- reports/tables/data_preprocessing/referential_integrity.csv
- reports/tables/data_preprocessing/student_vle_duplicate_group_size_distribution.csv
- reports/tables/data_preprocessing/student_vle_duplicate_summary.csv
- reports/tables/data_preprocessing/table_shapes.csv
- reports/tables/data_preprocessing/target_distribution_by_module.csv
- reports/tables/data_preprocessing/target_distribution_by_module_presentation.csv
- reports/tables/data_preprocessing/target_distribution_by_presentation.csv
- reports/tables/data_preprocessing/target_distribution_overall.csv
