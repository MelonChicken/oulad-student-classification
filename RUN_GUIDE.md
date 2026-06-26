# OULAD Pipeline Run Guide

Run every command from the project root:

```powershell
cd C:\Users\osca0\Dev\studyDataMining\teamproject
```

## 1. Prepare raw data

Place the raw OULAD CSV files in `data/raw/`:

```text
data/raw/
  assessments.csv
  courses.csv
  studentAssessment.csv
  studentInfo.csv
  studentRegistration.csv
  studentVle.csv
  vle.csv
```

The current pipeline uses:

```text
assessments.csv
studentAssessment.csv
studentInfo.csv
studentRegistration.csv
studentVle.csv
```

## 2. Install dependencies

```powershell
pip install -r requirements.txt
```

## 3. Build cutoff feature files

```powershell
python -m src.build_features
```

Expected outputs:

```text
data/processed/features_week5.csv
data/processed/features_week7.csv
data/processed/features_week10.csv
```

The script prints validation evidence for each cutoff:

```text
rows
positive_rate
studentVle duplicate key rows handled by mean aggregation
future VLE rows excluded
future assessment rows excluded
unmatched assessment rows
```

## 4. Train Random Forest models

```powershell
python -m src.train_model
```

Expected outputs:

```text
models/rf_week5.pkl
models/rf_week7.pkl
models/rf_week10.pkl
models/metrics.json
models/feature_columns.json
data/processed/test_students.csv
```

The training script uses `GroupShuffleSplit` with `id_student` groups, `test_size=0.2`, and `random_state=724`.

## 5. Create anonymized app data

```powershell
python -m src.anonymize
```

Expected outputs:

```text
data/app/app_test_students.csv
data/app/app_features_week5.csv
data/app/app_features_week7.csv
data/app/app_features_week10.csv
```

These files use `anon_id` and do not expose `id_student`. The Streamlit app reads these app-facing files only.

## 6. Audit outputs

```powershell
python -m src.audit_outputs
```

The audit checks required artifacts, selected feature columns, leakage exclusions, app anonymization, duplicate keys, target integrity, and prediction probability sanity.

## 7. Run Streamlit

```powershell
streamlit run app.py
```

Open:

```text
http://localhost:8501
```

## One-shot run

After raw CSV files are in `data/raw/`, run:

```powershell
pip install -r requirements.txt
python -m src.build_features
python -m src.train_model
python -m src.anonymize
python -m src.audit_outputs
streamlit run app.py
```
