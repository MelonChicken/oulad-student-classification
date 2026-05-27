# OULAD 조기 이탈 예측 - 데이터 탐색 리포트 (논의용)

> 데이터 감사·누수 검토·feature pipeline 완료. cohort 결정 완료. 이 문서는 모델링 직전 **남은 결정 사항**을 정리한 자료. 시각화는 `exploring_data_appendix.html` 참조.

---

## 1. 프로젝트 개요

- **목표**: week 5/7/10 (학기 시작 후 35/49/70일) 시점에 학생의 학업 위험 예측
- **데이터**: OULAD (Kaggle 버전), `student_info` 기준 32,593행 (학생 × 모듈 × 학기)
- **주요 feature 소스**: VLE 클릭 로그 10.6M행, 과제 제출 173.9K행

---

## 1.5 핵심 개념 정리

이 리포트에서 반복적으로 등장하는 용어들의 정의입니다.

### Cohort (코호트)
**예측 모델의 대상이 되는 학생 집단**. 통계학·역학에서 "특정 조건을 공유하는 집단"을 가리키는 용어입니다.

이 프로젝트에서는 **"각 cutoff 시점에 실제로 예측 대상이 되는 학생들"**을 의미합니다. 예를 들어 week5 cohort = "day 35 시점에 아직 학교에 남아있는, 그래서 예측이 의미 있는 학생들"입니다.

> **왜 중요한가?** 이미 학교를 떠난 학생을 "곧 떠날 사람"으로 예측하는 건 의미 없습니다. 실제 운영 시 모델은 "현재 등록 중인 학생"에 대해서만 돌아갑니다. 따라서 학습 데이터도 그 조건과 일치시켜야 합니다 — 이것이 "active-at-cutoff cohort" 정의의 핵심.

### Cutoff (컷오프, 예측 시점)
**학생의 미래를 예측하는 기준 시점**. 이 프로젝트에서는 학기 시작 후 day 35 (week5), day 49 (week7), day 70 (week10) 세 가지를 사용합니다. cutoff 이후의 정보는 학습에 사용하면 안 됩니다(미래 정보 사용 = leakage).

### Leakage (누수)
**예측 시점 이후의 정보가 feature에 섞여 들어가는 것**. 예를 들어 day 35 모델인데 day 50에 발생한 과제 점수를 feature로 쓰면 → 모델은 "미래를 보고 예측"하는 셈이 되어 실제 운영에서 작동하지 않습니다. `date_unregistration`(탈퇴 날짜)을 predictor에서 제외한 것도 leakage 방지.

### Target (타겟, 예측 대상)
**모델이 맞추려는 정답 변수**. 이 프로젝트에서는 cohort 안에서 어떤 학생을 "위험"으로 정의할지가 핵심 결정사항 (쟁점 ①).

---

## 2. 결정 완료 사항

### ✅ Cohort: Active-at-cutoff
- `date_unregistration ≤ cutoff_day`인 학생을 각 cutoff에서 제외
- 이유: 이미 떠난 학생은 활동도 거의 없어 "활동 없음 = 탈퇴"라는 자명한 패턴만 학습하게 됨

### Cohort 적용 결과

| cutoff | 원본 | 제외 | **cohort** |
|---|---:|---:|---:|
| week5 (day 35) | 32,593 | 5,349 | **27,244** |
| week7 (day 49) | 32,593 | 5,817 | **26,776** |
| week10 (day 70) | 32,593 | 6,524 | **26,069** |

- "활동 없음 → 탈퇴" 비율: cohort 적용 전 82.9% → 후 20.4% (week5 기준), 자명한 패턴 해소

### 생성 파일
- `features_week5_cohort.csv` (27,244 × 68)
- `features_week7_cohort.csv` (26,776 × 68)
- `features_week10_cohort.csv` (26,069 × 70)

---

## 3. Cohort 적용 후 데이터 특성

### Cohort 내 결과별 분포 (모든 cutoff 공통, withdrawn만 cutoff별로 다름)

