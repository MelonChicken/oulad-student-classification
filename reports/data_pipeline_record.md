# OULAD Data Pipeline — Raw to Unified CSV

> 모델링 시작 전 데이터 처리 과정과 의사결정 전체 기록. 본 문서는 raw 데이터에서 model-ready unified CSV까지의 모든 단계, 각 단계의 결정 근거, 산출물을 정리합니다.
> 
> **프로젝트명**: OULAD 조기 학업 위험군 예측 (Early At-Risk Student Prediction)

---

## 0. 개요

### 처리 흐름
```
[7개 raw CSV]
    ↓ Stage 1: 데이터 감사
[감사 리포트]
    ↓ Stage 2: 누수 검토
[leakage 규칙]
    ↓ Stage 3: Feature pipeline (cutoff별 1차 가공)
[features_week{5,7,10}.csv]
    ↓ Stage 4: Cohort 적용
[features_week{5,7,10}_cohort.csv]
    ↓ Stage 5: 전처리 (target 생성, mean 전략, 결측 처리)
[features_week{5,7,10}_baseline.csv]  ← model-ready
```

### 최종 산출물 명세
- 행 단위: 1행 = 1 학생 × 모듈 × 학기
- 행 수: week5 27,244 / week7 26,776 / week10 26,069 (cohort 적용 후)
- Target: `target_at_risk` (Withdrawn 또는 Fail = 1)
- Positive 비율: 41~44% (cutoff별)

---

## 1. Raw 데이터 (Stage 0)

OULAD (Open University Learning Analytics Dataset), Kaggle 버전 7개 테이블.

| 테이블 | 행 수 | Key | 역할 |
|---|---:|---|---|
| `studentInfo.csv` | 32,593 | (module, presentation, student) | **base 단위**, 인구통계 + 결과 |
| `studentRegistration.csv` | 32,593 | (module, presentation, student) | 등록·탈퇴 날짜 |
| `studentAssessment.csv` | 173,912 | (assessment, student) | 과제 제출 기록 |
| `studentVle.csv` | 10,655,280 | (module, pres, student, site, date) | VLE 클릭 로그 |
| `assessments.csv` | 206 | (assessment) | 과제 메타 (마감일, 가중치) |
| `vle.csv` | 6,364 | (site) | VLE 콘텐츠 메타 (activity_type) |
| `courses.csv` | 22 | (module, presentation) | 코스 메타 (학기 길이) |

### 날짜 표현
모든 날짜는 학기 시작일 기준 offset (정수). 학기 시작일은 day 0.
- 음수: 학기 시작 전 (사전 등록, 사전 활동)
- 양수: 학기 진행 중

---

## 2. Stage 1: 데이터 감사

### 목적
모델링에 들어가기 전 raw 데이터의 무결성, 중복, 결측, 참조관계를 점검.

### 수행 작업
- 테이블별 shape 확인
- 키 중복 검사
- 결측치 분포
- 참조 무결성 (테이블 간 join 무결성)
- 날짜·수치 범위 검사
- Target 분포 (전체 / module별 / presentation별)

### 주요 발견

**Key 중복**: `student_vle` 한 곳에서만 발견
- raw 10,655,280행 중 exact duplicate 787,170행
- exact duplicate 제거 후에도 key 중복 1,408,790행 남음
- 1,179,074개 key 그룹에서 `sum_click` 값이 서로 다름 → 모델링 단계에서 집계 전략 결정 필요 (→ Stage 5)

**결측치 (nonzero만)**:
| 컬럼 | 결측 수 | 비율 |
|---|---:|---:|
| `vle.week_from`, `week_to` | 5,243 | 82.4% |
| `studentRegistration.date_unregistration` | 22,521 | 69.1% (탈퇴 안 한 학생은 정상) |
| `assessments.date` | 11 | 5.3% |
| `studentInfo.imd_band` | 1,111 | 3.4% |
| `studentRegistration.date_registration` | 45 | 0.14% |
| `studentAssessment.score` | 173 | 0.10% |

**참조 무결성** (left_only는 모두 0, 즉 로그가 메타를 벗어나는 케이스는 없음):
- `student_info` 기준 `student_vle`에 활동 기록 없는 학생: 3,365명 (활동 0 케이스)
- 메타에는 있지만 사용 기록 없는 `id_assessment`: 18개
- 메타에는 있지만 사용 기록 없는 `id_site`: 96개

