# OULAD 기반 조기 At-Risk 학생 예측

## Summary

이 프로젝트는 Open University Learning Analytics Dataset(OULAD)을 사용해 조기 at-risk 학생 예측 파이프라인과 Streamlit 포트폴리오 앱을 구현합니다. cutoff별 행동 feature를 만들고, Week 5, Week 7, Week 10 각각에 대해 Random Forest 모델을 학습한 뒤, 익명화된 앱 데이터를 통해 결과를 보여줍니다.

이 프로젝트는 교육 데이터마이닝 문제를 행동 기반 상태 예측 문제로 재구성합니다.

## Motivation

많은 교육 예측 프로젝트는 학기 후반이나 최종 결과에 가까운 시점의 정보를 사용합니다. 이 프로젝트는 더 이른 시점인 Week 5, Week 7, Week 10에서 학생의 현재 위험 상태를 행동 데이터로 설명할 수 있는지를 확인합니다.

이 앱은 실제 학생 개입 결정을 위한 도구가 아닙니다. 목적은 leakage를 통제한 재현 가능한 모델링 파이프라인과 포트폴리오용 인터랙티브 데모를 보여주는 것입니다.

## Why Behavior-Based Prediction?

모델은 각 cutoff 이전에 관측 가능한 행동 feature에 집중합니다.

- VLE 활동량
- 활동 일수
- 사용한 사이트 수
- 최근 활동성
- 평가 참여 횟수
- 평가 점수와 제출 시점

이 feature들은 특정 시점까지 학생이 강좌에 어떻게 참여하고 있는지를 설명합니다. 따라서 이 데모는 정적 학생 프로파일링보다 조기 상태 모니터링에 가깝습니다.

## Dataset

원본 OULAD CSV 파일은 `data/raw/`에 둡니다.

필요 파일:

```text
assessments.csv
courses.csv
studentAssessment.csv
studentInfo.csv
studentRegistration.csv
studentVle.csv
vle.csv
```

현재 파이프라인이 직접 읽는 파일:

```text
assessments.csv
studentAssessment.csv
studentInfo.csv
studentRegistration.csv
studentVle.csv
```

## Target Definition

이진 target 정의:

- `target_at_risk = 1`: `final_result`가 `Fail` 또는 `Withdrawn`
- `target_at_risk = 0`: `final_result`가 `Pass` 또는 `Distinction`

따라서 앱에서는 fail probability가 아니라 **At-risk probability**라는 용어를 사용합니다.

## Feature Design

feature는 세 cutoff 기준으로 생성됩니다.

- Week 5: day 35
- Week 7: day 49
- Week 10: day 70

모델에 사용하는 feature:

```text
active_days_until_cutoff
total_click_until_cutoff
used_site_count_until_cutoff
avg_click_per_active_day_until_cutoff
days_since_last_activity_at_cutoff
assessment_count_until_cutoff
mean_score_until_cutoff
avg_days_before_due_until_cutoff
highest_education_encoded
credits_bin
```

leakage 통제:

- `studentVle.date <= cutoff_day`만 사용합니다.
- `studentAssessment.date_submitted <= cutoff_day`만 사용합니다.
- `date_unregistration <= cutoff_day`인 학생은 제외합니다.
- `studentVle` 중복은 `code_module`, `code_presentation`, `id_student`, `id_site`, `date` 기준으로 `sum_click` 평균 처리합니다.
- `final_result`, `date_unregistration`, `target_at_risk`, `target_withdrawn`은 모델 feature에서 제외합니다.

## Why Demographic Features Are Excluded

배포 모델 feature 목록에서는 직접적인 demographic column을 제외합니다.

```text
gender
region
age_band
```

이 프로젝트는 실제 개입 시스템이 아니라 포트폴리오 및 연구 탐색용 데모입니다. 해당 column을 제외함으로써 demographic profiling이 아니라 행동 기반 상태 예측에 초점을 둡니다.

## Pipeline

주요 파일:

```text
src/config.py
src/data_loader.py
src/build_features.py
src/train_model.py
src/anonymize.py
src/audit_outputs.py
app.py
```

실행 순서:

```powershell
python -m src.build_features
python -m src.train_model
python -m src.anonymize
python -m src.audit_outputs
```

앱 전용 데이터는 `data/app/`에 저장되며 `anon_id`만 사용합니다. Streamlit 앱은 raw CSV를 읽지 않습니다.

## Model

cutoff별로 하나의 `RandomForestClassifier`를 학습합니다.

- `models/rf_week5.pkl`
- `models/rf_week7.pkl`
- `models/rf_week10.pkl`

학습/평가 분리는 `id_student` 기준 `GroupShuffleSplit`을 사용합니다. 따라서 앱에서 선택 가능한 profile은 학습에 사용되지 않은 held-out 학생입니다.

설정:

```text
n_estimators=300
max_depth=None
min_samples_leaf=5
class_weight="balanced"
random_state=724
n_jobs=-1
```

평가 지표는 `models/metrics.json`에 저장됩니다.

## Streamlit App

실행:

```powershell
streamlit run app.py
```

페이지:

- Project Overview
- Student Explorer
- What-if Simulator
- Model Performance

앱은 익명화된 `Student Profile` 라벨만 사용하며 `id_student`를 노출하지 않습니다. What-if Simulator는 causal inference가 아니라 model sensitivity simulation임을 명시합니다.

## Local Setup

의존성 설치:

```powershell
pip install -r requirements.txt
```

전체 로컬 실행:

```powershell
python -m src.build_features
python -m src.train_model
python -m src.anonymize
python -m src.audit_outputs
streamlit run app.py
```

## Streamlit Cloud Deployment

배포 전 확인:

- `data/raw/`는 업로드하지 않습니다.
- private student mapping 파일은 업로드하지 않습니다.
- `data/app/`의 익명화된 앱 데이터만 사용합니다.
- `python -m src.audit_outputs`가 통과해야 합니다.
- 모델 파일 용량이 배포 환경 제한에 맞는지 확인합니다.
- `app.py`가 raw CSV를 읽지 않는지 확인합니다.

현재 로컬 모델 pickle 파일은 각각 100 MB 미만이지만, 세 파일 합산 용량은 약 231 MB입니다. 배포 전 Streamlit Cloud 제한을 확인해야 합니다.

## Limitations

- 예측값은 모델 추정치이며 실제 개입 권고가 아닙니다.
- target은 `Fail`과 `Withdrawn`을 함께 묶습니다. 두 결과는 관련이 있지만 동일한 현상은 아닙니다.
- What-if Simulator는 causal estimate가 아닙니다.
- Random Forest feature importance는 전역적이고 근사적인 설명입니다.
- 앱은 포트폴리오와 연구 탐색용이며 실제 학생 지원 운영 도구가 아닙니다.

## Future Work

- 배포를 위한 모델 경량화
- probability calibration 비교
- 추가 행동 기반 feature set 평가
- module/presentation 단위 검증
- 개인정보를 보호하는 설명 기능 개선

## Research Direction Relevance

이 데모는 교육 데이터마이닝을 정적 학생 정체성이 아니라 관측 가능한 행동 상태 중심으로 바라보는 연구 방향과 연결됩니다. 시간 cutoff 준수, leakage 통제, 익명화된 표현, 행동 기반 해석을 강조합니다.
