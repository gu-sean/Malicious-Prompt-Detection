#   [3] e5-large + LightGBM
#   [4] e5-large + XGBoost
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

LARGE_MODEL  = "intfloat/multilingual-e5-large"
SAMPLE_LARGE = None    
EMBED_BATCH  = 64       # GPU에서 배치 크기 증가 (12GB VRAM)
TEST_SIZE    = 0.2
RANDOM_STATE = 42

ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
(ARTIFACTS_DIR / "large").mkdir(parents=True, exist_ok=True)

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
# STEP 2 | e5-large 임베딩 (캐시 있으면 재사용)
# ════════════════════════════════════════════════════════════
_sample_label = "전체행" if SAMPLE_LARGE is None else f"{SAMPLE_LARGE:,}행"
print("\n" + "=" * 65)
print(f"STEP 2 | e5-large 임베딩  (샘플={_sample_label})")
print("=" * 65)

_emb_cache  = ARTIFACTS_DIR / "large" / "embeddings_large.npy"
_lbl_cache  = ARTIFACTS_DIR / "large" / "labels_large.npy"
_expected_n = len(df_all) if SAMPLE_LARGE is None else SAMPLE_LARGE
_cache_ok   = (
    _emb_cache.exists() and _lbl_cache.exists() and
    len(np.load(_lbl_cache)) == _expected_n
)

if _cache_ok:
    print("  캐시 발견 → 재사용 (임베딩 생략)")
    emb_l    = np.load(_emb_cache)
    labels_l = np.load(_lbl_cache)
    timing["e5-large 임베딩"] = 0.0
    print(f"  로드 완료  shape={emb_l.shape}")
else:
    n_sample_est  = len(df_all) if SAMPLE_LARGE is None else SAMPLE_LARGE
    n_batches_est = (n_sample_est + EMBED_BATCH - 1) // EMBED_BATCH
    est_min = n_batches_est * 30 / 60
    print(f"  예상 임베딩 시간: 약 {est_min:.0f}분 ({n_batches_est}배치 × 30초)")

    df_l     = sample_data(df_all, SAMPLE_LARGE)
    labels_l = df_l["label"].values
    texts    = ["query: " + t for t in df_l["text"].tolist()]

    embedder = SentenceTransformer(LARGE_MODEL)
    batches  = [texts[i:i+EMBED_BATCH] for i in range(0, len(texts), EMBED_BATCH)]
    print(f"  {len(texts):,}개 / {len(batches)}배치 / 배치크기={EMBED_BATCH}")

    t0 = time.time()
    parts = []
    for batch in tqdm(batches, desc="  임베딩(e5-large)", unit="batch", ncols=70):
        parts.append(embedder.encode(batch, show_progress_bar=False))
    emb_l = np.vstack(parts)
    timing["e5-large 임베딩"] = time.time() - t0

    np.save(_emb_cache, emb_l)
    np.save(_lbl_cache, labels_l)
    print(f"  임베딩 완료  shape={emb_l.shape}  소요={timing['e5-large 임베딩']:.1f}초 ({timing['e5-large 임베딩']/60:.1f}분)")

X_tr, X_te, y_tr, y_te = train_test_split(
    emb_l, labels_l, test_size=TEST_SIZE, stratify=labels_l, random_state=RANDOM_STATE
)
print(f"  Train: {len(X_tr):,}  Test: {len(X_te):,}")


# ════════════════════════════════════════════════════════════
# STEP 3 | 모델 [3]  e5-large + LightGBM
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 65)
print("STEP 3 | 모델 [3]  e5-large + LightGBM")
print("=" * 65)

lgb_params = {
    "objective": "binary", "metric": "binary_logloss",
    "boosting_type": "gbdt",
    "learning_rate": 0.02,
    "num_leaves": 63, "max_depth": 6,
    "min_child_samples": 5,
    "feature_fraction": 0.5,
    "bagging_fraction": 0.8, "bagging_freq": 5,
    "reg_alpha": 0.1, "reg_lambda": 0.5,
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
timing["[3] e5-large + LGB"] = time.time() - t0
print(f"\n  학습 완료  best_iter={lgb_m.best_iteration}  소요={timing['[3] e5-large + LGB']:.1f}초")

prob3 = lgb_m.predict(X_te, num_iteration=lgb_m.best_iteration)
best_all, best_f1fpr, best_f1t = scan_best(y_te, prob3)

print(f"\n  ┌─ [3] e5-large + LGB")
if best_all:
    print_result(full_metrics(y_te, prob3, best_all[0]), "★ 3조건 달성")
elif best_f1fpr:
    print_result(full_metrics(y_te, prob3, best_f1fpr[0]), "F1✅FPR✅ 최선")
print_result(full_metrics(y_te, prob3, best_f1t), "F1 최적")
print(f"  └{'─'*60}")

with open(ARTIFACTS_DIR / "large" / "detector_model_large.pkl", "wb") as f:
    pickle.dump(lgb_m, f)
print("  저장: artifacts/large/detector_model_large.pkl")


# ════════════════════════════════════════════════════════════
# STEP 4 | 모델 [4]  e5-large + XGBoost
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 65)
print("STEP 4 | 모델 [4]  e5-large + XGBoost")
print("=" * 65)

xgb_params = {
    "objective": "binary:logistic", "eval_metric": "logloss",
    "tree_method": "hist",
    "scale_pos_weight": 1.0,  
    "max_depth": 6,
    "learning_rate": 0.02,
    "subsample": 0.8, "colsample_bytree": 0.5,
    "min_child_weight": 5,
    "gamma": 0.1,
    "reg_alpha": 0.1, "reg_lambda": 0.5,
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
timing["[4] e5-large + XGB"] = time.time() - t0
print(f"\n  학습 완료  best_iter={xgb_m.best_iteration}  소요={timing['[4] e5-large + XGB']:.1f}초")

prob4 = xgb_m.predict(dm_te)
best_all, best_f1fpr, best_f1t = scan_best(y_te, prob4)

print(f"\n  ┌─ [4] e5-large + XGB")
if best_all:
    print_result(full_metrics(y_te, prob4, best_all[0]), "★ 3조건 달성")
elif best_f1fpr:
    print_result(full_metrics(y_te, prob4, best_f1fpr[0]), "F1✅FPR✅ 최선")
print_result(full_metrics(y_te, prob4, best_f1t), "F1 최적")
print(f"  └{'─'*60}")

xgb_m.save_model(str(ARTIFACTS_DIR / "large" / "detector_model_xgb_large.json"))
print("  저장: artifacts/large/detector_model_xgb_large.json")


# ════════════════════════════════════════════════════════════
# 최종 요약
# ════════════════════════════════════════════════════════════
TOTAL_ELAPSED = time.time() - TOTAL_START
timing["─ 전체 합계 ─"] = TOTAL_ELAPSED

W = 65
print("\n\n" + "=" * W)
print("  ★  e5-large 학습 완료 요약")
print("=" * W)
print(f"\n  {'모델':<26} {'AUC':>7}  {'F1최적':>7}  {'FPR':>7}  {'FNR':>7}  {'3조건'}")
print("  " + "─" * (W - 2))
for name, prob, y in [("[3] e5-large + LGB", prob3, y_te), ("[4] e5-large + XGB", prob4, y_te)]:
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
print(f"\n  학습 데이터: e5-large {_sample_label}")
print(f"  저장 위치: {ARTIFACTS_DIR / 'large'}")
print("=" * W)