**Target 분포 (전체)**: Pass 37.9% / Withdrawn 31.2% / Fail 21.6% / Distinction 9.3%

### 산출물
- `data_integrity_report.md`
- `reports/tables/data_preprocessing/` 하위 12개 CSV 증거 파일

---

## 3. Stage 2: 누수(Leakage) 검토

### 목적
각 cutoff 시점(day 35, 49, 70)에서 어떤 데이터를 feature로 써도 되고 어떤 것은 안 되는지 규칙화.

### 핵심 원칙
> Cutoff 이후의 정보는 절대 feature에 포함하지 않는다.

### 규칙

**❌ 절대 사용 금지 (predictor)**
- `final_result` — 정답
- `date_unregistration` — 탈퇴 시점, 정답을 직접 노출
- `student_vle.date > cutoff` 이후 활동
- `student_assessment.date_submitted > cutoff` 이후 제출
- 전체 학기 합산 통계

**✅ 안전 (Static 변수, 등록 시점에 결정됨)**
- 인구통계 8개 (gender, region, highest_education, imd_band, age_band, num_of_prev_attempts, studied_credits, disability)
- `code_module`, `code_presentation` (categorical)

**⚠️ 조건부**
- `score`, `date_submitted` — cutoff 이전 제출만 사용
- `is_banked` — cutoff 시점에 확정되는지 확인 필요
- `assessments.date` (마감일) — 사전 공지 가정 시 사용 가능
- `vle.week_from/to` — 82% 결측, 사용 어려움

### 산출물
- `leakage_review.md`

---

## 4. Stage 3: Feature Pipeline (1차 가공)

### 목적
누수 규칙을 코드로 구현해 cutoff별 1차 feature CSV 생성.

### 입력
7개 raw CSV.

### 처리 단계
1. `studentInfo`를 base로 잡음 (32,593행)
2. `studentRegistration`에서 `date_registration`만 join (date_unregistration 제외)
3. `studentVle`에서 exact duplicate 제거 (787,170행 제거)
4. 각 cutoff별로:
   - VLE: `date ≤ cutoff_day` 필터 후 (학생, 모듈, 학기) 단위로 집계
   - Assessment: `date_submitted ≤ cutoff_day` 필터 후 집계
5. base에 left join

### 의사결정 — Stage 3
| # | 결정 | 근거 |
|---|---|---|
| 3-1 | base 단위 = `studentInfo` 한 행 = (module, presentation, student) | 32,593행에서 시작, 어떤 학생도 누락 안 됨 |
| 3-2 | `date_unregistration` 컬럼 미포함 | leakage (정답 직접 노출) |
| 3-3 | VLE exact duplicate 제거 | 데이터 보존이 아니라 명백한 중복 |
| 3-4 | VLE key 중복은 sum/max 두 버전 모두 생성 | Stage 3에서는 결정 보류, 분석 후 선택 |
| 3-5 | Count 계열 결측 → 0 채움 | "활동 0건" 정보 보존 (left join 후 NaN과 동치) |
| 3-6 | Score/date 계열 결측 → NaN 유지 | 평균을 0으로 보면 정보 왜곡 |

### 산출물
- `features_week5.csv` (32,593 × 68)
- `features_week7.csv` (32,593 × 68)
- `features_week10.csv` (32,593 × 70) — week10에만 `repeatactivity` 2개 컬럼 추가
- `feature_pipeline_report.md`

---

## 5. Stage 4: Cohort 적용

### 동기
Stage 3의 출력은 모든 학생을 포함합니다. 하지만 "이미 떠난 학생을 곧 떠날 거라 예측"하는 건 의미가 없고, 또 데이터에 자명한 패턴(활동 0 → 82.9% withdrawn)을 만들어 모델 학습을 망가뜨립니다.

### 발견
| | week5 | week7 | week10 |
|---|---:|---:|---:|
| 원본에서 활동 0인 학생 중 Withdrawn 비율 | **82.9%** | 85.1% | 87.0% |
| Cohort 적용 후 같은 비율 | **20.4%** | 18.8% | 15.1% |

자명한 패턴이 사라짐 → 모델이 진짜 행동 신호를 학습하도록 강제됨.

