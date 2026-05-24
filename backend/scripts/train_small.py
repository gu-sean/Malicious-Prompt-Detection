#   [1] e5-small + LightGBM
#   [2] e5-small + XGBoost

import sys
import time
import glob
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
    confusion_matrix, roc_auc_score,
)

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")

# ── 경로 & 설정 ──────────────────────────────────────────────
SCRIPTS_DIR   = Path(__file__).parent
ARTIFACTS_DIR = SCRIPTS_DIR.parent / "artifacts"
PARQUET_GLOB  = str(SCRIPTS_DIR / "train-*.parquet")

SMALL_MODEL  = "intfloat/multilingual-e5-small"
SAMPLE_SMALL = None    
EMBED_BATCH  = 512      # GPU에서 배치 크기 2배로 증가
TEST_SIZE    = 0.2
RANDOM_STATE = 42

ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
(ARTIFACTS_DIR / "small").mkdir(parents=True, exist_ok=True)

TOTAL_START = time.time()
timing = {}


# ════════════════════════════════════════════════════════════
# STEP 1 | parquet 4-shard 로드 & 전처리
# ════════════════════════════════════════════════════════════
print("=" * 65)
print("STEP 1 | parquet 로드")
print("=" * 65)

t0    = time.time()
files = sorted(glob.glob(PARQUET_GLOB))
if not files:
    print(f"[오류] parquet 파일 없음: {PARQUET_GLOB}")
    sys.exit(1)

frames = []
for f in files:
    shard = pd.read_parquet(f)
    print(f"  {Path(f).name} : {len(shard):,}행")
    frames.append(shard)

df_all = pd.concat(frames, ignore_index=True)
timing["로드"] = time.time() - t0

df_all["label"] = df_all["is_dangerous"].astype(int)
df_all["text"]  = df_all["prompt"].astype(str).str.strip()
df_all = df_all[df_all["text"].notna() & (df_all["text"] != "") & (df_all["text"].str.len() >= 5)]
df_all = df_all.drop_duplicates(subset="text").reset_index(drop=True)

mal = df_all["label"].eq(1).sum()
nor = df_all["label"].eq(0).sum()
print(f"\n  전체: {len(df_all):,}행  |  악성={mal:,}  정상={nor:,}")
print(f"  로드 소요: {timing['로드']:.1f}초")


# ── 공통 함수 ────────────────────────────────────────────────
def sample_data(df, n):
    if n is None or n >= len(df):
        out = df.sample(frac=1, random_state=RANDOM_STATE).reset_index(drop=True)
        print(f"  전체 사용: {len(out):,}행")
    else:
        out, _ = train_test_split(df, train_size=n, stratify=df["label"], random_state=RANDOM_STATE)
        out = out.reset_index(drop=True)
        print(f"  계층 샘플링: {len(out):,}행  (악성={out['label'].eq(1).sum():,}  정상={out['label'].eq(0).sum():,})")
    return out


def scan_best(y_true, y_prob):
    best_all   = None   
    best_f1fpr = None   
    for ti in range(1, 199):
        t    = ti / 200
        pred = (y_prob >= t).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true, pred).ravel()
        fpr = fp / (tn + fp) if (tn + fp) > 0 else 0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0
        f1  = f1_score(y_true, pred, zero_division=0)
        if f1 >= 0.85 and fpr < 0.10 and fnr < 0.10:
            if best_all is None or f1 > best_all[2]:
                best_all = (round(t, 3), fpr, f1, fnr)
        if f1 >= 0.85 and fpr < 0.10:
            if best_f1fpr is None or fnr < best_f1fpr[3]:
                best_f1fpr = (round(t, 3), fpr, f1, fnr)
    best_f1t, best_f1 = 0.5, 0.0
    for ti in range(1, 199):
        t = ti / 200
        f = f1_score(y_true, (y_prob >= t).astype(int), zero_division=0)
        if f > best_f1:
            best_f1, best_f1t = f, round(t, 3)
    return best_all, best_f1fpr, best_f1t


def full_metrics(y_true, y_prob, t):
    pred = (y_prob >= t).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, pred).ravel()
    return {
        "t":   t,
        "f1":  f1_score(y_true, pred, zero_division=0),
        "fpr": fp / (tn + fp) if (tn + fp) > 0 else 0,
        "fnr": fn / (fn + tp) if (fn + tp) > 0 else 0,
        "acc": accuracy_score(y_true, pred),
        "prec":precision_score(y_true, pred, zero_division=0),
        "rec": recall_score(y_true, pred, zero_division=0),
        "auc": roc_auc_score(y_true, y_prob),
        "tn":int(tn), "fp":int(fp), "fn":int(fn), "tp":int(tp),
    }


