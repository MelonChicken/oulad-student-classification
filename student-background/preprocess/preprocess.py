import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import os

# ── paths ──────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR   = os.path.join(BASE_DIR, "data", "total")
OUT_DIR    = os.path.join(BASE_DIR, "data", "preprocessed")
os.makedirs(OUT_DIR, exist_ok=True)

WEEK_CUTOFFS = {"week5": 35, "week7": 49, "week10": 70}

# ── load raw tables ────────────────────────────────────────────────────────
print("Loading raw data...")
info = pd.read_csv(os.path.join(DATA_DIR, "studentInfo.csv"))
vle  = pd.read_csv(os.path.join(DATA_DIR, "studentVle.csv"))
reg  = pd.read_csv(os.path.join(DATA_DIR, "studentRegistration.csv"))

JOIN_KEYS = ["code_module", "code_presentation", "id_student"]

# date_unregistration: "?" → NaN, 나머지 → float
reg["date_unregistration"] = pd.to_numeric(
    reg["date_unregistration"].replace("?", np.nan), errors="coerce"
)
# active-at-cutoff 필터링에 필요한 열만 보존
reg_clean = reg[JOIN_KEYS + ["date_unregistration"]].copy()

# ══════════════════════════════════════════════════════════════════════════
# 1. studentInfo 전처리  (담당 피처: highest_education, num_of_prev_attempts,
#                                    studied_credits)
# ══════════════════════════════════════════════════════════════════════════

# 1-1. highest_education → ordinal
EDU_ORDER = {
    "No Formal quals":            0,
    "Lower Than A Level":         1,
    "A Level or Equivalent":      2,
    "HE Qualification":           3,
    "Post Graduate Qualification":4,
}
info["highest_education_enc"] = info["highest_education"].map(EDU_ORDER)

# 1-2. num_of_prev_attempts → bin (0 / 1 / 2+)
info["prev_attempts_bin"] = info["num_of_prev_attempts"].clip(upper=2)

# 1-3. studied_credits → keep as numeric (scaled later per split)

# 1-4. target: final_result → int label
RESULT_MAP = {"Distinction": 0, "Pass": 1, "Fail": 2, "Withdrawn": 3}
info["label"] = info["final_result"].map(RESULT_MAP)

# base columns to carry forward
BASE_INFO_COLS = JOIN_KEYS + [
    "highest_education_enc",
    "prev_attempts_bin",
    "studied_credits",
    "label",
]
info_clean = info[BASE_INFO_COLS].copy()

print(f"  studentInfo cleaned: {info_clean.shape}")

# ══════════════════════════════════════════════════════════════════════════
# 2. VLE 집계  (base features: total_clicks, active_days)
#    week cutoff 별로 각각 집계
# ══════════════════════════════════════════════════════════════════════════

def aggregate_vle(vle_df, cutoff_day):
    """cutoff_day 이전(0~cutoff) VLE 로그만 사용해 집계.
    중복 (student, date, site) 조합은 mean으로 처리 후 집계."""
    vle_cut = vle_df[(vle_df["date"] >= 0) & (vle_df["date"] <= cutoff_day)].copy()
    # mean strategy: 같은 (student, date, site) 중복 행 → 평균
    vle_dedup = (
        vle_cut
        .groupby(JOIN_KEYS + ["date", "id_site"], as_index=False)["sum_click"]
        .mean()
    )
    agg = (
        vle_dedup
        .groupby(JOIN_KEYS)
        .agg(
            total_clicks  =("sum_click", "sum"),
            active_days   =("date",      "nunique"),
        )
        .reset_index()
    )
    return agg


# ══════════════════════════════════════════════════════════════════════════
# 3. 최종 데이터셋 생성  (ver1 / ver2 × week5 / week7 / week10)
# ══════════════════════════════════════════════════════════════════════════

VER1_FEATURES = ["highest_education_enc", "prev_attempts_bin", "studied_credits"]
VER2_FEATURES = VER1_FEATURES + ["total_clicks", "active_days"]

print("\nAggregating VLE by week cutoff...")
vle_aggs = {}
for week, cutoff in WEEK_CUTOFFS.items():
    vle_aggs[week] = aggregate_vle(vle, cutoff)
    print(f"  {week} (day <= {cutoff}): {vle_aggs[week].shape[0]} student-course rows")

scaler_params = {}   # week → scaler (fitted on ver2, reused on ver2)

for week, cutoff in WEEK_CUTOFFS.items():
    merged = info_clean.merge(vle_aggs[week], on=JOIN_KEYS, how="left")

    # VLE 없는 학생(행동 로그 0) → 0으로 채움
    merged["total_clicks"] = merged["total_clicks"].fillna(0).astype(int)
    merged["active_days"]  = merged["active_days"].fillna(0).astype(int)

    # ── active-at-cutoff 필터링 ─────────────────────────────────────────
    # cutoff 이전에 이미 탈락한 학생 제외
    merged = merged.merge(reg_clean, on=JOIN_KEYS, how="left")
    merged = merged[
        merged["date_unregistration"].isna() |
        (merged["date_unregistration"] >= cutoff)
    ].drop(columns=["date_unregistration"])
    print(f"  {week}: {len(merged)} rows after active-at-cutoff filter (was 32593)")

    # ── ver1: 담당 피처만 ───────────────────────────────────────────────
    df_v1 = merged[JOIN_KEYS + VER1_FEATURES + ["label"]].copy()

    # studied_credits 스케일링 (ver1 전용 scaler)
    sc1 = StandardScaler()
    df_v1 = df_v1.copy()
    df_v1["studied_credits"] = sc1.fit_transform(df_v1[["studied_credits"]])

    out1 = os.path.join(OUT_DIR, f"ver1_{week}.csv")
    df_v1.to_csv(out1, index=False)
    print(f"  Saved: ver1_{week}.csv  shape={df_v1.shape}")

    # ── ver2: base 피처 + 담당 피처 ────────────────────────────────────
    df_v2 = merged[JOIN_KEYS + VER2_FEATURES + ["label"]].copy()

    sc2 = StandardScaler()
    df_v2[["studied_credits", "total_clicks", "active_days"]] = sc2.fit_transform(
        df_v2[["studied_credits", "total_clicks", "active_days"]]
    )

    out2 = os.path.join(OUT_DIR, f"ver2_{week}.csv")
    df_v2.to_csv(out2, index=False)
    print(f"  Saved: ver2_{week}.csv  shape={df_v2.shape}")

print("\nDone. Output files:")
for f in sorted(os.listdir(OUT_DIR)):
    path = os.path.join(OUT_DIR, f)
    print(f"  {f}  ({os.path.getsize(path)//1024} KB)")