### 의사결정 — Stage 4
| # | 결정 | 근거 |
|---|---|---|
| 4-1 | **Active-at-cutoff cohort** 채택 | "현재 등록 중인 학생만 예측" — 실제 운영 시나리오와 일치 |
| 4-2 | 제외 기준: `date_unregistration ≤ cutoff_day` | leakage_review에서 권장한 표준 기준 |
| 4-3 | `date_unregistration` 결측인 withdrawn 93명 → cohort 유지 | 절대 수 작음, sensitivity check로 후속 검증 |
| 4-4 | Non-withdrawn이지만 unreg ≤ cutoff인 8명 → 제외 | 데이터 일관성 |
| 4-5 | `date_unregistration` 컬럼은 출력에 미포함 | 사용 목적(cohort 정의) 완료 후 폐기, leakage 방지 |

### Cohort 적용 결과
| cutoff | 원본 | 제외 | **cohort** |
|---|---:|---:|---:|
| week5 (day 35) | 32,593 | 5,349 | **27,244** |
| week7 (day 49) | 32,593 | 5,817 | **26,776** |
| week10 (day 70) | 32,593 | 6,524 | **26,069** |

### 산출물
- `features_week5_cohort.csv` (27,244 × 68)
- `features_week7_cohort.csv` (26,776 × 68)
- `features_week10_cohort.csv` (26,069 × 70)

---

## 6. Stage 5: Unified CSV (전처리 및 최종 통합)

### 목적
Cohort CSV에서 model-ready unified CSV로 전환. Target 정의, VLE 중복 최종 처리, 결측치 처리, 일부 row 정리.

### 의사결정 — Stage 5

#### 5-1. Target 정의: `target_at_risk` (W+F)

**결정**: `target_at_risk = (final_result ∈ {Withdrawn, Fail}) → 1, else 0`

**근거**:
- Cutoff 시점 행동 비교(week5)에서 **Fail이 Withdrawn보다 더 낮은 활동**을 보임:
  - Pass 평균 클릭 459 → Withdrawn 320 → **Fail 248**
  - Pass 활성일 19.5 → Withdrawn 15.2 → **Fail 12.0**
- 즉 활동 신호 기준으로 Fail도 동급 또는 그 이상의 위험군
- 교수자 개입 관점에서 Fail과 Withdrawn 모두 도움이 필요한 학생

**주의**:
- 프로젝트명이 "조기 **이탈** 예측"이 아닌 "조기 **학업 위험군** 예측"으로 정정됨
- 기존 `target_withdrawn` 컬럼은 보조 분석용으로 유지

**Cohort 내 positive 비율**:
| cutoff | positive (W+F) | positive 비율 |
|---|---:|---:|
| week5 | 11,859 | 43.5% |
| week7 | 11,391 | 42.5% |
| week10 | 10,684 | 41.0% |

#### 5-2. VLE 중복 처리: mean 전략

**결정**: 같은 (학생, 모듈, 학기, 사이트, 날짜) 키에 여러 `sum_click` 값이 있을 때 평균값 사용.

**근거**:
- **sum (모두 더함)**: "두 기록 = 두 번의 독립 세션" 가정 → 과대 집계 위험
- **max (최댓값)**: "두 기록 = 같은 활동 중복 기록" 가정 → 진짜 다중 세션 학생 과소 추정
- **mean (평균)**: 같은 날 **다른 시간대 접속** 가능성을 반영하되, sum의 과대 집계는 피함 — 중간 입장 채택

**참고 수치 (week5 cohort 기준 총 클릭)**:
- sum 전략: 11,216,671
- **mean 전략: 8,566,096** ← 채택
- max 전략: 9,938,047

**영향 컬럼**:
- `total_click_until_cutoff`
- `avg_click_per_active_day_until_cutoff`
- `clicks_activity_{type}_until_cutoff` (19개)

→ 기존 `_sum_strategy`, `_max_strategy` 컬럼은 `_mean_strategy`로 대체.

#### 5-3. 결측치 처리: 플래그 + 값 분리 패턴

**결정**: 결측이 의미를 가지는 컬럼은 두 컬럼으로 분리.

**패턴**:
```
원본 컬럼 X에 결측이 있다면:
  X_missing = (X.isna()).astype(int)  # 0/1 binary
  X = X.fillna(0)                      # numeric은 0
  또는 X = X.fillna("Unknown")          # categorical은 "Unknown"
```

**근거**: "값이 없음"과 "값이 작음"은 다른 정보. 단순 imputation은 둘을 섞어버림. 플래그 컬럼을 따로 두면 모델이 두 효과를 분리해 학습 가능.