| 결과 | week5 | week7 | week10 |
|---|---:|---:|---:|
| Pass | 12,361 | 12,361 | 12,361 |
| Fail | 7,044 | 7,044 | 7,044 |
| **Withdrawn** | **4,815** | **4,347** | **3,640** |
| Distinction | 3,024 | 3,024 | 3,024 |

### Cutoff별 feature 신호 분포

| cutoff | VLE 활동 학생 (cohort 내) | 과제 제출 학생 (cohort 내) | VLE 활동 0인 학생 |
|---|---:|---:|---:|
| week5 | 26,453 | 22,394 | 791 |
| week7 | 26,126 | 22,884 | 650 |
| week10 | 25,540 | 24,168 | 529 |

- VLE는 week5에 거의 모두 시작, 과제 제출은 후반 cutoff에서 더 풍부
- → 후반 cutoff일수록 assessment feature 신호 비중 ↑

### 주요 결측 컬럼 (week5 cohort 기준)

| 컬럼 | 결측 | 의미 |
|---|---:|---|
| `weighted_score` | 6,413 | 가중치 있는 과제 미제출 |
| `mean/min/max_score` | 4,662 | 점수 받은 제출 없음 |
| activity date 계열 | 791 | VLE 활동 없음 |
| `imd_band` | 1,022 | 사회경제지표 원본 결측 |

**핵심 판단**: 점수·활동 결측은 "제출/활동 안 함"이라는 정보 그 자체 → 평균 imputation은 정보 왜곡

---

## 4. 남은 결정 사항

### 쟁점 ① Target 정의: Withdrawn만? Fail만? 둘 다?

**가장 본질적인 결정**입니다. 무엇을 "위험"으로 정의할지에 따라 모델의 정체성이 달라집니다.

#### Cohort 내 분포

| Target 정의 | week5 positive | week7 positive | week10 positive | 비율 (week10) |
|---|---:|---:|---:|---:|
| **A. Withdrawn만** | 4,815 (17.7%) | 4,347 (16.2%) | 3,640 (14.0%) | 14.0% |
| **B. Fail만** | 7,044 (25.9%) | 7,044 (26.3%) | 7,044 (27.0%) | 27.0% |
| **C. Withdrawn + Fail (struggling)** | 11,859 (43.5%) | 11,391 (42.5%) | 10,684 (41.0%) | 41.0% |

#### Cutoff 시점 행동 차이 (week5 기준)

| 결과 | n | 평균 클릭 | 평균 활성일 | 평균 과제 제출 | 활동 0인 비율 |
|---|---:|---:|---:|---:|---:|
| Distinction | 3,024 | 633 | 23.4 | 1.22 | 0.6% |
| Pass | 12,361 | 459 | 19.5 | 1.18 | 0.9% |
| **Withdrawn** | **4,815** | **320** | **15.2** | **1.02** | **3.3%** |
| **Fail** | **7,044** | **248** | **12.0** | **0.95** | **7.1%** |

**중요한 관찰**: cutoff 시점에는 **Fail 학생이 Withdrawn 학생보다 더 활동이 적음**. 즉 활동 신호만으로는 두 그룹 구분이 어렵고, 결과적으로 둘은 행동적으로 매우 유사한 "위험군"으로 볼 수 있음.

#### 대안과 장단점

| 대안 | 장점 | 단점 |
|---|---|---|
| **A. Withdrawn만 (현재 default)** | 정의 단순. "이탈"이라는 명확한 사건 | Fail도 위험인데 놓침. cutoff에서 Fail이 더 활동 적은데 무시 |
| **B. Fail만** | 학업 실패에 집중. label 풍부(25-27%) | "Withdrawn"이 빠지는 게 부자연스러움 |
| **C. Withdrawn + Fail (struggling)** | **개입 대상 모두 포함**. label 가장 풍부(41-44%) | "둘이 다른 현상"이라는 주장에 약함. 해석 약간 모호 |
| **D. 다중 분류 (4-class)** | 정보 손실 없음 | 모델 복잡, 평가 어려움, 운영 시점 의사결정 모호 |

