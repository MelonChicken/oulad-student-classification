# -*- coding: utf-8 -*-
"""
modeling_add_ext_binary.py  –  add_ext 이진 분류
0 = Distinction + Pass / 1 = Fail + Withdrawn
"""

import os
import pandas as pd
import numpy as np
from sklearn.base import clone
from sklearn.model_selection import StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import (
    precision_score, recall_score, f1_score,
    roc_auc_score, classification_report
)

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR   = os.path.join(BASE_DIR, "data", "preprocessed")
RESULT_DIR = os.path.join(BASE_DIR, "result")
os.makedirs(RESULT_DIR, exist_ok=True)

MODELS = {
    "RandomForest": RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42),
    "DecisionTree": DecisionTreeClassifier(max_depth=10,     class_weight="balanced", random_state=42),
    "NaiveBayes":   GaussianNB(),
    "KNN":          KNeighborsClassifier(n_neighbors=5),
}
DROP_COLS = ["code_module", "code_presentation", "id_student", "label"]

def to_binary(s): return (s >= 2).astype(int)

path = os.path.join(DATA_DIR, "add_ext.csv")
df = pd.read_csv(path)
X  = df.drop(columns=DROP_COLS).values
y  = to_binary(df["label"])

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

print(f"\n{'='*55}")
print(f"  add_ext  |  at-risk={y.sum()}  total={len(y)}")
print(f"{'='*55}")

records = []

for name, clf in MODELS.items():
    fold_metrics = []
    for train_idx, test_idx in skf.split(X, y):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        model = clone(clf)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]
        fold_metrics.append({
            "p":   precision_score(y_test, y_pred, zero_division=0),
            "r":   recall_score   (y_test, y_pred, zero_division=0),
            "f1":  f1_score       (y_test, y_pred, zero_division=0),
            "f1m": f1_score       (y_test, y_pred, average="macro", zero_division=0),
            "auc": roc_auc_score  (y_test, y_prob),
        })
    p   = np.mean([m["p"]   for m in fold_metrics])
    r   = np.mean([m["r"]   for m in fold_metrics])
    f1  = np.mean([m["f1"]  for m in fold_metrics])
    f1m = np.mean([m["f1m"] for m in fold_metrics])
    auc = np.mean([m["auc"] for m in fold_metrics])

    print(f"  [{name:<14}]  P={p:.4f}  R={r:.4f}  "
          f"F1={f1:.4f}  F1-macro={f1m:.4f}  AUC={auc:.4f}")

    records.append({
        "version": "add_ext", "week": "N/A", "model": name,
        "precision": round(p,   4), "recall":   round(r,   4),
        "f1_atrisk": round(f1,  4), "f1_macro": round(f1m, 4),
        "roc_auc":   round(auc, 4),
    })

results_df = pd.DataFrame(records)
out = os.path.join(RESULT_DIR, "results_add_ext_binary.csv")
results_df.to_csv(out, index=False)
print(f"\nSaved → {out}")
print(results_df.to_string(index=False))