**적용 대상**:
- 인구통계: `imd_band`
- 등록: `date_registration`, `is_registered_before_start`
- 점수: `mean/min/max_score`, `weighted_score`, `scored_assessment_count`
- 활동 날짜: `first_activity_date`, `last_activity_date`, `days_since_last_activity`

#### 5-4. `date_unregistration` 처리

**결정**: Stage 4에서 cohort 적용에 이미 사용되었으므로 추가 작업 불필요.

- cohort CSV에는 이미 컬럼이 없음
- predictor로 절대 사용 안 함 (leakage)
- 0.3%에 해당하던 non-withdrawn × unreg 케이스(각 cutoff당 8명)는 cohort 적용 단계에서 이미 제외됨

#### 5-5. `assessments.date` 결측 처리: 옵션 A

**결정**: due-date 결측인 11개 assessment에 대한 **모든 제출 row를 제외**한 뒤 assessment summary 계산.

**근거**: 데이터 깨끗함을 우선. due-date가 없으면 `submitted_late` 계산 자체가 불가능하고, 그런 데이터로 계산된 다른 통계(점수 평균 등)도 일관성을 위해 제외.

**영향**: 11개 assessment 관련 제출 건만 빠짐. 전체 173,912건 중 일부.

#### 5-6. 활동 없는 학생 처리

**결정**: VLE/assessment count 계열 컬럼은 0으로 채움 (Stage 3 정책 유지).

단, 5-3 결측 플래그 규칙은 적용:
- `first_activity_date_missing = 1`
- `first_activity_date = 0`

→ 모델은 "활동 자체가 없었음"과 "활동했는데 첫 날짜가 day 0"을 구분 가능.

#### 5-7. 추가 도메인 feature

논의 결과 다음 feature들을 baseline에 포함하기로 결정.

**채택 (3종)**

| 추가 feature | 정의 | 의미 |
|---|---|---|
| `on_time_submission_count_until_cutoff` | cutoff까지 `date_submitted ≤ assessments.date`인 제출 건수 | 자기관리 능력 |
| `avg_days_before_due_until_cutoff` | cutoff까지 제출의 평균 `(due_date − submitted_date)` | 미리 제출 경향 (양수=조기, 음수=지각) |
| `is_retake` | `num_of_prev_attempts > 0` binary 파생 | 재수강 여부 (인구통계에 12.8% 해당) |

**근거**:
- **정시 제출 강화**: 현재 `submitted_late_count`(지각만 카운트) 외에 "정시"와 "조기"를 구분하면 자기관리 패턴이 더 명확. 전체 제출의 80.5%가 정시(week5 기준).
- **재수강 binary**: `num_of_prev_attempts`는 이미 있으나 0/1/2+ 의미가 비선형일 수 있음 → binary 파생으로 단순 신호 제공.

**검토 대상이지만 채택 안 함 (3종)**

| 제안 | 결정 | 이유 |
|---|---|---|
| **VLE 접근 주기** (avg/max gap, long-gap count) | **조건부 보류** — baseline에서 관련 feature 중요도 확인 후 재검토 | 데이터 검증 결과 (아래) |
| **입학 성적** | **데이터 부재** | OULAD에 입학 성적 컬럼 없음. 대체로 `highest_education`(이전 학력 5단계)이 이미 포함되어 있어 부분 대체 |
| **개인 식별 정보** | **사용 안 함** | OULAD는 이미 익명화된 공개 데이터셋이므로 추가 개인정보 이슈는 없음. 단, 논문 목적(온라인 도메인 일반화)을 고려할 때 기관별 추가 데이터를 끌어오는 방향은 적절치 않음 |

**VLE 접근 주기 보류 사유 — 데이터 검증 결과**

week5 cohort (26,453명, 활동 있는 학생만) 기준 `max_gap` 신호 강도:

| 그룹 | n | max_gap 평균 | 7일+ 비활성 발생률 |
|---|---:|---:|---:|
| target=0 (위험 없음) | 21,799 | 9.55일 | 65.8% |
| target=1 (위험) | 4,654 | 10.40일 | 71.0% |
| **차이** | | **+0.85일** | **+5.2%p** |

활동일 수를 통제해도 차이는 거의 없음 (모든 활동량 구간에서 max_gap 차이 0.4~0.7일 수준).

**근본적 이유**: "활동 간격" 정보는 이미 baseline의 `active_days_until_cutoff`와 `days_since_last_activity_at_cutoff`에 더 강한 형태로 포함됨. 별도 주기 feature는 약한 신호 + 정보 중복 가능성.

