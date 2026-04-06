#!/usr/bin/env python3
"""
S8_2：**Corsi (2009) 型 HAR-RV**，回归元为日/周/月异质成分；**因变量**按本项目的 **ttm**
与 **S8_1** 同尺度：**未来 ``ttm`` 个交易日**上的年化实现方差（与 ``log_rv_ann`` 公式相同，但窗口向前）。

**文献**：Corsi (2009) 基准式预测的是 **下一交易日** 的日度 RV；**1 / 5 / 22** 指 **回归元**
（日、周、月已实现波动成分），不是预测步长。此处为与期权到期/``Q_matrix`` 的 **τ 日**一致，
将因变量取为 **自 ``t+1`` 起共 ``ttm`` 日** 的对数收益平方和 × ``annualized_days()/ttm``，
使 ``har_rv_pred`` 与 **S8_1** 的 ``log_rv_ann`` 属同一对象（一前一后）。

**回归元（与 Corsi 一致）**：``rv_d = annualized_days() × (Δ log P)^2``；
``RV^{(w)}`` = 过去 5 日 ``rv_d`` 的均值；``RV^{(m)}`` = 过去 22 日 ``rv_d`` 的均值。

**输入**：**S8_1** ``log_RV/logRV_ttm{ttm}day*.csv``（**须先跑 S8_1**）；每个 ``ttm`` 单独估计（因变量随 ``ttm`` 变）。

**输出**（``results/ttm_XX/HAR-RV/``）::

  列：``date``, ``log_rv_ann``（若输入含）, ``rv_d``, ``rv_w``, ``rv_m``, ``rv_fwd_ttm``, ``har_rv_pred``

``rv_fwd_ttm``：样本内 **已实现** 的未来 ``ttm`` 日年化 RV（末段 ``ttm`` 个交易日因未来未知而为空）；
``har_rv_pred``：HAR 对同一段的 **预测**。二者与 **S8_1** 的 ``log_rv_ann`` 同尺度。

**估计**：默认 **全样本 OLS**；可用 ``--recursive-ols`` 做扩张窗（无全样本 lookahead）。
规划文件名 ``scripts/S8_2_HAR_RV_eth.py``。

用法::

    python3 scripts/S8_2_HAR_RV_eth.py
    python3 scripts/S8_2_HAR_RV_eth.py --ttm 9 27 45 --use-d15
    python3 scripts/S8_2_HAR_RV_eth.py --recursive-ols --min-train 500
    python3 scripts/S8_2_HAR_RV_eth.py --robust --ttm 14 28 42
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from function import (  # noqa: E402
    ETH_DAILY_CSV,
    ETH_HAR_RV_SUBDIR,
    ETH_LOG_RV_SUBDIR,
    annualized_days,
    ensure_results_dir,
    load_eth_daily,
    PRIMARY_TTMS,
    ROBUSTNESS_TTMS,
)


def _forward_ttm_log_rv_ann(log_r: pd.Series, ttm: int, ann: float) -> pd.Series:
    """
    与 ``function.log_rv_aligned_to_dates`` 同尺度，但窗口 **向前**：
    在索引 ``i`` 处为 ``(ann/ttm) * sum_{k=1}^{ttm} log_r[i+k]^2``（下一 ``ttm`` 个交易日）。
    """
    lr = log_r.to_numpy(dtype=float)
    n = len(lr)
    out = np.full(n, np.nan, dtype=float)
    for i in range(n):
        if i + ttm >= n:
            break
        chunk = lr[i + 1 : i + ttm + 1]
        if chunk.shape[0] == ttm and np.isfinite(chunk).all():
            out[i] = (ann / float(ttm)) * float(np.sum(chunk**2))
    return pd.Series(out, index=log_r.index)


def _build_corsi_har_frame(eth: pd.DataFrame, ttm: int) -> pd.DataFrame:
    """全交易日：Corsi 回归元 + 因变量 = 未来 ``ttm`` 日 ``log_rv_ann`` 同定义。"""
    ann = annualized_days()
    df = eth.sort_values("date").reset_index(drop=True)
    log_r = np.log(df["price"] / df["price"].shift(1))
    rv_d = ann * (log_r**2)
    rv_w = rv_d.rolling(window=5, min_periods=5).mean()
    rv_m = rv_d.rolling(window=22, min_periods=22).mean()
    rv_fwd = _forward_ttm_log_rv_ann(log_r, ttm, ann)
    out = pd.DataFrame(
        {
            "date": pd.to_datetime(df["date"], errors="coerce").dt.normalize(),
            "rv_d": rv_d,
            "rv_w": rv_w,
            "rv_m": rv_m,
            "rv_fwd_ttm": rv_fwd,
        }
    )
    return out


def _ols_beta(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    return np.linalg.lstsq(X, y, rcond=None)[0]


def _har_predict_full_sample(har: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, float]:
    """全样本 OLS：返回 (beta(4,), pred[len], r2_in_sample)。"""
    cols_ok = har[["rv_d", "rv_w", "rv_m", "rv_fwd_ttm"]].notna().all(axis=1)
    X_fit = np.column_stack(
        (
            np.ones(int(cols_ok.sum())),
            har.loc[cols_ok, "rv_d"].to_numpy(),
            har.loc[cols_ok, "rv_w"].to_numpy(),
            har.loc[cols_ok, "rv_m"].to_numpy(),
        )
    )
    y_fit = har.loc[cols_ok, "rv_fwd_ttm"].to_numpy(dtype=float)
    beta = _ols_beta(X_fit, y_fit)
    resid = y_fit - X_fit @ beta
    sst = np.var(y_fit, ddof=1) * (len(y_fit) - 1)
    sse = float(np.sum(resid**2))
    r2 = float(1.0 - sse / sst) if sst > 0 else float("nan")

    pred = np.full(len(har), np.nan, dtype=float)
    cols_x = har[["rv_d", "rv_w", "rv_m"]].notna().all(axis=1)
    if cols_x.any():
        X_all = np.column_stack(
            (
                np.ones(int(cols_x.sum())),
                har.loc[cols_x, "rv_d"].to_numpy(),
                har.loc[cols_x, "rv_w"].to_numpy(),
                har.loc[cols_x, "rv_m"].to_numpy(),
            )
        )
        pred[np.where(cols_x.values)[0]] = X_all @ beta
    return beta, pred, r2


def _har_predict_recursive(har: pd.DataFrame, min_train: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    对每个时点 i：仅用 j < i 且回归元、因变量完整的观测估计 β，再用当日 X_i 预测 forward RV。
    返回 (pred[len], n_train_used[len])。
    """
    n = len(har)
    pred = np.full(n, np.nan, dtype=float)
    n_used = np.full(n, -1, dtype=int)
    for i in range(n):
        if i == 0:
            continue
        train = har.iloc[:i]
        ok = train[["rv_d", "rv_w", "rv_m", "rv_fwd_ttm"]].notna().all(axis=1)
        k = int(ok.sum())
        if k < min_train:
            continue
        tsub = train.loc[ok]
        X = np.column_stack(
            (
                np.ones(k),
                tsub["rv_d"].to_numpy(),
                tsub["rv_w"].to_numpy(),
                tsub["rv_m"].to_numpy(),
            )
        )
        y = tsub["rv_fwd_ttm"].to_numpy(dtype=float)
        beta = _ols_beta(X, y)
        row = har.iloc[i]
        if pd.isna(row["rv_d"]) or pd.isna(row["rv_w"]) or pd.isna(row["rv_m"]):
            continue
        xi = np.array([1.0, float(row["rv_d"]), float(row["rv_w"]), float(row["rv_m"])])
        pred[i] = float(xi @ beta)
        n_used[i] = k
    return pred, n_used


