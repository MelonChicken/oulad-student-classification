# -*- coding: utf-8 -*-
"""
preprocess_base_ext.py  –  base feature extension
추가 파생 변수:
  engagement_rate = active_days / cutoff_day
  clicks_per_day  = total_clicks / active_days  (active_days=0 이면 0)
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "total")
OUT_DIR  = os.path.join(BASE_DIR, "data", "preprocessed")
os.makedirs(OUT_DIR, exist_ok=True)

WEEK_CUTOFFS = {"week5": 35, "week7": 49, "week10": 70}
JOIN_KEYS    = ["code_module", "code_presentation", "id_student"]

# ── studentInfo ────────────────────────────────────────────────────────────
print("Loading raw data...")
info = pd.read_csv(os.path.join(DATA_DIR, "studentInfo.csv"))
vle  = pd.read_csv(os.path.join(DATA_DIR, "studentVle.csv"))
reg  = pd.read_csv(os.path.join(DATA_DIR, "studentRegistration.csv"))

reg["date_unregistration"] = pd.to_numeric(
    reg["date_unregistration"].replace("?", np.nan), errors="coerce"
)
reg_clean = reg[JOIN_KEYS + ["date_unregistration"]].copy()

EDU_ORDER = {
    "No Formal quals":             0,
    "Lower Than A Level":          1,
    "A Level or Equivalent":       2,
    "HE Qualification":            3,
    "Post Graduate Qualification": 4,
}
info["highest_education_enc"] = info["highest_education"].map(EDU_ORDER)
info["prev_attempts_bin"]     = info["num_of_prev_attempts"].clip(upper=2)
info["label"]                 = info["final_result"].map(
    {"Distinction": 0, "Pass": 1, "Fail": 2, "Withdrawn": 3}
)

info_clean = info[JOIN_KEYS + ["highest_education_enc", "prev_attempts_bin",
                                "studied_credits", "label"]].copy()

# ── VLE 집계 + 파생 변수 ───────────────────────────────────────────────────
def aggregate_vle(vle_df, cutoff_day):
    vle_cut = vle_df[(vle_df["date"] >= 0) & (vle_df["date"] <= cutoff_day)]
    # mean strategy: 같은 (student, date, site) 중복 행 → 평균
    vle_dedup = (
        vle_cut
        .groupby(JOIN_KEYS + ["date", "id_site"], as_index=False)["sum_click"]
        .mean()
    )
    return (
        vle_dedup.groupby(JOIN_KEYS)
        .agg(total_clicks=("sum_click", "sum"), active_days=("date", "nunique"))
        .reset_index()
    )

print("\nProcessing weeks...")
for week, cutoff in WEEK_CUTOFFS.items():
    agg = aggregate_vle(vle, cutoff)
    merged = info_clean.merge(agg, on=JOIN_KEYS, how="left")
    merged["total_clicks"] = merged["total_clicks"].fillna(0).astype(int)
    merged["active_days"]  = merged["active_days"].fillna(0).astype(int)

    # ── active-at-cutoff 필터링 ─────────────────────────────────────────
    merged = merged.merge(reg_clean, on=JOIN_KEYS, how="left")
    merged = merged[
        merged["date_unregistration"].isna() |
        (merged["date_unregistration"] >= cutoff)
    ].drop(columns=["date_unregistration"])
    print(f"  {week}: {len(merged)} rows after active-at-cutoff filter")

    # ── 파생 변수 ──────────────────────────────────────────────────────────
    merged["engagement_rate"] = merged["active_days"] / cutoff          # 0~1
    merged["clicks_per_day"]  = np.where(
        merged["active_days"] > 0,
        merged["total_clicks"] / merged["active_days"],
        0.0
    )

    feature_cols = [
        "highest_education_enc", "prev_attempts_bin", "studied_credits",
        "total_clicks", "active_days",
        "engagement_rate", "clicks_per_day",
    ]

    df_out = merged[JOIN_KEYS + feature_cols + ["label"]].copy()

    # 수치형 피처 스케일링
    scale_cols = ["studied_credits", "total_clicks", "active_days",
                  "engagement_rate", "clicks_per_day"]
    sc = StandardScaler()
    df_out[scale_cols] = sc.fit_transform(df_out[scale_cols])

    path = os.path.join(OUT_DIR, f"base_ext_{week}.csv")
    df_out.to_csv(path, index=False)
    print(f"  Saved: base_ext_{week}.csv  shape={df_out.shape}")

print("Done.")