**재검토 조건**:
- baseline 모델에서 `active_days_until_cutoff` 또는 `days_since_last_activity_at_cutoff`의 feature importance가 상위권일 경우
- → 그제서야 더 정교한 주기 feature (예: `inactivity_ratio = 1 − active_days/cutoff_day`) 시도

### 보류 사항 (1차 baseline 이후 검토)

| 항목 | 재검토 조건 |
|---|---|
| VLE 접근 주기 (avg_gap, max_gap, long_gap_count, inactivity_ratio) | `active_days_until_cutoff` 또는 `days_since_last_activity_at_cutoff`의 importance가 상위권일 때만 |
| `is_banked` 사용 여부 | baseline 성능 확인 후 |
| `vle.week_from/to` 사용 여부 | baseline 성능 확인 후 |
| `module_presentation_length` 사용 여부 | baseline 성능 확인 후 |
| activity_type 19개 → 4개 그룹 차원 축소 | feature importance 확인 후 |
| 점수 결측에 mode/median 대안 | baseline 성능 확인 후 |
| Target 모호 케이스 93명 sensitivity check | baseline 학습 후 |

### 산출물 (예정)
- `features_week5_baseline.csv`
- `features_week7_baseline.csv`
- `features_week10_baseline.csv`

---

## 7. 검증 요구사항

unified CSV가 다음을 만족해야 모델링 단계로 넘어갈 수 있음:

| 검증 항목 | 기대값 |
|---|---|
| `date_unregistration` 컬럼 부재 | ✅ 없음 |
| base key 중복 | 0 |
| `final_result`, `target_withdrawn`, `target_at_risk` 모두 존재 (분석용) | ✅ |
| `target_at_risk` positive 비율 | cutoff별 41~44% |
| cutoff 이후 활동 데이터 부재 | `last_activity_date ≤ cutoff_day` |
| 모든 `_missing` 플래그 binary | 0 또는 1만 |
| VLE 컬럼 모두 `_mean_strategy` 접미사 | ✅ |
| due-date 결측 assessment 11개 제외됨 | assessment 관련 통계 검증 |
| 새 도메인 feature 존재 | `on_time_submission_count_until_cutoff`, `avg_days_before_due_until_cutoff`, `is_retake` |
| `is_retake` binary 확인 | 0 또는 1만, positive 비율 약 12.8% |

---

## 8. 1차 Baseline 권장 Feature 셋

unified CSV의 모든 컬럼 중 1차 모델에 사용할 셋 (약 28개):

| 그룹 | 컬럼 |
|---|---|
| Categorical | `code_module`, `code_presentation` |
| 인구통계 (8 + flag) | gender, region, highest_education, imd_band, age_band, num_of_prev_attempts, studied_credits, disability + `imd_band_missing` |
| 인구통계 파생 | `is_retake` (num_of_prev_attempts > 0) |
| 등록 | `is_registered_before_start`, `is_registered_before_start_missing` |
| VLE 종합 | `total_click_until_cutoff_mean_strategy`, `active_days_until_cutoff`, `days_since_last_activity_at_cutoff` (+ missing flag) |
| 과제 | `assessment_count_until_cutoff`, `mean_score_until_cutoff` (+ missing flag) |
| **정시 제출** | `on_time_submission_count_until_cutoff`, `avg_days_before_due_until_cutoff` (+ missing flag) |

**제외 (1차)**: activity_type별 19개 클릭 컬럼, weighted_score, submitted_late_count, VLE 접근 주기, conditional features.

**모델링 후보** (별도 결정):
- Logistic Regression (해석 가능 baseline)
- Random Forest (비선형 + feature importance)
- XGBoost/LightGBM (성능 + NaN 자체 지원)

---

## 9. 의사결정 요약 (한눈에)

