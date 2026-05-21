# e5-small 임베딩 + LightGBM & XGBoost 
import time
import pickle
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
import xgboost as xgb
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    confusion_matrix, roc_auc_score, average_precision_score,
)

warnings.filterwarnings("ignore")

# ── 경로 & 설정 ──────────────────────────────────────────
PROJECT_ROOT  = Path(__file__).parent.parent.parent
AEGIS_PATH    = PROJECT_ROOT / "nvidia_aegis_2.0.csv"
ARTIFACTS_DIR = Path(__file__).parent.parent / "artifacts"
EMBED_PATH    = ARTIFACTS_DIR / "small" / "embeddings.npy"
LABEL_PATH    = ARTIFACTS_DIR / "small" / "labels.npy"
LGB_PATH      = ARTIFACTS_DIR / "small" / "detector_model.pkl"
XGB_PATH      = ARTIFACTS_DIR / "small" / "detector_model_xgb_small.json"

SAMPLE_SIZE      = None   # None = 전체 사용
EMBED_MODEL_NAME = "intfloat/multilingual-e5-small"
EMBED_BATCH_SIZE = 256
TEST_SIZE        = 0.2
RANDOM_STATE     = 42
# ────────────────────────────────────────────────────────

ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
(ARTIFACTS_DIR / "small").mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════
# STEP 1 | 데이터 로드 및 샘플링
# ══════════════════════════════════════════════════════
print("=" * 60)
print("STEP 1 | AEGIS 2.0 데이터 로드 및 샘플링")
print("=" * 60)

df_raw = pd.read_csv(AEGIS_PATH, encoding="utf-8-sig")
print(f"전체 행수: {len(df_raw):,}  "
      f"(safe={( df_raw['prompt_label']=='safe').sum():,}, "
      f"unsafe={(df_raw['prompt_label']=='unsafe').sum():,})")

df_raw = df_raw[df_raw["prompt_label"].isin(["safe", "unsafe"])].copy()
df_raw["label"] = (df_raw["prompt_label"] == "unsafe").astype(int)
df_raw["text"]  = df_raw["prompt"].astype(str).str.strip()
df_raw = df_raw[df_raw["text"].notna() & (df_raw["text"] != "") & (df_raw["text"].str.lower() != "redacted")]
df_raw = df_raw.drop_duplicates(subset="text").reset_index(drop=True)
print(f"정제 후:  {len(df_raw):,}행  "
      f"(safe={df_raw['label'].eq(0).sum():,}, unsafe={df_raw['label'].eq(1).sum():,})")

if SAMPLE_SIZE is None or SAMPLE_SIZE >= len(df_raw):
    df = df_raw.sample(frac=1, random_state=RANDOM_STATE).reset_index(drop=True)
    print(f"전체 데이터 사용: {len(df):,}행")
else:
    df, _ = train_test_split(
        df_raw, train_size=SAMPLE_SIZE,
        stratify=df_raw["label"], random_state=RANDOM_STATE,
    )
    df = df.reset_index(drop=True)
    print(f"샘플링 후: {len(df):,}행")

labels = df["label"].values
texts  = ["query: " + t for t in df["text"].tolist()]


# ══════════════════════════════════════════════════════
# STEP 2 | 임베딩
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print(f"STEP 2 | 텍스트 임베딩  ({EMBED_MODEL_NAME})")
print("=" * 60)

embedder = SentenceTransformer(EMBED_MODEL_NAME)
batches  = [texts[i:i + EMBED_BATCH_SIZE] for i in range(0, len(texts), EMBED_BATCH_SIZE)]
print(f"총 {len(texts):,}개 / {len(batches)}배치 / 배치 크기 {EMBED_BATCH_SIZE}\n")

t0 = time.time()
embed_list = []
for batch in tqdm(batches, desc="임베딩", unit="batch", ncols=80):
    embed_list.append(embedder.encode(batch, show_progress_bar=False))
embeddings = np.vstack(embed_list)
embed_time = time.time() - t0
print(f"\n임베딩 완료  shape={embeddings.shape}  소요={embed_time:.1f}초")


# ══════════════════════════════════════════════════════
# STEP 3 | 임베딩 저장
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("STEP 3 | 임베딩 저장")
print("=" * 60)

np.save(EMBED_PATH, embeddings)
np.save(LABEL_PATH, labels)
print(f"저장 완료 → {EMBED_PATH.name}  ({embeddings.nbytes/1024**2:.1f} MB)")


# ══════════════════════════════════════════════════════
# STEP 4 | Train / Test 분리 (80/20)
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("STEP 4 | Train / Test 분리 (80/20, stratified)")
print("=" * 60)

X_train, X_test, y_train, y_test = train_test_split(
    embeddings, labels,
    test_size=TEST_SIZE, stratify=labels, random_state=RANDOM_STATE,
)
print(f"Train: {len(X_train):,}개  (safe={( y_train==0).sum():,}, unsafe={y_train.sum():,})")
print(f"Test : {len(X_test):,}개   (safe={(y_test==0).sum():,},  unsafe={y_test.sum():,})")


# ══════════════════════════════════════════════════════
# STEP 5 | LightGBM 학습
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("STEP 5 | LightGBM 학습")
print("=" * 60)

