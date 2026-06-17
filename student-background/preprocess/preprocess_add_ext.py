# -*- coding: utf-8 -*-
"""
preprocess_add_ext.py  –  add feature extension  (ver1 기반, 행동 데이터 없음)
추가 파생 변수:
  credits_bin      = studied_credits 구간화  (0: ≤60 / 1: 61~120 / 2: 121+)
  edu_x_attempts   = highest_education_enc × prev_attempts_bin  (교호작용)
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "total")
OUT_DIR  = os.path.join(os.path.dirname(__file__), "data", "preprocessed")
os.makedirs(OUT_DIR, exist_ok=True)

JOIN_KEYS = ["code_module", "code_presentation", "id_student"]

print("Loading studentInfo...")
info = pd.read_csv(os.path.join(DATA_DIR, "studentInfo.csv"))

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

# ── 파생 변수 ──────────────────────────────────────────────────────────────
def credits_bin(x):
    if x <= 60:   return 0   # light
    if x <= 120:  return 1   # medium
    return 2                  # heavy

info["credits_bin"]     = info["studied_credits"].apply(credits_bin)
info["edu_x_attempts"]  = info["highest_education_enc"] * info["prev_attempts_bin"]

feature_cols = [
    "highest_education_enc",
    "prev_attempts_bin",
    "studied_credits",
    "credits_bin",
    "edu_x_attempts",
]

df_out = info[JOIN_KEYS + feature_cols + ["label"]].copy()

# studied_credits / edu_x_attempts 스케일링 (연속형만)
sc = StandardScaler()
df_out[["studied_credits", "edu_x_attempts"]] = sc.fit_transform(
    df_out[["studied_credits", "edu_x_attempts"]]
)

# static 피처라 week 구분 없이 하나의 파일로 저장
path = os.path.join(OUT_DIR, "add_ext.csv")
df_out.to_csv(path, index=False)
print(f"Saved: add_ext.csv  shape={df_out.shape}")
print("Done.")