def print_result(m, tag=""):
    g_f1  = "✅" if m["f1"]  >= 0.85 else "❌"
    g_fpr = "✅" if m["fpr"] <  0.10 else "❌"
    g_fnr = "✅" if m["fnr"] <  0.10 else "❌"
    print(f"  │  [{tag}]  t={m['t']:.3f}  "
          f"F1={m['f1']*100:.1f}% {g_f1}  "
          f"FPR={m['fpr']*100:.1f}% {g_fpr}  "
          f"FNR={m['fnr']*100:.1f}% {g_fnr}  "
          f"AUC={m['auc']:.4f}")
    print(f"  │    TP={m['tp']:,}  FP={m['fp']:,}  TN={m['tn']:,}  FN={m['fn']:,}")


# ════════════════════════════════════════════════════════════
# STEP 2 | e5-small 임베딩 (캐시 있으면 재사용)
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 65)
_sample_label = "전체" if SAMPLE_SMALL is None else f"{SAMPLE_SMALL:,}"
print(f"STEP 2 | e5-small 임베딩  (샘플={_sample_label}행)")
print("=" * 65)

_emb_cache = ARTIFACTS_DIR / "small" / "embeddings.npy"
_lbl_cache = ARTIFACTS_DIR / "small" / "labels.npy"
_cache_ok  = (
    _emb_cache.exists() and _lbl_cache.exists() and
    (SAMPLE_SMALL is None or len(np.load(_lbl_cache)) == SAMPLE_SMALL)
)

if _cache_ok:
    print("  캐시 발견 → 재사용 (임베딩 생략)")
    emb_s    = np.load(_emb_cache)
    labels_s = np.load(_lbl_cache)
    timing["e5-small 임베딩"] = 0.0
    print(f"  로드 완료  shape={emb_s.shape}")
else:
    df_s     = sample_data(df_all, SAMPLE_SMALL)
    labels_s = df_s["label"].values
    texts    = ["query: " + t for t in df_s["text"].tolist()]

    embedder = SentenceTransformer(SMALL_MODEL)
    batches  = [texts[i:i+EMBED_BATCH] for i in range(0, len(texts), EMBED_BATCH)]
    print(f"  {len(texts):,}개 / {len(batches)}배치 / 배치크기={EMBED_BATCH}")

    t0 = time.time()
    parts = []
    for batch in tqdm(batches, desc="  임베딩(e5-small)", unit="batch", ncols=70):
        parts.append(embedder.encode(batch, show_progress_bar=False))
    emb_s = np.vstack(parts)
    timing["e5-small 임베딩"] = time.time() - t0

    np.save(_emb_cache, emb_s)
    np.save(_lbl_cache, labels_s)
    print(f"  임베딩 완료  shape={emb_s.shape}  소요={timing['e5-small 임베딩']:.1f}초")

X_tr, X_te, y_tr, y_te = train_test_split(
    emb_s, labels_s, test_size=TEST_SIZE, stratify=labels_s, random_state=RANDOM_STATE
)
print(f"  Train: {len(X_tr):,}  Test: {len(X_te):,}")


# ════════════════════════════════════════════════════════════
# STEP 3 | 모델 [1]  e5-small + LightGBM
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 65)
print("STEP 3 | 모델 [1]  e5-small + LightGBM")
print("=" * 65)

lgb_params = {
    "objective": "binary", "metric": "binary_logloss",
    "boosting_type": "gbdt",
    "device": "gpu",          
    "learning_rate": 0.03,
    "num_leaves": 127,
    "max_depth": 8,
    "min_child_samples": 10,
    "feature_fraction": 0.7,
    "bagging_fraction": 0.8, "bagging_freq": 5,
    "reg_alpha": 0.05, "reg_lambda": 0.1,
    "is_unbalance": False,
    "scale_pos_weight": 1.0,   
    "verbose": -1,
}

t0 = time.time()
lgb_m = lgb.train(
    lgb_params,
    lgb.Dataset(X_tr, label=y_tr),
    num_boost_round=2000,
    valid_sets=[lgb.Dataset(X_tr, label=y_tr), lgb.Dataset(X_te, label=y_te)],
    valid_names=["train", "valid"],
    callbacks=[lgb.early_stopping(100, verbose=True), lgb.log_evaluation(200)],
)
timing["[1] e5-small + LGB"] = time.time() - t0
print(f"\n  학습 완료  best_iter={lgb_m.best_iteration}  소요={timing['[1] e5-small + LGB']:.1f}초")

prob1 = lgb_m.predict(X_te, num_iteration=lgb_m.best_iteration)
best_all, best_f1fpr, best_f1t = scan_best(y_te, prob1)

