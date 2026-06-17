# -*- coding: utf-8 -*-
"""
feature_analysis.py  –  피처별 통계 기반 기여도 분석
대상: ver2_week10 (최고 성능 데이터셋, 이진 타겟 기준)
출력: mean by class / mean diff / Cohen's D / correlation w/ target
"""

import os
import numpy as np
import pandas as pd

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR   = os.path.join(BASE_DIR, "data", "preprocessed")
RESULT_DIR = os.path.join(BASE_DIR, "result")
os.makedirs(RESULT_DIR, exist_ok=True)

# ── 데이터 로드 & 이진 타겟 생성 ──────────────────────────────────────────
df = pd.read_csv(os.path.join(DATA_DIR, "ver2_week10.csv"))
df["binary_label"] = (df["label"] >= 2).astype(int)  # 0=success / 1=at-risk

FEATURES = [
    "highest_education_enc",
    "prev_attempts_bin",
    "studied_credits",
    "total_clicks",
    "active_days",
]

FEATURE_LABELS = {
    "highest_education_enc": "highest_education",
    "prev_attempts_bin":     "prev_attempts",
    "studied_credits":       "studied_credits",
    "total_clicks":          "total_clicks",
    "active_days":           "active_days",
}

# ── 통계 계산 ─────────────────────────────────────────────────────────────
records = []

for feat in FEATURES:
    g0 = df.loc[df["binary_label"] == 0, feat]
    g1 = df.loc[df["binary_label"] == 1, feat]

    mean0 = g0.mean()
    mean1 = g1.mean()
    diff  = mean1 - mean0

    # Cohen's D  (pooled std)
    n0, n1   = len(g0), len(g1)
    pooled_std = np.sqrt(((n0 - 1) * g0.std(ddof=1)**2 + (n1 - 1) * g1.std(ddof=1)**2)
                         / (n0 + n1 - 2))
    cohens_d = diff / pooled_std if pooled_std > 0 else 0.0

    # Pearson correlation with binary target
    corr = df[feat].corr(df["binary_label"])

    records.append({
        "feature":        FEATURE_LABELS[feat],
        "mean_success":   round(mean0, 3),
        "mean_atrisk":    round(mean1, 3),
        "mean_diff":      round(diff,  3),
        "cohens_d":       round(cohens_d, 3),
        "corr_w_target":  round(corr, 3),
    })

result_df = pd.DataFrame(records)

# |Cohen's D| 기준 내림차순 정렬
result_df["abs_d"] = result_df["cohens_d"].abs()
result_df = result_df.sort_values("abs_d", ascending=False).drop(columns="abs_d")
result_df = result_df.reset_index(drop=True)

# ── 출력 ──────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("  Feature Analysis  |  ver2_week10  |  Binary Target (0=success / 1=at-risk)")
print("="*70)
print(f"  {'Feature':<28} {'Mean(0)':>10} {'Mean(1)':>10} {'Diff':>10} {'Cohen D':>10} {'Corr':>8}")
print("-"*70)
for _, row in result_df.iterrows():
    print(f"  {row['feature']:<28} {row['mean_success']:>10.3f} {row['mean_atrisk']:>10.3f} "
          f"{row['mean_diff']:>10.3f} {row['cohens_d']:>10.3f} {row['corr_w_target']:>8.3f}")
print("="*70)

# ── 저장 ──────────────────────────────────────────────────────────────────
out = os.path.join(RESULT_DIR, "feature_analysis.csv")
result_df.to_csv(out, index=False)
print(f"\nSaved → {out}")
