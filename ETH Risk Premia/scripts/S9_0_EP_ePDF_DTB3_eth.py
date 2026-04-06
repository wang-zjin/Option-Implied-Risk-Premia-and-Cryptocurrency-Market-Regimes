#!/usr/bin/env python3
"""
S9_0：**EP（Equity Premium）** = **P density 一阶矩（年化）− DTB3（三月期 T-bill，年化小数）**。

对齐 BTC ``S6_2_RiskPremia_BP_report_*_Tbill_multivar_9_27_45.m``：

- :math:`\\hat\\mu_{\\mathbb P} = \\frac{365}{\\tau} \\int_{-1}^{1} x\\,\\hat p(x)\\,dx`（梯形积分，`Returns` 与 ``P_NB{n}`` 同列）。
- **Overall / HV / LV** 分别读 **S8_0** ``P_ePDF_OA|HV|LV_ttm{τ}day.xlsx`` 中同一 ``P_NB{n}``（默认 **NB12**）。
- **无风险**：**Overall** 下 DTB3 均值为 **HV 日 ∪ LV 日**（与 Matlab ``mean([IR_HV;IR_LV])`` 同构）；**HV/LV** 为各簇上 DTB3 均值。
  利率与 **``function.interest_rates_asof_on_calendar_dates``** 对齐：**每个聚类自然日** 用 **≤ 该日的最近 DTB3**（周末/假日 LOCF，与 ``tbill_annual_decimal_for_date`` 一致），**不再**对 ``load_ir_daily()`` 做 **inner**（避免丢掉仅含周末的聚类日）。

**输出**：``results/ttm_XX/EP/ePDF_DTB3/EP_report_ttm{τ}day.csv``  
行：``EP_hat``, ``mu_P``, ``mean_rf``, ``n_obs``（各列 ``mean_rf`` 所平均的 **聚类日历日条数**；含周末；若某日早于 DTB3 起点或日期无效则不计入）。

先决：**S8_0** ``P_density/ePDF/``；**S7** ``common_dates_cluster.csv``；**FRED** ``data/Interest_Rate/DTB3.csv``。

用法::

    python3 scripts/S9_0_EP_ePDF_DTB3_eth.py
    python3 scripts/S9_0_EP_ePDF_DTB3_eth.py --ttm 9 27 45 --p-nb 12
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from function import (  # noqa: E402
    ETH_EP_REPORT_SUBDIR,
    ETH_P_DENSITY_EXCEL_SUBDIR,
    PRIMARY_TTMS,
    annualized_days,
    clustering_multivariate_run_dir,
    ensure_results_dir,
    interest_rates_asof_on_calendar_dates,
    load_ir_daily,
)


def load_common_dates_cluster(path: Path) -> pd.DataFrame:
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


def mu_p_ann_from_epdf_xlsx(path: Path, p_nb_col: str, ttm: int) -> float:
    df = pd.read_excel(path, engine="openpyxl")
    if "Returns" not in df.columns:
        raise ValueError(f"Returns column missing: {path}")
    if p_nb_col not in df.columns:
        raise ValueError(f"{p_nb_col} missing in {path}")
    ret = df["Returns"].to_numpy(dtype=float)
    p = df[p_nb_col].to_numpy(dtype=float)
    p = np.maximum(p, 0.0)
    return float(np.trapz(ret * p, ret) * (annualized_days() / float(ttm)))


def mean_rf_on_dates(ir: pd.DataFrame, dates: pd.Series) -> float:
    m = interest_rates_asof_on_calendar_dates(dates, ir_daily=ir)
    v = pd.to_numeric(m["interest_rate"], errors="coerce")
    v = v[np.isfinite(v.to_numpy())]
    if v.empty:
        return float("nan")
    return float(v.mean())


def n_rf_obs_on_dates(ir: pd.DataFrame, dates: pd.Series) -> int:
    """``mean_rf`` 所用样本量：LOCF 后有有效利率的聚类日历行数。"""
    m = interest_rates_asof_on_calendar_dates(dates, ir_daily=ir)
    v = pd.to_numeric(m["interest_rate"], errors="coerce")
    return int(np.isfinite(v.to_numpy()).sum())


def main() -> int:
    p = argparse.ArgumentParser(description="S9_0: EP = mu_P(ePDF) - DTB3 → results/ttm_*/EP/ePDF_DTB3/")
    p.add_argument("--ttm", type=int, nargs="+", default=list(PRIMARY_TTMS))
    p.add_argument(
        "--cluster-csv",
        type=Path,
        default=None,
        help="S7 common_dates_cluster.csv",
    )
    p.add_argument("--robust", action="store_true")
    p.add_argument("--p-nb", type=int, default=12, help="P_NB column (BTC 默认常取 12)")
    p.add_argument(
        "--p-density-dir",
        type=Path,
        default=None,
        help="Override：含 P_ePDF_*_ttm{τ}day.xlsx 的目录（默认 results/ttm_XX/P_density/ePDF/）",
    )
    args = p.parse_args()

    cluster_path = args.cluster_csv or (clustering_multivariate_run_dir() / "common_dates_cluster.csv")
    if not cluster_path.is_file():
        raise SystemExit(f"missing {cluster_path}")
    cluster_df = load_common_dates_cluster(cluster_path)
    ir = load_ir_daily()

    hv_dates = cluster_df.loc[cluster_df["cluster"] == 0, "date"]
    lv_dates = cluster_df.loc[cluster_df["cluster"] == 1, "date"]
    oa_dates = pd.concat([hv_dates, lv_dates], ignore_index=True)

    pcol = f"P_NB{args.p_nb}"

    for ttm in args.ttm:
        ttm_root = ensure_results_dir(ttm, robust=args.robust)
        pdir = args.p_density_dir or (ttm_root / ETH_P_DENSITY_EXCEL_SUBDIR)
        paths = {
            "OA": pdir / f"P_ePDF_OA_ttm{ttm}day.xlsx",
            "HV": pdir / f"P_ePDF_HV_ttm{ttm}day.xlsx",
            "LV": pdir / f"P_ePDF_LV_ttm{ttm}day.xlsx",
        }
        for k, path in paths.items():
            if not path.is_file():
                print(f"skip ttm={ttm}: missing {path}", file=sys.stderr)
                break
        else:
            mu_p: Dict[str, float] = {}
            mu_p["Overall"] = mu_p_ann_from_epdf_xlsx(paths["OA"], pcol, ttm)
            mu_p["HV"] = mu_p_ann_from_epdf_xlsx(paths["HV"], pcol, ttm)
            mu_p["LV"] = mu_p_ann_from_epdf_xlsx(paths["LV"], pcol, ttm)

            rf_oa = mean_rf_on_dates(ir, oa_dates)
            rf_hv = mean_rf_on_dates(ir, hv_dates)
            rf_lv = mean_rf_on_dates(ir, lv_dates)

            ep_oa = mu_p["Overall"] - rf_oa
            ep_hv = mu_p["HV"] - rf_hv
            ep_lv = mu_p["LV"] - rf_lv

            n_oa = n_rf_obs_on_dates(ir, oa_dates)
            n_hv = n_rf_obs_on_dates(ir, hv_dates)
            n_lv = n_rf_obs_on_dates(ir, lv_dates)

            out_dir = ttm_root / ETH_EP_REPORT_SUBDIR
            out_dir.mkdir(parents=True, exist_ok=True)
            out_csv = out_dir / f"EP_report_ttm{ttm}day.csv"
            tbl = pd.DataFrame(
                {
                    "Overall": [ep_oa, mu_p["Overall"], rf_oa, float(n_oa)],
                    "HV": [ep_hv, mu_p["HV"], rf_hv, float(n_hv)],
                    "LV": [ep_lv, mu_p["LV"], rf_lv, float(n_lv)],
                },
                index=["EP_hat", "mu_P", "mean_rf", "n_obs"],
            )
            tbl.to_csv(out_csv, encoding="utf-8")
            print(f"ttm={ttm} {pcol} -> {out_csv}")
            print(tbl.to_string())

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