print(f"\n  ┌─ [1] e5-small + LGB")
if best_all:
    print_result(full_metrics(y_te, prob1, best_all[0]), "★ 3조건 달성")
elif best_f1fpr:
    print_result(full_metrics(y_te, prob1, best_f1fpr[0]), "F1✅FPR✅ 최선")
print_result(full_metrics(y_te, prob1, best_f1t), "F1 최적")
print(f"  └{'─'*60}")

with open(ARTIFACTS_DIR / "small" / "detector_model.pkl", "wb") as f:
    pickle.dump(lgb_m, f)
print("  저장: artifacts/small/detector_model.pkl")


# ════════════════════════════════════════════════════════════
# STEP 4 | 모델 [2]  e5-small + XGBoost
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 65)
print("STEP 4 | 모델 [2]  e5-small + XGBoost")
print("=" * 65)

xgb_params = {
    "objective": "binary:logistic", "eval_metric": "logloss",
    "tree_method": "hist",
    "device": "cuda",         
    "scale_pos_weight": 1.0,   
    "max_depth": 7,
    "learning_rate": 0.03,
    "subsample": 0.8, "colsample_bytree": 0.7,
    "min_child_weight": 10,
    "gamma": 0.05,
    "reg_alpha": 0.05, "reg_lambda": 0.5,
    "seed": RANDOM_STATE, "verbosity": 0,
}
dm_tr = xgb.DMatrix(X_tr, label=y_tr)
dm_te = xgb.DMatrix(X_te, label=y_te)

t0 = time.time()
xgb_m = xgb.train(
    xgb_params, dm_tr,
    num_boost_round=2000,
    evals=[(dm_tr, "train"), (dm_te, "valid")],
    early_stopping_rounds=100, verbose_eval=200,
)
timing["[2] e5-small + XGB"] = time.time() - t0
print(f"\n  학습 완료  best_iter={xgb_m.best_iteration}  소요={timing['[2] e5-small + XGB']:.1f}초")

prob2 = xgb_m.predict(dm_te)
best_all, best_f1fpr, best_f1t = scan_best(y_te, prob2)

print(f"\n  ┌─ [2] e5-small + XGB")
if best_all:
    print_result(full_metrics(y_te, prob2, best_all[0]), "★ 3조건 달성")
elif best_f1fpr:
    print_result(full_metrics(y_te, prob2, best_f1fpr[0]), "F1✅FPR✅ 최선")
print_result(full_metrics(y_te, prob2, best_f1t), "F1 최적")
print(f"  └{'─'*60}")

xgb_m.save_model(str(ARTIFACTS_DIR / "small" / "detector_model_xgb_small.json"))
print("  저장: artifacts/small/detector_model_xgb_small.json")


# ════════════════════════════════════════════════════════════
# 최종 요약
# ════════════════════════════════════════════════════════════
TOTAL_ELAPSED = time.time() - TOTAL_START
timing["─ 전체 합계 ─"] = TOTAL_ELAPSED

W = 65
print("\n\n" + "=" * W)
print("  ★  e5-small 학습 완료 요약")
print("=" * W)
print(f"\n  {'모델':<26} {'AUC':>7}  {'F1최적':>7}  {'FPR':>7}  {'FNR':>7}  {'3조건'}")
print("  " + "─" * (W - 2))
for name, prob, y in [("[1] e5-small + LGB", prob1, y_te), ("[2] e5-small + XGB", prob2, y_te)]:
    auc = roc_auc_score(y, prob)
    _, _, f1t = scan_best(y, prob)
    m   = full_metrics(y, prob, f1t)
    achieved = any(
        full_metrics(y, prob, t/200)["f1"]  >= 0.85 and
        full_metrics(y, prob, t/200)["fpr"] <  0.10 and
        full_metrics(y, prob, t/200)["fnr"] <  0.10
        for t in range(1, 199)
    )
    ok = "✅✅✅" if achieved else "❌"
    print(f"  {name:<26} {auc:>7.4f}  {m['f1']*100:>6.1f}%  {m['fpr']*100:>6.1f}%  {m['fnr']*100:>6.1f}%  {ok}")

print("\n" + "=" * W)
print(f"  {'단계':<28} {'초':>8}  {'분':>8}")
print(f"  {'─'*28}  {'─'*8}  {'─'*8}")
for k, v in timing.items():
    if k.startswith("─"):
        print(f"  {'─'*28}  {'─'*8}  {'─'*8}")
    print(f"  {k:<28} {v:>8.1f}초  {v/60:>7.1f}분")
print("=" * W)
print(f"\n  학습 데이터: e5-small {'전체' if SAMPLE_SMALL is None else f'{SAMPLE_SMALL:,}'}행")
print(f"  저장 위치: {ARTIFACTS_DIR / 'small'}")
print("=" * W)