> **추천 논점**: "조기 경고 시스템이 누구를 위해 무엇을 하는 것인가?"
> - 교수가 개입할 대상을 찾는다면 → **C (struggling)** 가 가장 실용적
> - 휴학 상담/리텐션 정책 대상이라면 → **A (Withdrawn)**
> - Fail이 행동적으로 Withdrawn보다 더 위험해 보인다는 데이터는 **C 또는 B**를 강하게 지지

---

### 쟁점 ② VLE 중복 처리

`student_vle` 키 중복이 exact duplicate 제거 후에도 1.4M행 남음. 같은 키의 `sum_click` 값이 모두 다름.

| 대안 | 장단점 |
|---|---|
| **A. sum (합산)** | 모든 활동 반영 vs 과대 집계 가능 |
| **B. max (최댓값)** | 보수적·안전 vs 진짜 다중 세션도 축소 |
| **C. 둘 다 만들어 비교** | 실증적 판단 vs 실험 복잡 |

참고: sum vs max 차이가 cutoff별로 11% 일정 → 데이터 수집 단계의 시스템적 문제 가능성.

> Kaggle 원본의 중복이 오류인지 정상인지 확인 후 결정 권장.

---

### 쟁점 ③ 결측치 처리

| 컬럼 그룹 | 권장 처리 방향 |
|---|---|
| 점수·활동 결측 | 결측 플래그 + 0 채우기 또는 별도 처리 |
| `imd_band` | "Unknown" 범주 (결측 자체가 신호일 수 있음) |
| `assessments.date` 11개 | 해당 과제만 due-date feature에서 제외 |

> 모델 종류에 따라 다름: tree 계열은 NaN 그대로, linear 계열은 imputation 필요.

---

### 쟁점 ④ Target 모호 케이스 (Cohort 내 잔류분)

Withdrawn인데 `date_unregistration` 결측 93명은 cohort에 그대로 포함됨 (제외 조건 불충족).

| 대안 | 장단점 |
|---|---|
| **A. cohort 유지** | 정의 일관성 vs 모호 케이스 포함 |
| **B. 별도 제외** | 깨끗 vs 93명 손실 |
| **C. sensitivity check** | 본 모델 후 별도 검증 |

> 절대 수가 작으니 일단 cohort에 유지하고 최종 모델 후 C로 검증 권장.

---

### 쟁점 ⑤ Conditional features 채택 여부

| feature | 검토 포인트 |
|---|---|
| `weighted_score_until_cutoff` | 가중치 사전 공지 여부 (보통 가능) |
| `submitted_late_count` | `assessments.date` 결측 처리에 의존 |
| `is_banked` | cutoff 시점에 결정 완료되어 있는지 확인 |
| `vle.week_from/to` | 82.4% 결측, 사용 어려움 |

> 1차 모델 후 점진적 추가 가능.

---

### 쟁점 ⑥ 참조 무결성 미스매치

- `student_vle → student_info`: 3,365 unmatched
- `student_assessment → assessments`: 18 unmatched
- `student_vle → vle`: 96 unmatched

→ `student_info` left join 구조에서 자동 제외, 현재 pipeline에서 이미 해결. 원인 파악은 추후 권장.

---

## 5. 결정 우선순위

1. **① Target 정의** — 모델 정체성을 결정하는 가장 본질적인 사안
2. **② VLE 중복** — 가장 큰 feature 그룹에 직접 영향
3. **③ 결측치** — 모델 입력 형태 확정
4. **④ Target 모호 케이스** — 영향 작음, sensitivity check로 보완 가능
5. **⑤ Conditional features** — 1차 모델 후 점진 추가
6. **⑥ 참조 무결성** — 현재 조치 불필요

> **제안**: 1차 baseline은 보수적 선택 (예: Target C struggling + max + 결측 플래그)으로 만들고, 다른 옵션과 비교하는 방식.
