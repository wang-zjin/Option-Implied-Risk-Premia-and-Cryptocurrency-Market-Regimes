#!/usr/bin/env python3
"""
S8_1：**ex-post logRV / realized variance**。

使用 ``function.log_rv_aligned_to_dates``：对 **过去 ``ttm`` 个交易日** 的日对数收益平方和，
再乘以 ``annualized_days()/ttm``，列名 ``log_rv_ann``（年化方差尺度，与历史 S8_0 文档一致）。

**默认日期集合**（**``--use-cluster-dates``，默认开启）**：
``Q_matrix_{ttm}`` 表头日期 ∩ **S7** ``common_dates_cluster.csv`` 中 **Cluster ∈ {0, 1}**（HV/LV）的日期，
且 **保留 Q_matrix 列顺序**。即：logRV **仅落在 S7 的 HV/LV 交易日上**，并仍要求该日出现在 **本 τ 的 Q_matrix** 表头中（与 **S10_0** 等与聚类合并的逻辑一致）。
**各 τ 行数是否相同**仍取决于各 `Q_matrix` 对聚类日的覆盖是否一致；若某日在 τ=27 的 Q 中存在、在 τ=9 不存在，则两 τ 的 logRV 行数仍会不同。

**``--no-use-cluster-dates``**：关闭聚类筛选，恢复旧行为（**仅 ``Q_matrix`` 全表头日期**）。

**输出**（默认 ``results/ttm_XX/log_RV/logRV_ttm{ttm}day.csv``，稳健性 ``results/results_robust/ttm_XX/log_RV/``）::

  列：``date``, ``log_rv_ann``

**先决**：**S6_1** ``Q_matrix_{ttm}day.csv``（或 ``…_d15…``）；现货 ``function.load_eth_daily``；默认还须 **S7** ``common_dates_cluster.csv``。

规划文件名亦写作 ``S8_1_logRV.py``；本仓库实现为 ``S8_1_logRV_eth.py``。

用法::

    python3 scripts/S8_1_logRV_eth.py
    python3 scripts/S8_1_logRV_eth.py --ttm 9 27 45 --use-d15
    python3 scripts/S8_1_logRV_eth.py --no-use-cluster-dates
    python3 scripts/S8_1_logRV_eth.py --robust --ttm 14 28 42
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Set

import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from function import (  # noqa: E402
    ETH_DAILY_CSV,
    ETH_LOG_RV_SUBDIR,
    ETH_Q_MATRIX_MON_STEP_SUBDIR,
    ETH_Q_MATRIX_OUT_DIR,
    PRIMARY_TTMS,
    ROBUSTNESS_TTMS,
    annualized_days,
    clustering_multivariate_run_dir,
    ensure_results_dir,
    load_eth_daily,
    log_rv_aligned_to_dates,
)


def _read_q_matrix_header_dates(q_matrix_path: Path) -> List[str]:
    hdr = pd.read_csv(q_matrix_path, nrows=0)
    cols = [str(c) for c in hdr.columns]
    if not cols:
        raise ValueError(f"empty header: {q_matrix_path}")
    first = cols[0].lower()
    if first in ("return", "m", "moneyness", "ret"):
        cols = cols[1:]
    return cols


def default_q_matrix_path(ttm: int, *, use_d15: bool) -> Path:
    base = ETH_Q_MATRIX_OUT_DIR / ETH_Q_MATRIX_MON_STEP_SUBDIR
    suffix = "_d15" if use_d15 else ""
    return base / f"Q_matrix_{ttm}day{suffix}.csv"


def _cluster_date_set(path: Path) -> Set[pd.Timestamp]:
    """S7：仅 HV(0) / LV(1) 交易日，规范到 normalize() 的 NaT-free 集合。"""
    df = pd.read_csv(path)
    col_d = next((c for c in df.columns if str(c).lower() == "date"), df.columns[0])
    col_c = next((c for c in df.columns if str(c).lower() == "cluster"), None)
    if col_c is None:
        raise ValueError(f"missing Cluster column: {path}")
    d = pd.to_datetime(df[col_d], errors="coerce").dt.normalize()
    c = pd.to_numeric(df[col_c], errors="coerce")
    ok = c.isin((0, 1)) & d.notna()
    return set(d.loc[ok].unique())


def _filter_header_dates_by_cluster(dates_s: List[str], cluster_set: Set[pd.Timestamp]) -> List[str]:
    """保留 Q_matrix 列顺序，仅留下聚类样本日。"""
    out: List[str] = []
    for s in dates_s:
        ts = pd.to_datetime(s, errors="coerce")
        if pd.isna(ts):
            continue
        if ts.normalize() in cluster_set:
            out.append(s)
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="S8_1: logRV aligned to Q_matrix calendar → results/ttm_*/log_RV/")
    p.add_argument(
        "--ttm",
        type=int,
        nargs="+",
        default=list(PRIMARY_TTMS),
        help="TTM days（default: 9 27 45；稳健性可换 14 28 42 并加 --robust）",
    )
    p.add_argument("--q-matrix", type=Path, default=None, help="Explicit Q_matrix CSV")
    p.add_argument("--use-d15", action="store_true", help="Use Q_matrix_*_d15.csv when --q-matrix unset")
    p.add_argument("--spot-csv", type=Path, default=None, help="ETH daily（default ETH_DAILY_CSV）")
    p.add_argument("--robust", action="store_true", help="Write under results/results_robust/ttm_XX/")
    p.add_argument(
        "--meta-json",
        action="store_true",
        help="Write s8_1_run_meta.json next to each CSV（ttm、use_d15、n_rows、annualized_days）",
    )
    p.add_argument(
        "--use-cluster-dates",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Intersect Q_matrix header dates with S7 HV/LV dates (default: true)",
    )
    p.add_argument(
        "--cluster-csv",
        type=Path,
        default=None,
        help="S7 common_dates_cluster.csv（默认 function.clustering_multivariate_run_dir）",
    )
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
    ann = annualized_days()

    cluster_path: Path | None = None
    cluster_set: Set[pd.Timestamp] | None = None
    if args.use_cluster_dates:
        cluster_path = args.cluster_csv or (clustering_multivariate_run_dir() / "common_dates_cluster.csv")
        if not cluster_path.is_file():
            raise SystemExit(f"--use-cluster-dates requires cluster CSV: missing {cluster_path}")
        cluster_set = _cluster_date_set(cluster_path)

    for ttm in args.ttm:
        q_path = args.q_matrix if args.q_matrix is not None else default_q_matrix_path(ttm, use_d15=args.use_d15)
        if not q_path.is_file():
            print(f"skip ttm={ttm}: missing Q_matrix {q_path}", file=sys.stderr)
            continue
        dates_s = _read_q_matrix_header_dates(q_path)
        n_q = len(dates_s)
        if args.use_cluster_dates and cluster_set is not None:
            dates_s = _filter_header_dates_by_cluster(dates_s, cluster_set)
        if not dates_s:
            print(
                f"skip ttm={ttm}: no dates after filter "
                f"(q_header_n={n_q}, use_cluster_dates={args.use_cluster_dates})",
                file=sys.stderr,
            )
            continue
        dates = pd.to_datetime(pd.Series(dates_s), errors="coerce").dropna()
        if dates.empty:
            print(f"skip ttm={ttm}: no parsable dates after filter {q_path}", file=sys.stderr)
            continue

        out = log_rv_aligned_to_dates(eth, dates, ttm)
        ttm_root = ensure_results_dir(ttm, robust=args.robust)
        out_dir = ttm_root / ETH_LOG_RV_SUBDIR
        out_dir.mkdir(parents=True, exist_ok=True)
        suffix = "_d15" if args.use_d15 else ""
        out_csv = out_dir / f"logRV_ttm{ttm}day{suffix}.csv"
        out.to_csv(out_csv, index=False)
        print(f"ttm={ttm} -> {out_csv} (n={len(out)})")

        if args.meta_json:
            meta = {
                "ttm": ttm,
                "use_d15": bool(args.use_d15),
                "use_cluster_dates": bool(args.use_cluster_dates),
                "cluster_csv": str(cluster_path.resolve()) if cluster_path is not None else None,
                "q_matrix": str(q_path.resolve()),
                "n_q_header_dates": int(n_q),
                "spot_csv": str(Path(spot_path).resolve()),
                "n_rows": int(len(out)),
                "annualized_days": float(ann),
                "column_log_rv_ann": "sum of squared daily log returns over prior ttm rows × annualized_days/ttm",
            }
            meta_path = out_dir / "s8_1_run_meta.json"
            meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
            print(f"  meta -> {meta_path}")

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