| Stage | 결정 항목 | 선택 | 핵심 근거 |
|---|---|---|---|
| 3 | Base 단위 | studentInfo 한 행 | 모든 학생 보존 |
| 3 | VLE exact duplicate | 제거 | 명백한 중복 |
| 4 | Cohort | Active-at-cutoff | 운영 시나리오 일치 + 자명한 패턴 제거 |
| 4 | Cohort 기준 | `date_unregistration ≤ cutoff` | leakage_review 표준 |
| 5 | Target | `target_at_risk` (W+F) | Fail의 활동 패턴이 Withdrawn보다 낮음 |
| 5 | VLE 중복 | mean 전략 | 다중 시간대 접속 반영 + 과대집계 회피 |
| 5 | 결측 처리 | 플래그 + 값 분리 | "없음"과 "작음" 정보 분리 |
| 5 | assessments.date 결측 | 옵션 A (제외) | 데이터 일관성 우선 |
| 5 | 활동 0 학생 | 0 채움 + missing 플래그 | 정보 분리 + 학생 보존 |
| 5 | 정시 제출 강화 | `on_time_count`, `avg_days_before_due` 추가 | 자기관리 신호 보강 |
| 5 | 재수강 binary | `is_retake` 파생 추가 | 비선형 신호의 단순 표현 |
| 5 | VLE 접근 주기 | 보류 | 데이터 검증 결과 신호 약함 (max_gap 차이 0.85일) + baseline에 유사 feature 존재 |
| 5 | 입학 성적 | 채택 안 함 | OULAD에 컬럼 없음 (highest_education이 부분 대체) |

---

## 10. 후속 단계 (모델링)

이 파이프라인의 출력 `features_week{5,7,10}_baseline.csv`는 model-ready 상태입니다.

다음 단계에서 해야 할 작업:
1. Train/test split (cutoff별 또는 학기별)
2. Categorical encoding (one-hot 또는 target encoding)
3. Baseline 모델 학습 (LR / RF / XGB)
4. 평가 (AUC, F1, recall — class imbalance 고려)
5. Feature importance 분석
6. 보류 사항 점진 추가 (5장 마지막 표)

---

## Appendix: 산출 파일 목록

### 중간 산출물
- `data_integrity_report.md` (+ tables/ CSV 12개)
- `leakage_review.md`
- `feature_pipeline_report.md`
- `decision_log.md`
- `reviewer_summary.md`
- `features_week{5,7,10}.csv` (Stage 3)
- `features_week{5,7,10}_cohort.csv` (Stage 4)

### 최종 산출물
- `features_week{5,7,10}_baseline.csv` (Stage 5, 모델링 입력)

### 논의용 문서
- `exploring_data_report.md`
- `exploring_data_appendix.html`
- 본 문서 `data_pipeline_record.md`

---

## 12. 최종 전처리 점검 기록

점검 기준: 본 문서의 Stage 5 의사결정과 `reports/baseline_feature_report.md`.

최종 전처리 산출물은 아래 3개 CSV로 한정한다.

- `data/processed/features_week5_baseline.csv`
- `data/processed/features_week7_baseline.csv`
- `data/processed/features_week10_baseline.csv`

검증 결과:

| cutoff | rows | columns | target positive | base key duplicates | missing flags | missing cells | final Stage 5 feature 누락 |
|---|---:|---:|---:|---:|---:|---:|---|
| week5 | 27,244 | 66 | 43.53% | 0 | 12 binary | 0 | none |
| week7 | 26,776 | 66 | 42.54% | 0 | 12 binary | 0 | none |
| week10 | 26,069 | 66 | 40.98% | 0 | 12 binary | 0 | none |

확인된 사항:
- `date_unregistration` is absent from all final baseline CSV files.
- `_sum_strategy` and `_max_strategy` VLE columns are absent from final baseline CSV files.
- Each final baseline CSV has 22 `_mean_strategy` VLE columns.
- `on_time_submission_count_until_cutoff`, `avg_days_before_due_until_cutoff`, and `is_retake` are present.
- `is_retake` is binary; positive rate is about 12.6%.
- VLE activity date checks pass: `first_activity_date_until_cutoff` and `last_activity_date_until_cutoff` do not exceed the cutoff.
- No final models were trained during preprocessing.

주의 사항:
- `date_registration` has a small number of values after the cutoff (week5=15, week7=9, week10=7). The current first paper-replication notebook does not use `date_registration`, and the recommended first baseline feature set uses `is_registered_before_start` instead. If later modeling uses `date_registration` directly, decide whether to cap, exclude, or cohort-filter these rows before training.

CSV 정리:
- Final preprocessing CSVs are only `features_week{5,7,10}_baseline.csv`.
- Report evidence is kept in markdown reports rather than creating an additional baseline validation CSV.
- The paper-replication notebook saves the full model evaluation record to `reports/tables/model_results/paper_replication_baseline_results.csv`. A best-only summary CSV is not kept.
