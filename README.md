# Study Data Mining Team Project

OULAD(Open University Learning Analytics Dataset)를 기반으로 학생 로그 데이터를 분석하고 withdraw 예측 classification 모델을 만드는 것이 목적입니다.
## 프로젝트 구조

```text
teamproject/
├── data/
│   ├── kaggle_oulad/
│   │   ├── assessments.csv
│   │   ├── courses.csv
│   │   ├── studentAssessment.csv
│   │   ├── studentInfo.csv
│   │   ├── studentRegistration.csv
│   │   ├── studentVle.csv
│   │   └── vle.csv
│   └── official_oulad/
│       ├── assessments.csv
│       ├── courses.csv
│       ├── OULAD.names
│       ├── studentAssessment.csv
│       ├── studentInfo.csv
│       ├── studentRegistration.csv
│       ├── studentVle.csv
│       └── vle.csv
├── notebooks/
│   └── exploring_dataset.ipynb
├── src/
│   └── eda.py
└── requirements.txt
```

## 디렉터리 설명

- `data/kaggle_oulad/`: Kaggle 경로 기준으로 정리된 OULAD CSV 파일 모음
- `data/official_oulad/`: 공식 배포본 기준 데이터와 설명 파일(`OULAD.names`)
- `notebooks/exploring_dataset.ipynb`: 데이터 구조와 분포를 탐색하는 주피터 노트북
- `src/`: 파이썬 코드 보관소
- `requirements.txt`: 현재 프로젝트에서 사용하는 최소 파이썬 패키지 목록

## 사용 라이브러리

`requirements.txt` 기준:

- `pandas`
- `numpy`
- `matplotlib`
- `seaborn`

설치 예시:

```bash
pip install -r requirements.txt
```

## 실행 방법

### 1. 노트북 실행

```bash
jupyter notebook notebooks/exploring_dataset.ipynb
```

### 2. 데이터 준비
```bash
  python src\build_features.py
  python src\build_cohort.py
  python src\build_baseline_features.py
```
#### 각 파일별 실행 산출물
  1. build_features.py
     → data/processed/features_week5.csv
     → data/processed/features_week7.csv
     → data/processed/features_week10.csv

  2. build_cohort.py
     → data/processed/features_week5_cohort.csv
     → data/processed/features_week7_cohort.csv
     → data/processed/features_week10_cohort.csv
     → reports/cohort_report.md

  3. build_baseline_features.py
     → data/processed/features_week5_baseline.csv
     → data/processed/features_week7_baseline.csv
     → data/processed/features_week10_baseline.csv
     → reports/baseline_feature_report.md

- 최종 모델링용 파일은 항상 이 3개입니다.
  - `data/processed/features_week5_baseline.csv`
  - `data/processed/features_week7_baseline.csv`
  - `data/processed/features_week10_baseline.csv`