def main() -> int:
    p = argparse.ArgumentParser(description="S8_2: Corsi HAR-RV → results/ttm_*/HAR-RV/")
    p.add_argument("--ttm", type=int, nargs="+", default=list(PRIMARY_TTMS))
    p.add_argument(
        "--logrv-csv",
        type=Path,
        default=None,
        help="Explicit S8_1 logRV CSV（默认 ttm_root/log_RV/logRV_ttm{ttm}day*.csv）",
    )
    p.add_argument("--use-d15", action="store_true")
    p.add_argument("--spot-csv", type=Path, default=None)
    p.add_argument("--robust", action="store_true")
    p.add_argument(
        "--recursive-ols",
        action="store_true",
        help="逐日扩张窗 OLS（无全样本 lookahead；首日需 --min-train 条完整历史）",
    )
    p.add_argument("--min-train", type=int, default=500, help="--recursive-ols 时最少训练行数")
    p.add_argument("--meta-json", action="store_true", help="写入 s8_2_run_meta.json")
    args = p.parse_args()

    if args.robust:
        bad = [t for t in args.ttm if t not in ROBUSTNESS_TTMS and t not in PRIMARY_TTMS]
        if bad:
            print(
                f"warning: --robust with non-standard ttms {bad}（规划稳健性为 {list(ROBUSTNESS_TTMS)}）",
                file=sys.stderr,
            )

    spot_path = args.spot_csv or ETH_DAILY_CSV
    eth = load_eth_daily(spot_path)

    for ttm in args.ttm:
        ttm_root = ensure_results_dir(ttm, robust=args.robust)
        suffix = "_d15" if args.use_d15 else ""
        if args.logrv_csv is not None:
            logrv_path = args.logrv_csv
        else:
            logrv_path = ttm_root / ETH_LOG_RV_SUBDIR / f"logRV_ttm{ttm}day{suffix}.csv"
        if not logrv_path.is_file():
            print(f"skip ttm={ttm}: missing S8_1 logRV {logrv_path}", file=sys.stderr)
            continue

        har = _build_corsi_har_frame(eth, ttm)
        full_beta: np.ndarray | None = None
        full_r2: float | None = None
        if args.recursive_ols:
            pred_all, _n_tr = _har_predict_recursive(har, min_train=int(args.min_train))
            har = har.copy()
            har["har_rv_pred"] = pred_all
        else:
            beta, pred_all, r2 = _har_predict_full_sample(har)
            har = har.copy()
            har["har_rv_pred"] = pred_all
            full_beta, full_r2 = beta, r2

        logrv = pd.read_csv(logrv_path)
        col_d = next((c for c in logrv.columns if str(c).lower() == "date"), logrv.columns[0])
        base = logrv.copy()
        base["date"] = pd.to_datetime(base[col_d], errors="coerce").dt.normalize()
        base = base.dropna(subset=["date"])
        merged = base.merge(har, on="date", how="left")

        out_cols = ["date", "log_rv_ann", "rv_d", "rv_w", "rv_m", "rv_fwd_ttm", "har_rv_pred"]
        out = merged[[c for c in out_cols if c in merged.columns]].copy()

        out_dir = ttm_root / ETH_HAR_RV_SUBDIR
        out_dir.mkdir(parents=True, exist_ok=True)
        out_csv = out_dir / f"HAR_RV_ttm{ttm}day{suffix}.csv"
        out.to_csv(out_csv, index=False)
        print(f"ttm={ttm} -> {out_csv} (n={len(out)})")

        if args.meta_json:
            meta = {
                "ttm": ttm,
                "use_d15": bool(args.use_d15),
                "logrv_csv": str(logrv_path.resolve()),
                "spot_csv": str(Path(spot_path).resolve()),
                "recursive_ols": bool(args.recursive_ols),
                "min_train": int(args.min_train) if args.recursive_ols else None,
                "corsi_note": "Corsi (2009) baseline forecasts 1-day-ahead daily RV; regressors use 1/5/22-day components. Here y = forward ttm-day logRV (same formula as S8_1).",
                "har_spec": "rv_d=ann*logret^2; rv_w=mean(rv_d,5); rv_m=mean(rv_d,22); y=(ann/ttm)*sum_{k=1}^{ttm} logret_{t+k}^2",
                "annualized_days": float(annualized_days()),
                "n_rows": int(len(out)),
            }
            if not args.recursive_ols and full_beta is not None and full_r2 is not None:
                meta["ols_beta"] = [float(x) for x in full_beta]
                meta["ols_r2_in_sample_full_eth"] = float(full_r2)

            meta_path = out_dir / "s8_2_run_meta.json"
            meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
            print(f"  meta -> {meta_path}")

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