lgb_params = {
    "objective":         "binary",
    "metric":            "binary_logloss",
    "boosting_type":     "gbdt",
    "learning_rate":     0.05,
    "num_leaves":        63,
    "max_depth":         -1,
    "min_child_samples": 20,
    "feature_fraction":  0.8,
    "bagging_fraction":  0.8,
    "bagging_freq":      5,
    "is_unbalance":      True,
    "verbose":           -1,
}

print("학습 시작 (early stopping: 50 rounds, max: 1000)...\n")
t1 = time.time()
lgb_model = lgb.train(
    lgb_params,
    lgb.Dataset(X_train, label=y_train),
    num_boost_round=1000,
    valid_sets=[
        lgb.Dataset(X_train, label=y_train),
        lgb.Dataset(X_test,  label=y_test),
    ],
    valid_names=["train", "valid"],
    callbacks=[
        lgb.early_stopping(stopping_rounds=50, verbose=True),
        lgb.log_evaluation(period=100),
    ],
)
lgb_time = time.time() - t1
print(f"\n학습 완료  최적 반복={lgb_model.best_iteration}  소요={lgb_time:.1f}초")


# ══════════════════════════════════════════════════════
# STEP 6 | XGBoost 학습
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("STEP 6 | XGBoost 학습")
print("=" * 60)

scale_pos = float((y_train == 0).sum()) / float((y_train == 1).sum())
xgb_params = {
    "objective":        "binary:logistic",
    "eval_metric":      "logloss",
    "tree_method":      "hist",
    "scale_pos_weight": scale_pos,
    "max_depth":        6,
    "learning_rate":    0.05,
    "subsample":        0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 20,
    "seed":             RANDOM_STATE,
    "verbosity":        0,
}

dm_train = xgb.DMatrix(X_train, label=y_train)
dm_test  = xgb.DMatrix(X_test,  label=y_test)

print("학습 시작 (early stopping: 50 rounds, max: 1000)...\n")
t2 = time.time()
xgb_model = xgb.train(
    xgb_params, dm_train,
    num_boost_round=1000,
    evals=[(dm_train, "train"), (dm_test, "valid")],
    early_stopping_rounds=50,
    verbose_eval=100,
)
xgb_time = time.time() - t2
print(f"\n학습 완료  최적 반복={xgb_model.best_iteration}  소요={xgb_time:.1f}초")


# ══════════════════════════════════════════════════════
# STEP 7 | 성능 평가 (LightGBM vs XGBoost)
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("STEP 7 | 성능 평가 비교")
print("=" * 60)

def metrics(y_true, prob):
    pred = (prob >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, pred).ravel()
    return {
        "acc":  accuracy_score(y_true, pred),
        "prec": precision_score(y_true, pred, zero_division=0),
        "rec":  recall_score(y_true, pred, zero_division=0),
        "f1":   f1_score(y_true, pred, zero_division=0),
        "fpr":  fp / (tn + fp) if (tn + fp) > 0 else 0,
        "fnr":  fn / (fn + tp) if (fn + tp) > 0 else 0,
        "auc":  roc_auc_score(y_true, prob),
        "aupr": average_precision_score(y_true, prob),
        "tn": tn, "fp": fp, "fn": fn, "tp": tp,
    }

lgb_m = metrics(y_test, lgb_model.predict(X_test, num_iteration=lgb_model.best_iteration))
xgb_m = metrics(y_test, xgb_model.predict(dm_test))

W = 54
print(f"\n  {'지표':<20} {'LightGBM':>14} {'XGBoost':>14}")
print(f"  {'─'*20}  {'─'*14}  {'─'*14}")
for label, key, fmt in [
    ("정확도  Accuracy",  "acc",  "pct"),
    ("정밀도  Precision", "prec", "pct"),
    ("재현율  Recall",    "rec",  "pct"),
    ("F1 Score",          "f1",   "pct"),
    ("AUC-ROC",           "auc",  "f4"),
    ("AUC-PR",            "aupr", "f4"),
    ("오탐률  FPR",       "fpr",  "pct"),
    ("미탐률  FNR",       "fnr",  "pct"),
]:
    lv = lgb_m[key]
    xv = xgb_m[key]
    if fmt == "pct":
        print(f"  {label:<20} {lv*100:>13.2f}%  {xv*100:>13.2f}%")
    else:
        print(f"  {label:<20} {lv:>14.4f}  {xv:>14.4f}")

print(f"\n  {'혼동행렬':<20} {'LightGBM':>14} {'XGBoost':>14}")
print(f"  {'─'*20}  {'─'*14}  {'─'*14}")
for label, key in [("TN", "tn"), ("FP", "fp"), ("FN", "fn"), ("TP", "tp")]:
    print(f"  {label:<20} {lgb_m[key]:>14,}  {xgb_m[key]:>14,}")


# ══════════════════════════════════════════════════════
# STEP 8 | 모델 저장
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("STEP 8 | 모델 저장")
print("=" * 60)

with open(LGB_PATH, "wb") as f:
    pickle.dump(lgb_model, f)
xgb_model.save_model(str(XGB_PATH))

print(f"LightGBM → {LGB_PATH.name}")
print(f"XGBoost  → {XGB_PATH.name}")

total = embed_time + lgb_time + xgb_time
print()
print("=" * 60)
print(f"전체 완료  임베딩={embed_time:.0f}초  LGB={lgb_time:.0f}초  XGB={xgb_time:.0f}초  합계={total:.0f}초")
print("=" * 60)
