#!/usr/bin/env python3
"""
S10_0：**VRP** 与 **ETH-VIX × S8_1 logRV** 对齐 BTC ``S6_2_RiskPremia_VRP_report_Qdensity_VIX_logRV_multivar_9_27_45.m`` 中 **VIX–logRV** 一支。

**默认 VRP 定义**（与表里 **BVIX² − RV** 量纲一致）：``implied_var = (EMA/100)²``，其中 **EMA** 为 ``eth_vix_EWA_{τ}.csv`` 中 VIX 指数（**百分数**，与 ``S6_3`` 一致），``log_rv_ann`` 为 **年化 realized variance**（``function.log_rv_aligned_to_dates``）。  
``VRP = implied_var - log_rv_ann``。

``--vrp-linear``：**``VRP = EMA - log_rv_ann``**（量纲混合，仅当明确需要字面「VIX − logRV」时使用）。

按 **S7** 标签分列 **Overall / HV / LV**，报告各列 **VRP、σ²_Q（隐含方差）、σ²_P（logRV）** 的样本均值及 **n**；可选 **ANOVA**（与 Matlab ``anova1`` 同构的两组：簇内 vs 全样本拼接）。

**输出**  
- ``results/ttm_XX/VRP/VIX_logRV/VRP_report_ttm{τ}day.csv``：汇总表  
- ``results/ttm_XX/VRP/VIX_logRV/VRP_panel_ttm{τ}day.csv``：日度合并面板（date, EMA, implied_var, log_rv_ann, VRP, cluster）

先决：**S6_3** ``results/ETH_VIX/eth_vix_EWA_{τ}.csv``；**S8_1** ``log_RV/logRV_ttm{τ}day.csv``；**S7** ``common_dates_cluster.csv``。

用法::

    python3 scripts/S10_0_VRP_VIX_logRV_eth.py
    python3 scripts/S10_0_VRP_VIX_logRV_eth.py --ttm 27 --anova
    python3 scripts/S10_0_VRP_VIX_logRV_eth.py --vrp-linear
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from function import (  # noqa: E402
    ETH_LOG_RV_SUBDIR,
    ETH_VIX_RESULTS_DIR,
    ETH_VRP_REPORT_SUBDIR,
    PRIMARY_TTMS,
    clustering_multivariate_run_dir,
    ensure_results_dir,
)


def load_cluster(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    col_d = next((c for c in df.columns if str(c).lower() == "date"), df.columns[0])
    col_c = next((c for c in df.columns if str(c).lower() == "cluster"), None)
    if col_c is None:
        raise ValueError(f"missing Cluster: {path}")
    out = pd.DataFrame(
        {
            "date": pd.to_datetime(df[col_d], errors="coerce").dt.normalize(),
            "cluster": pd.to_numeric(df[col_c], errors="coerce").astype("Int64"),
        }
    )
    out = out.dropna(subset=["date", "cluster"])
    return out[out["cluster"].isin((0, 1))].reset_index(drop=True)


def load_eth_vix_ewa(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    col_d = next((c for c in df.columns if str(c).lower() == "date"), df.columns[0])
    df = df.rename(columns={col_d: "Date"})
    df["date"] = pd.to_datetime(df["Date"].astype(str), format="%Y%m%d", errors="coerce").dt.normalize()
    if "EMA" not in df.columns:
        raise ValueError(f"EMA column missing: {path}")
    return df[["date", "EMA"]].dropna(subset=["date"]).sort_values("date")


def load_logrv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    col_d = next((c for c in df.columns if str(c).lower() == "date"), "date")
    df["date"] = pd.to_datetime(df[col_d], errors="coerce").dt.normalize()
    col_rv = next((c for c in df.columns if "log_rv" in str(c).lower() or c == "log_rv_ann"), None)
    if col_rv is None:
        raise ValueError(f"log_rv column missing: {path}")
    return df[["date", col_rv]].rename(columns={col_rv: "log_rv_ann"}).dropna(subset=["date"])


def _anova_p_two_groups(a: np.ndarray, b: np.ndarray) -> float:
    """One-way ANOVA F-test p-value for two independent samples (``scipy``)."""
    from scipy import stats

    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]
    if a.size < 2 or b.size < 2:
        return float("nan")
    return float(stats.f_oneway(a, b).pvalue)


def main() -> int:
    p = argparse.ArgumentParser(description="S10_0: VRP (VIX EWA vs logRV) → results/ttm_*/VRP/VIX_logRV/")
    p.add_argument("--ttm", type=int, nargs="+", default=list(PRIMARY_TTMS))
    p.add_argument("--robust", action="store_true")
    p.add_argument(
        "--cluster-csv",
        type=Path,
        default=None,
    )
    p.add_argument(
        "--vix-csv",
        type=Path,
        default=None,
        help="Default: results/ETH_VIX/eth_vix_EWA_{ttm}.csv",
    )
    p.add_argument(
        "--logrv-csv",
        type=Path,
        default=None,
        help="Default: results/ttm_XX/log_RV/logRV_ttm{ttm}day.csv",
    )
    p.add_argument(
        "--vrp-linear",
        action="store_true",
        help="VRP = EMA - log_rv_ann instead of (EMA/100)^2 - log_rv_ann",
    )
    p.add_argument(
        "--anova",
        action="store_true",
        help="Append ANOVA p-value rows (cluster subsample vs full pooled sample)",
    )
    args = p.parse_args()

    cluster_path = args.cluster_csv or (clustering_multivariate_run_dir() / "common_dates_cluster.csv")
    if not cluster_path.is_file():
        raise SystemExit(f"missing {cluster_path}")
    cl = load_cluster(cluster_path)

    for ttm in args.ttm:
        ttm_root = ensure_results_dir(ttm, robust=args.robust)
        vix_path = args.vix_csv or (ETH_VIX_RESULTS_DIR / f"eth_vix_EWA_{ttm}.csv")
        logrv_path = args.logrv_csv or (ttm_root / ETH_LOG_RV_SUBDIR / f"logRV_ttm{ttm}day.csv")
        if not vix_path.is_file():
            print(f"skip ttm={ttm}: missing VIX {vix_path}", file=sys.stderr)
            continue
        if not logrv_path.is_file():
            print(f"skip ttm={ttm}: missing logRV {logrv_path}", file=sys.stderr)
            continue

        vix = load_eth_vix_ewa(vix_path)
        rv = load_logrv(logrv_path)
        panel = vix.merge(rv, on="date", how="inner").merge(cl, on="date", how="inner")
        if panel.empty:
            print(f"skip ttm={ttm}: empty merge VIX∩logRV∩cluster", file=sys.stderr)
            continue

        if args.vrp_linear:
            panel["implied_var"] = panel["EMA"]
            panel["VRP"] = panel["EMA"] - panel["log_rv_ann"]
        else:
            panel["implied_var"] = (panel["EMA"] / 100.0) ** 2
            panel["VRP"] = panel["implied_var"] - panel["log_rv_ann"]

        out_dir = ttm_root / ETH_VRP_REPORT_SUBDIR
        out_dir.mkdir(parents=True, exist_ok=True)
        panel_out = out_dir / f"VRP_panel_ttm{ttm}day.csv"
        panel.to_csv(panel_out, index=False)

        def col_stats(mask: pd.Series) -> Tuple[float, float, float, int]:
            sub = panel.loc[mask]
            n = int(len(sub))
            if n == 0:
                return (float("nan"), float("nan"), float("nan"), 0)
            return (
                float(sub["VRP"].mean()),
                float(sub["implied_var"].mean()),
                float(sub["log_rv_ann"].mean()),
                n,
            )

        overall_m = panel["cluster"].isin((0, 1))
        hv_m = panel["cluster"] == 0
        lv_m = panel["cluster"] == 1

        vrp_o, q_o, p_o, n_o = col_stats(overall_m)
        vrp_h, q_h, p_h, n_h = col_stats(hv_m)
        vrp_l, q_l, p_l, n_l = col_stats(lv_m)

        rows = {
            "VRP_mean": [vrp_o, vrp_h, vrp_l],
            "sigma2_Q_mean": [q_o, q_h, q_l],
            "sigma2_P_mean": [p_o, p_h, p_l],
            "n_obs": [n_o, n_h, n_l],
        }
        if args.anova:
            over_vrp = panel.loc[overall_m, "VRP"].to_numpy()
            hv_vrp = panel.loc[hv_m, "VRP"].to_numpy()
            lv_vrp = panel.loc[lv_m, "VRP"].to_numpy()
            p_hv = _anova_p_two_groups(hv_vrp, over_vrp)
            p_lv = _anova_p_two_groups(lv_vrp, over_vrp)
            rows["anova_p_vs_overall"] = [float("nan"), p_hv, p_lv]

        report = pd.DataFrame(rows, index=["Overall", "HV", "LV"]).T
        rep_csv = out_dir / f"VRP_report_ttm{ttm}day.csv"
        report.to_csv(rep_csv, encoding="utf-8")
        print(f"ttm={ttm} vrp_linear={args.vrp_linear} -> {rep_csv}")
        print(report.to_string())
        print(f"  panel -> {panel_out} (n={len(panel)})")

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
