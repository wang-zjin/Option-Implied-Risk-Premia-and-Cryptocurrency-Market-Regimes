#!/usr/bin/env python3
"""
**``scripts/S8_0_prepare_Pdensity.py``** — 规划 **§1.3.1** **S8_0**（**ePDF**；**不** 计算 logRV，见 ``function.log_rv_aligned_to_dates`` / 将来 **S8_1**）。

**物理测度 P** — 与 ``Q_matrix`` 同轴网格 **``m ∈ [-1,1]``、步长 0.01**（项目内与 **K/S−1** 一致）
上的 **经验 P 密度**，并按 **BTC** 多变量聚类写法给出 **OA / HV / LV** 三套密度。

**BTC 只读参考**（工程路径勿改）::

  ``SVI_independent_tau/S6_1_RiskPremia_BP_write_QP_OA_NB_xlsx_multivar_9_27_45.m``（OA）  
  ``…_QP_c0_NB…``（HV：Q 对 cluster0；P 仍用全样本重叠简单收益 + 方差重标定）  
  ``…_QP_c1_NB…``（LV）

**重叠简单收益**（同 ``Simple_return_fullsample_overlapping``）::

  ``(S_{t+τ} - S_t) / S_t``，在 **日频升序、一行一日** 的价格面板上按行索引 ``t`` 与 ``t+τ`` 计算。

**OA / HV / LV 的 P**

- **默认（``--hv-lv-via-subset`` 未开）**：对齐 BTC ``…_c0_NB…`` / ``…_c1_NB…`` 与
  ``rescale_shift_return_exp(..., 0, 0, var_full, var_cluster, τ)`` 在均值为 0 时的标量分支：**HV/LV**
  仍使用 **全历史**重叠简单收益作样本，但整体乘以 ``sqrt(var_k / var_full)``。**方差定义**（与仅「全历史 pooled」区分）：
  ``var_full`` = 仅 **起点日 ∈ S7 HV∪LV（聚类日历并集）** 的 τ 重叠收益样本方差（再 **× ``annualized_days()/τ``** 年化）；
  ``var_hv`` / ``var_lv`` 为 **起点日分别落在 HV / LV** 的同定义样本方差（同样年化）。缩放比 ``sqrt(var_k/var_full)`` 与是否先乘年化常数无关。**OA** 不缩放。
- **可选（``--hv-lv-via-subset``）**：对齐 ``ETH_risk_premia_plan.md`` §1.3.1 文案 — **HV / LV** 的 P 仅基于
  **起点日**属于该簇的重叠简单收益子样本；**OA** 仍为全样本。

**估计器（规划）**：**S8_0** **默认** **``btc_poly_gev``**（与 BTC ``S6_1`` **multivar** 含 **GEV** 尾一致）；**``--method btc_poly``** 为无尾、翼置 0 的旧版；**``kde``** 为备用。

- **``--method kde``**：``scipy.stats.gaussian_kde``（**备用 KDE**）。  
- **``--method btc_poly``**：直方图+多项式核映射到 ``[-1,1]``，**翼部置 0**（无 GEV）。  
- **``--method btc_poly_gev``**（**默认**）：与 BTC ``S6_1_*_multivar_9_27_45.m`` 中 ``P_epdf_overall_ttm27`` 同构 —
  ``computePDFusingECDF_10th_poly`` + **``gev_tail``**（左右尾 **GEV** 拟合 + ``spline`` 接中部），再插值到 ``_GRID_FULL`` 并梯形归一。

**输出**

- **主表（BTC 形式）**：``results/ttm_XX/P_density/ePDF/P_ePDF_{OA|HV|LV}_ttm{τ}day.xlsx``  
  列 **``Returns``**（与 ``_GRID_FULL`` 一致，即状态网格）、**``P_NB6`` … ``P_NB15``**（与 BTC ``differentNB`` 循环一致）。  
  **KDE 备用**：``results/ttm_XX/P_density/ePDF/P_KDE_{OA|HV|LV}_ttm{τ}day.xlsx``，列 ``Returns``, ``P_KDE``。  
- **可选 CSV**（``--write-csv``）：与 xlsx 同目录 ``P_density/ePDF/P_empirical_*_ttm{τ}day.csv``（单列 ``--n-bin``）。

**先决**：``Q_matrix_{τ}day.csv``（至少表头日期非空，与主分析日历一致）；**S7** ``common_dates_cluster.csv``；现货 ``function.load_eth_daily``。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from numpy.polynomial import Polynomial

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from function import (  # noqa: E402
    ETH_DAILY_CSV,
    ETH_P_DENSITY_EXCEL_SUBDIR,
    ETH_Q_MATRIX_MON_STEP_SUBDIR,
    ETH_Q_MATRIX_OUT_DIR,
    PRIMARY_TTMS,
    _GRID_FULL,
    annualized_days,
    clustering_multivariate_run_dir,
    ensure_results_dir,
    load_eth_daily,
)


def _read_q_matrix_header_dates(q_matrix_path: Path) -> List[str]:
    """First row of ``Q_matrix_*.csv`` is date column names."""
    hdr = pd.read_csv(q_matrix_path, nrows=0)
    cols = [str(c) for c in hdr.columns]
    if not cols:
        raise ValueError(f"empty header: {q_matrix_path}")
    first = cols[0].lower()
    if first in ("return", "m", "moneyness", "ret"):
        cols = cols[1:]
    return cols


def overlapping_simple_returns_full_sample(
    eth: pd.DataFrame,
    ttm: int,
    *,
    var_full: Optional[float] = None,
    var_cluster: Optional[float] = None,
) -> np.ndarray:
    """
    BTC ``Simple_return_fullsample_overlapping``: row ``t`` uses prices ``t`` and ``t+ttm``:
    ``(P[t+ttm]-P[t])/P[t]``. Requires strictly increasing dates with **one row per calendar step** in the
    price panel (same as MATLAB ``(1+ttm):end`` indexing).
    """
    eth = eth.sort_values("date").reset_index(drop=True)
    p = eth["price"].to_numpy(dtype=float)
    if len(p) <= ttm:
        return np.array([], dtype=float)
    r = (p[ttm:] - p[:-ttm]) / p[:-ttm]
    r = r[np.isfinite(r)]
    if var_full is not None and var_cluster is not None and var_full > 0:
        r = r * np.sqrt(float(var_cluster) / float(var_full))
    return r


def overlapping_simple_returns_with_start_dates(
    eth: pd.DataFrame,
    ttm: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    与 ``Simple_return_fullsample_overlapping`` 相同，但返回与每个收益对应的 **起点日历日**（长度 ``n - ttm``）。
    """
    eth = eth.sort_values("date").reset_index(drop=True)
    p = eth["price"].to_numpy(dtype=float)
    d = pd.to_datetime(eth["date"], errors="coerce").dt.normalize()
    if len(p) <= ttm:
        return np.array([], dtype=float), np.array([], dtype="datetime64[ns]")
    r = (p[ttm:] - p[:-ttm]) / p[:-ttm]
    starts = d.iloc[:-ttm].to_numpy()
    ok = np.isfinite(r)
    return r[ok], starts[ok]


def load_common_dates_cluster(path: Path) -> pd.DataFrame:
    """S7 产出：列 ``Date``, ``Cluster``（0=HV，1=LV）。"""
    df = pd.read_csv(path)
    col_d = next((c for c in df.columns if str(c).lower() == "date"), df.columns[0])
    col_c = next((c for c in df.columns if str(c).lower() == "cluster"), None)
    if col_c is None:
        raise ValueError(f"missing Cluster column: {path}")
    out = pd.DataFrame(
        {
            "date": pd.to_datetime(df[col_d], errors="coerce").dt.normalize(),
            "cluster": pd.to_numeric(df[col_c], errors="coerce").astype("Int64"),
        }
    )
    out = out.dropna(subset=["date", "cluster"])
    return_out = out[out["cluster"].isin((0, 1))].reset_index(drop=True)
    if return_out.empty:
        raise ValueError(f"no rows with Cluster 0/1: {path}")
    return return_out


def _sample_var(x: np.ndarray, *, ddof: int = 1) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size <= ddof:
        return float("nan")
    return float(np.var(x, ddof=ddof))


def cluster_start_masks(
    start_dates: np.ndarray,
    cluster_df: pd.DataFrame,
) -> Tuple[np.ndarray, np.ndarray]:
    """与 ``oa_hv_lv_variance_scales`` 相同的起点日 → HV(0)/LV(1) 掩码。"""
    hv_idx = pd.DatetimeIndex(
        pd.to_datetime(cluster_df.loc[cluster_df["cluster"] == 0, "date"], errors="coerce")
    ).normalize()
    lv_idx = pd.DatetimeIndex(
        pd.to_datetime(cluster_df.loc[cluster_df["cluster"] == 1, "date"], errors="coerce")
    ).normalize()
    starts_ts = pd.DatetimeIndex(pd.to_datetime(start_dates, errors="coerce")).normalize()
    mh = starts_ts.isin(hv_idx)
    ml = starts_ts.isin(lv_idx)
    return np.asarray(mh, dtype=bool), np.asarray(ml, dtype=bool)


def oa_hv_lv_variance_scales(
    returns: np.ndarray,
    start_dates: np.ndarray,
    cluster_df: pd.DataFrame,
    *,
    ttm: int,
    ddof: int = 1,
) -> Dict[str, float]:
    """
    返回 **年化** ``var_full``, ``var_hv``, ``var_lv``（τ 期重叠简单收益的样本方差 × ``annualized_days()/τ``），用于
    ``r_scaled = r * sqrt(var_k / var_full)``（**比值**与未年化相同；打印与元数据为年化方差）。

    - ``var_full``：**仅**起点日落在 **S7 聚类日历 HV∪LV** 上的那些 τ 收益；
    - ``var_hv`` / ``var_lv``：起点日分别在 HV / LV 子样本上的方差（同上年化）。
    """
    if returns.size == 0:
        return {"var_full": float("nan"), "var_hv": float("nan"), "var_lv": float("nan")}

    mask_hv, mask_lv = cluster_start_masks(start_dates, cluster_df)
    mask_union = mask_hv | mask_lv
    ann = annualized_days() / float(ttm)

    def _ann_cluster_var(idx: np.ndarray) -> float:
        if not np.any(idx):
            return float("nan")
        v = _sample_var(returns[idx], ddof=ddof)
        if not np.isfinite(v) or v < 0:
            return float("nan")
        return float(v * ann)

    var_full = _ann_cluster_var(mask_union)
    var_hv = _ann_cluster_var(mask_hv)
    var_lv = _ann_cluster_var(mask_lv)

    return {"var_full": var_full, "var_hv": var_hv, "var_lv": var_lv}


def rescale_overlapping_simple_returns(
    returns: np.ndarray,
    var_full: float,
    var_cluster: float,
) -> np.ndarray:
    """BTC ``rescale_shift_return_exp`` 在均值为 0、不外推移位时的标量分支。"""
    r = np.asarray(returns, dtype=float)
    if not np.isfinite(var_full) or var_full <= 0:
        return r
    if not np.isfinite(var_cluster) or var_cluster <= 0:
        return r
    return r * np.sqrt(var_cluster / var_full)


def histogram_poly_pdf_btc(
    data: np.ndarray,
    n_bin: int,
    *,
    poly_degree: int = 10,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Port of BTC ``computePDFusingECDF_10th_poly``（中部核；**翼部**见 ``epdf_on_grid_btc_poly_gev`` / ``gev_tail_combine``）。

    **中部**：在 **样本 10%–90% 分位** 内用直方图 + **``numpy.polynomial.Polynomial.fit``**（scaled domain，减轻高阶 **Runge**）光滑，并把该段面积规范到 **0.8**；
    映到全网格 ``epdf_on_grid_btc_poly`` 时对 **多项式支撑外** 用线性插值的 **left/right=0**（两翼 **人为置 0**），
    再对 ``[-1,1]`` 全格梯形 **重归一化** 为总质量 1。接 **GEV 翼** 时用 ``epdf_on_grid_btc_poly_gev`` / ``gev_tail_combine``（对齐 BTC ``P_epdf_overall_ttm*``）。
    """
    d = np.asarray(data, dtype=float)
    d = d[np.isfinite(d)]
    if d.size < max(30, n_bin + 2):
        raise ValueError(f"need more data points for ePDF (got {d.size})")
    p10, p90 = np.percentile(d, [10, 90])
    edges = np.linspace(float(np.min(d)), float(np.max(d)), int(n_bin) + 1)
    counts, _ = np.histogram(d, bins=edges)
    x_centers = (edges[:-1] + edges[1:]) / 2.0
    c = counts.astype(float)
    den = np.trapz(c, x_centers)
    if den <= 0:
        den = 1.0
    n_norm = c / den
    mask = (x_centers > p10) & (x_centers < p90) & np.isfinite(n_norm)
    xs = x_centers[mask]
    ns = n_norm[mask]
    if xs.size < 3:
        xs = x_centers
        ns = n_norm
    X_cut = np.concatenate(([p10], xs, [p90]))
    f_cut = np.interp(
        X_cut,
        x_centers,
        n_norm,
        left=float(n_norm[0]) if n_norm.size else 0.0,
        right=float(n_norm[-1]) if n_norm.size else 0.0,
    )
    deg = min(poly_degree, max(1, X_cut.size - 1))
    # ``np.polyfit`` 高阶时在区间端易产生 Runge 振荡，左接缝处会误导 GEV 目标；改用scaled-domain ``Polynomial.fit``（同cheb 型，更稳）
    dom_lo, dom_hi = float(np.min(X_cut)), float(np.max(X_cut))
    poly = Polynomial.fit(X_cut, f_cut, deg, domain=[dom_lo, dom_hi])
    x_fit = np.linspace(float(p10), float(p90), 1000)
    y_fit = poly(x_fit)
    y_fit = np.maximum(y_fit, 0.0)
    integ = np.trapz(y_fit, x_fit)
    if integ <= 0:
        integ = 1.0
    y_fit = y_fit / integ * 0.8
    return x_fit, y_fit


def epdf_on_grid_btc_poly(
    samples: np.ndarray,
    grid: np.ndarray,
    n_bin: int,
) -> np.ndarray:
    x_fit, y_fit = histogram_poly_pdf_btc(samples, n_bin)
    f = np.interp(
        np.asarray(grid, dtype=float),
        x_fit,
        y_fit,
        left=0.0,
        right=0.0,
    )
    f = np.maximum(f, 0.0)
    g = np.asarray(grid, dtype=float)
    a = np.trapz(f, g)
    if a > 0:
        f = f / a
    return f


def epdf_on_grid_kde(samples: np.ndarray, grid: np.ndarray) -> np.ndarray:
    from scipy.stats import gaussian_kde

    d = np.asarray(samples, dtype=float)
    d = d[np.isfinite(d)]
    if d.size < 5:
        raise ValueError("KDE needs at least 5 finite returns")
    kde = gaussian_kde(d)
    f = kde.evaluate(np.asarray(grid, dtype=float))
    f = np.maximum(f, 0.0)
    g = np.asarray(grid, dtype=float)
    a = np.trapz(f, g)
    if a > 0:
        f = f / a
    return f


# --- BTC ``S6_1_RiskPremia_BP_write_QP_*_multivar_9_27_45.m`` — ``GEV_tail`` + ``P_epdf_overall_*`` ---
#
# **单侧极值与轴向**（GEV 在工具箱里是 **极大值** 族，只自然描述“一端的长尾”）：
#
# - **收益左尾**（大额负收益）：在变换 ``U = -R`` 上拟合；``U`` 大 ↔ ``R`` 更负。代码里一律在 **``x = -r``**
#   处调用 ``_gevpdf_matlab`` / ``_gevcdf_matlab``（与 Matlab 左尾在 **-R** 上一致），**不要把左尾当成直接在负的 ``r`` 上套同一轴向的 GEV**。
# - **收益右尾**（大额正收益）：在 **``x = r``** 上直接调用（``x`` 为正的分位网格）。
#
# 初值 ``genextreme.fit``：左用 ``u = -r``（``r<0``）与上述轴向一致；``k_{\\mathrm{Matlab}} = -c_{\\mathrm{scipy}}``。


def _gevpdf_matlab(x: np.ndarray, k: float, sigma: float, mu: float) -> np.ndarray:
    """MathWorks ``gevpdf(x,k,sigma,mu)``。**左尾传入 ``x=-r``，右尾传入 ``x=r``**（见文件头 GEV 注释）。"""
    x = np.asarray(x, dtype=float)
    sigma = float(sigma)
    if sigma <= 0 or not np.isfinite(sigma):
        return np.full_like(x, np.nan, dtype=float)
    z = (x - mu) / sigma
    out = np.zeros_like(x, dtype=float)
    if abs(k) < 1e-12:
        ok = np.isfinite(z)
        out[ok] = np.exp(-z[ok] - np.exp(-z[ok])) / sigma
        return out
    t = 1.0 + k * z
    ok = t > 0
    out[ok] = (t[ok] ** (-1.0 / k - 1.0)) * np.exp(-(t[ok] ** (-1.0 / k))) / sigma
    return out


def _gevcdf_matlab(x: np.ndarray, k: float, sigma: float, mu: float) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    sigma = float(sigma)
    if sigma <= 0 or not np.isfinite(sigma):
        return np.full_like(x, np.nan, dtype=float)
    z = (x - mu) / sigma
    out = np.zeros_like(x, dtype=float)
    if abs(k) < 1e-12:
        ok = np.isfinite(z)
        out[ok] = np.exp(-np.exp(-z[ok]))
        return out
    t = 1.0 + k * z
    ok = t > 0
    out[ok] = np.exp(-(t[ok] ** (-1.0 / k)))
    out[~ok] = 0.0
    return out


class GEVTailOptions:
    """与 ``S6_1_RiskPremia_BP_write_QP_c0_NB_xlsx_multivar_9_27_45.m`` 中 ``GEV_tail`` 默认参数对齐。"""

    __slots__ = (
        "initial_left",
        "initial_right",
        "ub_left",
        "lb_left",
        "ub_right",
        "lb_right",
    )

    def __init__(
        self,
        *,
        initial_left: Tuple[float, float, float] = (-0.18, 0.1, 0.02),
        initial_right: Tuple[float, float, float] = (-0.18, 0.1, -0.1),
        ub_left: Tuple[float, float, float] = (0.4, 0.11, 0.5),
        lb_left: Tuple[float, float, float] = (-0.5, 0.05, -0.5),
        ub_right: Tuple[float, float, float] = (0.4, 0.11, 0.5),
        lb_right: Tuple[float, float, float] = (-0.5, 0.05, -0.5),
    ) -> None:
        self.initial_left = initial_left
        self.initial_right = initial_right
        self.ub_left = ub_left
        self.lb_left = lb_left
        self.ub_right = ub_right
        self.lb_right = lb_right


def _clip_vec(x: np.ndarray, lb: np.ndarray, ub: np.ndarray) -> np.ndarray:
    return np.minimum(np.maximum(x, lb), ub)


def _warm_start_left_gev(
    raw_returns: np.ndarray,
    lb: np.ndarray,
    ub: np.ndarray,
    *,
    min_u: int = 80,
) -> Optional[np.ndarray]:
    """
    用 ``u_i=-r_i`` 的 **MLE（scipy.genextreme）** 给 Matlab 形参初值 ``(k,\\sigma,\\mu)``，其中 ``k=-c_{\\mathrm{scipy}}``。

    **样本**：优先 **全部负收益日** ``r<0``（``u>0``，与「左尾压力」同向，比极窄分位子样本更稳）；不足 ``min_u`` 时再并上 ``r\\le q_{25\\%}``。
    注意：经验收益并非 GEV 抽样，此初值仅为把优化送进合理盆地，**不可替代** BTC 锚点约束。
    """
    from scipy.stats import genextreme

    s = np.asarray(raw_returns, dtype=float)
    s = s[np.isfinite(s)]
    if s.size < 50:
        return None
    u = -s[s < 0]
    u = u[u > 1e-10]
    if u.size < min_u:
        thr = float(np.percentile(s, 25.0))
        u = -s[s <= thr]
        u = u[u > 1e-10]
    if u.size < 40:
        return None
    try:
        c_hat, loc_hat, scale_hat = genextreme.fit(u)
    except Exception:
        return None
    if not np.isfinite(scale_hat) or scale_hat <= 0:
        return None
    # **符号**：``scipy.stats.genextreme`` 的形状参数 ``c`` 与 Matlab ``gevpdf(x,k,σ,μ)`` 的 ``k`` **相反**
    # （``genextreme.pdf(x,c,…)`` ≡ 本文件的 ``_gevpdf_matlab(x, -c, σ, μ)``）。初值须用 ``k = -c_hat``。
    k_hat = float(-c_hat)
    x0 = np.array([k_hat, float(scale_hat), float(loc_hat)], dtype=float)
    return _clip_vec(x0, lb, ub)


def _optimize_gev_three_params(
    objective: Any,
    nl_eq: Any,
    nl_ineq: Any,
    x0: np.ndarray,
    lb: np.ndarray,
    ub: np.ndarray,
    *,
    n_random_starts: int = 7,
    rng_seed: int = 42,
) -> Tuple[Any, Dict[str, Any]]:
    """
    GEV 单侧三参数（``k, sigma, mu``）：约束与目标与 BTC 单侧一致；**左右尾分开**优化，避免六参数联合时左尾为右尾让步。
    """
    from scipy.optimize import Bounds, NonlinearConstraint, minimize

    x0 = _clip_vec(np.asarray(x0, dtype=float), lb, ub)
    bounds = Bounds(lb, ub)
    con_eq = NonlinearConstraint(
        lambda x: nl_eq(x),
        np.zeros(1),
        np.zeros(1),
    )
    con_ineq = NonlinearConstraint(
        lambda x: nl_ineq(x),
        np.zeros(2),
        np.full(2, np.inf),
    )

    starts: List[np.ndarray] = [x0]
    rng = np.random.default_rng(rng_seed)
    span = np.maximum(ub - lb, 1e-6)
    ndim = int(x0.size)
    for _ in range(n_random_starts):
        u = rng.uniform(0.15, 0.85, size=ndim)
        x_try = lb + u * span
        starts.append(_clip_vec(x_try, lb, ub))

    best_res: Any = None
    best_key: Tuple[float, float, float] = (float("inf"), float("inf"), float("inf"))

    def score_res(res: Any) -> Tuple[float, float, float]:
        x = res.x
        v_eq = float(np.max(np.abs(nl_eq(x))))
        vi = nl_ineq(x)
        v_in = float(np.nanmin(vi)) if vi.size else float("nan")
        obj = float(objective(x))
        in_feas = np.isfinite(v_eq) and np.isfinite(v_in) and v_eq < 5e-4 and v_in >= -1e-4
        key = (0.0 if in_feas else 1.0, v_eq + max(0.0, -v_in) * 10.0, obj)
        return key

    last_err: str | None = None
    for xs in starts:
        for method, use_cons in (
            ("trust-constr", True),
            ("SLSQP", True),
        ):
            if not use_cons:
                continue
            try:
                if method == "trust-constr":
                    res = minimize(
                        objective,
                        xs,
                        method="trust-constr",
                        bounds=bounds,
                        constraints=[con_eq, con_ineq],
                        options={"maxiter": 2000, "gtol": 1e-8, "xtol": 1e-10},
                    )
                else:
                    res = minimize(
                        objective,
                        xs,
                        method="SLSQP",
                        bounds=list(zip(lb, ub)),
                        constraints=(
                            {"type": "eq", "fun": nl_eq},
                            {"type": "ineq", "fun": nl_ineq},
                        ),
                        options={"maxiter": 800, "ftol": 1e-10},
                    )
            except Exception as e:
                last_err = str(e)
                continue
            k = score_res(res)
            if k < best_key:
                best_key = k
                best_res = res

    def _viol_metrics(x: np.ndarray) -> Tuple[float, float]:
        return float(np.max(np.abs(nl_eq(x)))), float(np.min(nl_ineq(x)))

    meta: Dict[str, Any] = {"fallback": None, "last_error": last_err}
    # 以 **约束违反度** 为准（``trust-constr`` 可能 ``success=False`` 但已接近可行）
    if best_res is not None and best_key[0] == 0.0:
        xb = best_res.x
        me, mi = _viol_metrics(xb)
        meta.update(
            {
                "primary_method": "trust-constr_or_SLSQP",
                "scipy_success": bool(getattr(best_res, "success", False)),
                "scipy_nit": getattr(best_res, "nit", None),
                "max_abs_eq": me,
                "min_ineq": mi,
                "final_objective": float(objective(xb)),
            }
        )
        return best_res, meta

    def soft_obj(x: np.ndarray) -> float:
        base = float(objective(x))
        ve = nl_eq(x)
        pen_eq = float(np.dot(ve, ve)) * 500.0
        vi = nl_ineq(x)
        pen_in = float(np.sum(np.maximum(0.0, -vi) ** 2)) * 500.0
        return base + pen_eq + pen_in

    seed_x = best_res.x if best_res is not None else x0
    best_soft: Any = None
    best_v = float("inf")
    polish_starts = [seed_x] + starts[:3]
    for xs in polish_starts:
        try:
            r2 = minimize(
                soft_obj,
                _clip_vec(xs, lb, ub),
                method="L-BFGS-B",
                bounds=list(zip(lb, ub)),
                options={"maxiter": 800},
            )
        except Exception:
            continue
        if r2.fun < best_v:
            best_v = float(r2.fun)
            best_soft = r2

    if best_soft is not None:
        xs = best_soft.x
        me_s, mi_s = _viol_metrics(xs)
        use_soft = True
        if best_res is not None:
            me_b, mi_b = _viol_metrics(best_res.x)
            if me_b <= me_s and mi_b >= mi_s and (me_b < 1e-2 or mi_b >= 0):
                use_soft = False
        if use_soft:
            meta["fallback"] = "L-BFGS-B_soft_penalty"
            meta["primary_method"] = "L-BFGS-B_soft_penalty"
            meta["scipy_success"] = bool(getattr(best_soft, "success", False))
            meta["max_abs_eq"] = me_s
            meta["min_ineq"] = mi_s
            meta["final_objective"] = float(objective(xs))
            meta["soft_penalty_total"] = best_v
            return best_soft, meta

    if best_res is not None:
        xb = best_res.x
        me, mi = _viol_metrics(xb)
        meta["fallback"] = "best_infeasible_constrained"
        meta["primary_method"] = "trust_constr_SLSQP_infeasible"
        meta["scipy_success"] = bool(getattr(best_res, "success", False))
        meta["max_abs_eq"] = me
        meta["min_ineq"] = mi
        meta["final_objective"] = float(objective(xb))
        return best_res, meta

    raise RuntimeError(f"GEV optimization failed ({last_err or 'unknown'})")


def _tail_left_nondecreasing(y: np.ndarray) -> np.ndarray:
    """沿 ``r`` 从 -1 向中部：单峰密度左支应单调不降（消除凹陷以免 \\(\\hat q/\\hat p\\) 左尾虚高）。"""
    y = np.asarray(y, dtype=float).copy()
    for i in range(1, y.size):
        if y[i] < y[i - 1]:
            y[i] = y[i - 1]
    return y


def _tail_right_nonincreasing(y: np.ndarray) -> np.ndarray:
    """沿 ``r`` 从中部向右：单峰密度右支应单调不升。"""
    y = np.asarray(y, dtype=float).copy()
    for i in range(1, y.size):
        if y[i] > y[i - 1]:
            y[i] = y[i - 1]
    return y


def _audit_left_gev_btc_conditions(
    k1: float,
    s1: float,
    m1: float,
    target_l: np.ndarray,
    rnd_l: np.ndarray,
    *,
    r_join_left: float,
    spl_at_join: float,
    cdf_l: float = 0.1,
) -> Dict[str, Any]:
    """
    在 **优化得到** 的 ``(k_1,\\sigma_1,\\mu_1)`` 上核对 BTC ``GEV_tail`` 左尾条件（**修补/归一前**）；对象始终是 **左尾段用的 GEV(U)**，``U=-R``。

    - **条件 1（硬等式）**：在 **收益** ``r=\\alpha_l=\\min r_t`` 处，``\\hat f_{\\mathrm{GEV}}(-\\alpha_l)=\\texttt{rnd_l[0]}``，
      即 **辅助变量** ``U=-r`` 取 ``u=-\\alpha_l`` 时的 GEV **密度**，与 **PCHIP(多项式核)** 在同一点 ``r=\\alpha_l`` 的值对齐（核刻度，尚未整段 trapz 成最终 ``\\hat p``）。

    - **条件 2（硬不等式）**：``\\mathbb{P}_{\\mathrm{GEV}}(U > -\\alpha_l) = 1-\\texttt{gevcdf}(-\\alpha_l)`` ∈ ``[0.09,0.11]``（``\\texttt{cdf_l}=0.1``）。
      这是对 **参数族 GEV(U)** 在 **单个阈值** ``u_0=-\\alpha_l`` 上 **上尾质量** 的盒子约束 **不是**「收益 ``R`` 落在某左半轴的累积概率」、**不是** ``\\hat q``/``\\hat p`` 的边际 CDF、**更不是** ``\\widehat{PK}=\\hat q/\\hat p`` 的 CDF。
      图上 PK 左尾「很宽」与这一数字 **无直接可比性**。

    - **条件 3（软，BTC）**：``r=\\alpha_l+0.01`` 处 PDF 逼近 ``\\texttt{rnd_l[1]}``（仅进目标，非硬等式）。
      **ETH 增补软项**：``r=r_{\\mathrm{join}}=tl-0.001`` 处 PDF vs ``\\texttt{spl_at_join}``。
    """
    alpha0 = float(target_l[0])
    alpha1 = float(target_l[1])
    pdf0 = float(_gevpdf_matlab(np.array([-alpha0]), k1, s1, m1)[0])
    pdf1 = float(_gevpdf_matlab(np.array([-alpha1]), k1, s1, m1)[0])
    F0 = float(_gevcdf_matlab(np.array([-alpha0]), k1, s1, m1)[0])
    surv = 1.0 - F0
    pdf_join = float(_gevpdf_matlab(np.array([-r_join_left]), k1, s1, m1)[0])
    c1 = 1.0 - F0 - cdf_l - 0.01
    c2 = -0.01 - (1.0 - F0 - cdf_l)
    neg_c1, neg_c2 = -float(c1), -float(c2)
    tol_eq = 5e-4
    tol_ineq = 1e-4
    return {
        "eq_pdf_at_minus_alpha": {
            "gevpdf": pdf0,
            "spline_rnd": float(rnd_l[0]),
            "abs_mismatch": abs(pdf0 - float(rnd_l[0])),
            "ok_abs_le": tol_eq,
            "pass": bool(abs(pdf0 - float(rnd_l[0])) <= tol_eq),
        },
        "ineq_survival_1_minus_F": {
            "value": surv,
            "target_cdf_l": cdf_l,
            "allowed_interval": [cdf_l - 0.01, cdf_l + 0.01],
            "pass_band": bool((cdf_l - 0.01) - tol_ineq <= surv <= (cdf_l + 0.01) + tol_ineq),
            "nlp_ineq_neg_c1": neg_c1,
            "nlp_ineq_neg_c2": neg_c2,
            "pass_nlp_both_ge0": bool(neg_c1 >= -tol_ineq and neg_c2 >= -tol_ineq),
        },
        "soft_pdf_inner_anchor": {
            "gevpdf_minus_alpha_plus_01": pdf1,
            "spline_rnd": float(rnd_l[1]),
            "abs_gap": abs(pdf1 - float(rnd_l[1])),
        },
        "soft_join_pdf": {
            "r_join": r_join_left,
            "gevpdf": pdf_join,
            "spline": float(spl_at_join),
            "abs_gap": abs(pdf_join - float(spl_at_join)),
        },
    }


def _audit_right_gev_btc_conditions(
    k2: float,
    s2: float,
    m2: float,
    target_r: np.ndarray,
    rnd_r: np.ndarray,
    *,
    cdf_r: float = 0.9,
) -> Dict[str, Any]:
    """右尾：等式 ``gevpdf(max r_t)=rnd_r[1]``；不等式 ``gevcdf(max)\\in[cdf_r-0.01,cdf_r+0.01]``。"""
    tr0 = float(target_r[0])
    tr1 = float(target_r[1])
    pdf_hi = float(_gevpdf_matlab(np.array([tr1]), k2, s2, m2)[0])
    pdf_lo = float(_gevpdf_matlab(np.array([tr0]), k2, s2, m2)[0])
    Fr = float(_gevcdf_matlab(np.array([tr1]), k2, s2, m2)[0])
    c3 = Fr - cdf_r - 0.01
    c4 = -0.01 - (Fr - cdf_r)
    neg_c3, neg_c4 = -float(c3), -float(c4)
    tol_eq = 5e-4
    tol_ineq = 1e-4
    return {
        "eq_pdf_at_max_r": {
            "gevpdf": pdf_hi,
            "spline_rnd": float(rnd_r[1]),
            "abs_mismatch": abs(pdf_hi - float(rnd_r[1])),
            "pass": bool(abs(pdf_hi - float(rnd_r[1])) <= tol_eq),
        },
        "ineq_cdf_at_max_r": {
            "F": Fr,
            "target_cdf_r": cdf_r,
            "allowed_interval": [cdf_r - 0.01, cdf_r + 0.01],
            "pass_band": bool((cdf_r - 0.01) - tol_ineq <= Fr <= (cdf_r + 0.01) + tol_ineq),
            "nlp_ineq_neg_c3": neg_c3,
            "nlp_ineq_neg_c4": neg_c4,
            "pass_nlp_both_ge0": bool(neg_c3 >= -tol_ineq and neg_c4 >= -tol_ineq),
        },
        "soft_pdf_anchor_minus_01": {
            "gevpdf": pdf_lo,
            "spline_rnd": float(rnd_r[0]),
            "abs_gap": abs(pdf_lo - float(rnd_r[0])),
        },
    }


def _left_gev_empirical_vs_fitted(
    raw_returns: np.ndarray,
    segL: np.ndarray,
    k1: float,
    s1: float,
    m1: float,
) -> Dict[str, Any]:
    """
    在左段网格 ``segL`` 上比较：**全样本 KDE** 与 **当前左 GEV**（``_gevpdf_matlab(-r,k1,s1,m1)``）在 **各自 trapz(segL) 归一** 后的 RMSE；
    另给尾样本 ``u=-r`` 在 ``scipy.genextreme.pdf(u,-k1,loc=m1,scale=s1)`` 下的对数似然（用于粗查拟合质量）。
    """
    from scipy.stats import gaussian_kde, genextreme

    d = np.asarray(raw_returns, dtype=float)
    d = d[np.isfinite(d)]
    out: Dict[str, Any] = {}
    if d.size < 40 or segL.size < 3:
        out["note"] = "insufficient_data"
        return out
    kde = gaussian_kde(d, bw_method="scott")
    f_emp = np.maximum(kde.evaluate(segL), 0.0)
    f_gev = np.maximum(_gevpdf_matlab(-segL, k1, s1, m1), 0.0)
    ie = float(np.trapz(f_emp, segL))
    ig = float(np.trapz(f_gev, segL))
    out["trapz_kde_on_segL"] = ie
    out["trapz_gev_on_segL"] = ig
    if ie > 1e-20 and ig > 1e-20:
        fe, fg = f_emp / ie, f_gev / ig
        out["rmse_shape_vs_kde_on_segL"] = float(np.sqrt(np.trapz((fe - fg) ** 2, segL)))

    thr = float(np.percentile(d, 12.0))
    u = -d[d <= thr]
    u = u[u > 1e-10]
    if u.size > 10:
        # Matlab ``k`` → scipy 形状 ``-k``（见 ``_warm_start_left_gev`` 注释）
        pdf_u = genextreme.pdf(u, -float(k1), loc=float(m1), scale=float(s1))
        lp = np.log(np.maximum(pdf_u, 1e-300))
        lp = lp[np.isfinite(lp)]
        if lp.size > 0:
            out["loglik_sum_tail_u"] = float(np.sum(lp))
            out["n_tail_u"] = int(u.size)
            out["loglik_mean_tail_u"] = float(np.mean(lp))

    return out


def gev_tail_combine(
    q_rt: np.ndarray,
    r_t: np.ndarray,
    opts: Optional[GEVTailOptions] = None,
    *,
    raw_returns: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    复刻 BTC ``GEV_tail``（``S6_1_RiskPremia_BP_write_QP_c0_NB_xlsx_multivar_9_27_45.m`` 537–540 行）：

    **轴向（单侧长尾）**：``gevpdf``/``gevcdf`` 是 **极大值** GEV。**左尾**在 **``U=-R``** 上估计（代码中所有左尾 PDF/CDF 的自变量为 **``-r``**）；
    **右尾**在 **``R`` 本身**上估计（自变量为 **``r>0``** 段）。两侧 **不能** 共用同一“收益轴正向”而不翻面。

    中部对 ``(r_t,q_rt)`` 用 **PCHIP**（避免 ``CubicSpline`` 在核边缘过冲使 ``rnd_l`` 失真）。

    **拼接网格（与 Matlab ``rt``/``Q_rt`` 一致）**：左段 ``r\in[-1,\,tl-0.001]``；
    中段 ``r\in[tl,\,tr]``（含端点）；右段 ``r\in[tr+0.001,\,1]``。共 2001 点。

    **ETH 增补**：左尾在 ``r=tl-0.001`` 处增 PDF 软匹配；``raw_returns`` 时左初值为 ``genextreme.fit(u)``，``u=-r``（优先 ``r<0``），且 ``k=-c_{\\mathrm{scipy}}``。
    """
    from scipy.interpolate import PchipInterpolator

    o = opts or GEVTailOptions()
    q_rt = np.asarray(q_rt, dtype=float)
    r_t = np.asarray(r_t, dtype=float)
    order = np.argsort(r_t)
    r_t = r_t[order]
    q_rt = q_rt[order]
    if float(np.max(r_t)) >= 1.0 or float(np.min(r_t)) <= -1.0:
        raise ValueError("GEV_tail requires min(r_t) > -1 and max(r_t) < 1")

    alpha_r = float(np.max(r_t))
    target_r = np.array([alpha_r - 0.01, alpha_r], dtype=float)
    spl_q = PchipInterpolator(r_t, q_rt)
    rnd_r = np.clip(spl_q(target_r), 0.0, None)
    cdf_r = 0.9

    alpha_l = float(np.min(r_t))
    target_l = np.array([alpha_l, alpha_l + 0.01], dtype=float)
    rnd_l = np.clip(spl_q(target_l), 0.0, None)
    cdf_l = 0.1

    tl = float(np.round(target_l[0], 3))
    tr = float(np.round(target_r[1], 3))
    if tl >= tr - 1e-6:
        raise ValueError("GEV_tail: degenerate poly support (tl >= tr)")

    # 与 Matlab ``rt`` / ``Q_rt`` 一致（``S6_1_*_multivar_9_27_45.m`` 537–540 行）：
    # 左段 ``-1:(tl-0.001)`` 仅 GEV；中段 ``tl:tr`` 全为 spline；右段 ``(tr+0.001):1`` 仅 GEV。
    tl_m = int(round(tl * 1000))
    tr_m = int(round(tr * 1000))
    if tl_m <= -1000 or tr_m >= 1000 or tl_m > tr_m:
        raise ValueError(f"GEV_tail: invalid join indices tl_m={tl_m}, tr_m={tr_m}")

    segL = np.arange(-1000, tl_m, dtype=np.int64) / 1000.0
    mid = np.arange(tl_m, tr_m + 1, dtype=np.int64) / 1000.0
    segR = np.arange(tr_m + 1, 1001, dtype=np.int64) / 1000.0

    # 左段末端拼接横坐标（与 ``segL`` 末点一致）：此处原流程无显式约束，易造成左尾形状与 PCHIP 外推脱节
    r_join_left = float(tl) - 0.001
    spl_at_join = max(float(spl_q(r_join_left)), 0.0)

    def objective_left(x: np.ndarray) -> float:
        k1, s1, m1 = x[0], x[1], x[2]
        pdf_join = float(_gevpdf_matlab(np.array([-r_join_left]), k1, s1, m1)[0])
        return float(
            (_gevpdf_matlab(np.array([-target_l[0]]), k1, s1, m1)[0] - rnd_l[0]) ** 2
            + (_gevpdf_matlab(np.array([-target_l[1]]), k1, s1, m1)[0] - rnd_l[1]) ** 2 / 3.0
            + (1.0 - float(_gevcdf_matlab(np.array([-target_l[0]]), k1, s1, m1)[0]) - cdf_l) ** 2
            + 5.0 * (pdf_join - spl_at_join) ** 2
        )

    def objective_right(x: np.ndarray) -> float:
        k2, s2, m2 = x[0], x[1], x[2]
        return float(
            (_gevpdf_matlab(np.array([target_r[0]]), k2, s2, m2)[0] - rnd_r[0]) ** 2 / 10.0
            + (_gevpdf_matlab(np.array([target_r[1]]), k2, s2, m2)[0] - rnd_r[1]) ** 2
            + (float(_gevcdf_matlab(np.array([target_r[1]]), k2, s2, m2)[0]) - cdf_r) ** 2
        )

    def nl_eq_left(z: np.ndarray) -> np.ndarray:
        k1, s1, m1 = z[0], z[1], z[2]
        return np.array(
            [float(_gevpdf_matlab(np.array([-target_l[0]]), k1, s1, m1)[0] - rnd_l[0])],
            dtype=float,
        )

    def nl_ineq_left(z: np.ndarray) -> np.ndarray:
        k1, s1, m1 = z[0], z[1], z[2]
        c1 = 1.0 - float(_gevcdf_matlab(np.array([-target_l[0]]), k1, s1, m1)[0]) - cdf_l - 0.01
        c2 = -0.01 - (1.0 - float(_gevcdf_matlab(np.array([-target_l[0]]), k1, s1, m1)[0]) - cdf_l)
        return np.array([-c1, -c2], dtype=float)

    def nl_eq_right(z: np.ndarray) -> np.ndarray:
        k2, s2, m2 = z[0], z[1], z[2]
        return np.array(
            [float(_gevpdf_matlab(np.array([target_r[1]]), k2, s2, m2)[0] - rnd_r[1])],
            dtype=float,
        )

    def nl_ineq_right(z: np.ndarray) -> np.ndarray:
        k2, s2, m2 = z[0], z[1], z[2]
        c3 = float(_gevcdf_matlab(np.array([target_r[1]]), k2, s2, m2)[0]) - cdf_r - 0.01
        c4 = -0.01 - (float(_gevcdf_matlab(np.array([target_r[1]]), k2, s2, m2)[0]) - cdf_r)
        return np.array([-c3, -c4], dtype=float)

    x0_l = np.array(list(o.initial_left), dtype=float)
    lb_l = np.array(list(o.lb_left), dtype=float)
    ub_l = np.array(list(o.ub_left), dtype=float)
    x0_r = np.array(list(o.initial_right), dtype=float)
    lb_r = np.array(list(o.lb_right), dtype=float)
    ub_r = np.array(list(o.ub_right), dtype=float)

    warm_left: Optional[np.ndarray] = None
    if raw_returns is not None:
        warm_left = _warm_start_left_gev(raw_returns, lb_l, ub_l)
        if warm_left is not None:
            x0_l = warm_left.astype(float)

    res_l, opt_meta_l = _optimize_gev_three_params(
        objective_left, nl_eq_left, nl_ineq_left, x0_l, lb_l, ub_l, rng_seed=42
    )
    res_r, opt_meta_r = _optimize_gev_three_params(
        objective_right, nl_eq_right, nl_ineq_right, x0_r, lb_r, ub_r, rng_seed=43
    )
    x = res_l.x
    k1, s1, m1 = float(x[0]), float(x[1]), float(x[2])
    x = res_r.x
    k2, s2, m2 = float(x[0]), float(x[1]), float(x[2])

    left_gev_diagnostic: Optional[Dict[str, Any]] = None
    if raw_returns is not None:
        left_gev_diagnostic = _left_gev_empirical_vs_fitted(raw_returns, segL, k1, s1, m1)

    btc_gev_conditions_pre_monotone = {
        "left": _audit_left_gev_btc_conditions(
            k1,
            s1,
            m1,
            target_l,
            rnd_l,
            r_join_left=r_join_left,
            spl_at_join=spl_at_join,
            cdf_l=cdf_l,
        ),
        "right": _audit_right_gev_btc_conditions(
            k2,
            s2,
            m2,
            target_r,
            rnd_r,
            cdf_r=cdf_r,
        ),
        "tol_note": (
            "条件 2 的「0.1」是 GEV(U), U=-R 在阈值 u0=-α_l 上的上尾概率 P(U>u0)，不是 R 的累积质量、不是 PK 的 CDF。"
            " 通过判据与 ``score_res`` 一致：等式 |·|<5e-4、不等式 NLP 分量 >=-1e-4。"
            " 后续 ``_tail_*``/桥接/对 qq 全宽 trapz 归一再插值到网格，最终图上的 \\hat p/\\widehat{PK} 不必与此表同句读。"
        ),
    }

    q_l = np.maximum(_gevpdf_matlab(-segL, k1, s1, m1), 0.0)
    q_mid = np.maximum(spl_q(mid), 0.0).copy()
    q_r = np.maximum(_gevpdf_matlab(segR, k2, s2, m2), 0.0)
    q_l = _tail_left_nondecreasing(q_l)
    q_r = _tail_right_nonincreasing(q_r)
    bridge_l = 0.5 * (float(q_l[-1]) + float(q_mid[0]))
    if q_l.size > 1:
        bridge_l = max(bridge_l, float(q_l[-2]))
    q_l[-1] = bridge_l
    q_mid[0] = bridge_l
    bridge_r = 0.5 * (float(q_r[0]) + float(q_mid[-1]))
    if q_r.size > 1:
        bridge_r = max(bridge_r, float(q_r[1]))
    q_r[0] = bridge_r
    q_mid[-1] = bridge_r
    qq = np.concatenate([q_l, q_mid, q_r])
    rr = np.concatenate([segL, mid, segR])
    if qq.size != rr.size or rr.size != 2001:
        raise ValueError(f"GEV_tail internal: expected 2001 points, got {rr.size}")
    qq = np.maximum(qq, 0.0)
    a0 = float(np.trapz(qq, rr))
    if a0 > 0:
        qq = qq / a0
    details: Dict[str, Any] = {
        "optimizer_success_left": bool(getattr(res_l, "success", False)),
        "optimizer_success_right": bool(getattr(res_r, "success", False)),
        "optimizer_message_left": str(getattr(res_l, "message", "")),
        "optimizer_message_right": str(getattr(res_r, "message", "")),
        "gev_opt_meta_left": opt_meta_l,
        "gev_opt_meta_right": opt_meta_r,
        "solution_left": [k1, s1, m1],
        "solution_right": [k2, s2, m2],
        "target_l": target_l.tolist(),
        "target_r": target_r.tolist(),
        "r_join_left": r_join_left,
        "spl_target_at_join": spl_at_join,
        "warm_start_left": None if warm_left is None else warm_left.tolist(),
        "left_gev_diagnostic": left_gev_diagnostic,
        "btc_gev_conditions_pre_monotone": btc_gev_conditions_pre_monotone,
    }
    return qq, rr, details


def epdf_on_grid_btc_poly_gev(
    samples: np.ndarray,
    grid: np.ndarray,
    n_bin: int,
    *,
    gev_opts: Optional[GEVTailOptions] = None,
) -> np.ndarray:
    """对齐 ``P_epdf_overall_ttm*``：核 + ``gev_tail_combine`` + 状态网格插值与梯形归一。"""
    x_fit, y_fit = histogram_poly_pdf_btc(samples, n_bin)
    qq, rr, _d = gev_tail_combine(y_fit, x_fit, gev_opts, raw_returns=samples)
    g = np.asarray(grid, dtype=float)
    lo_f, hi_f = float(max(qq[0], 0.0)), float(max(qq[-1], 0.0))
    f = np.interp(g, rr, qq, left=lo_f, right=hi_f)
    f = np.maximum(f, 0.0)
    a = float(np.trapz(f, g))
    if a > 0:
        f = f / a
    return f.astype(float)


def default_q_matrix_path(ttm: int, *, use_d15: bool) -> Path:
    base = ETH_Q_MATRIX_OUT_DIR / ETH_Q_MATRIX_MON_STEP_SUBDIR
    suffix = "_d15" if use_d15 else ""
    return base / f"Q_matrix_{ttm}day{suffix}.csv"


def _excel_engine() -> str:
    try:
        import openpyxl  # noqa: F401
    except ImportError as e:
        raise SystemExit(
            ".Excel 输出需要 openpyxl：pip install openpyxl"
        ) from e
    return "openpyxl"


def build_p_epdf_excel_table(
    grid: np.ndarray,
    samples: np.ndarray,
    *,
    n_bin_min: int,
    n_bin_max: int,
    epdf_grid_fn: Callable[[np.ndarray, np.ndarray, int], np.ndarray],
) -> pd.DataFrame:
    """
    BTC ``Q_P_ePDF_*_differentNB_ttm*.xlsx`` 的 **P 侧**列：``Returns`` + ``P_NB{n}``。
    ``epdf_grid_fn`` 为 ``epdf_on_grid_btc_poly`` 或 ``epdf_on_grid_btc_poly_gev``。
    """
    g = np.asarray(grid, dtype=float)
    data: Dict[str, np.ndarray] = {"Returns": g}
    for n_bin in range(n_bin_min, n_bin_max + 1):
        data[f"P_NB{n_bin}"] = epdf_grid_fn(samples, grid, n_bin)
    return pd.DataFrame(data)


def main() -> int:
    p = argparse.ArgumentParser(
        description="S8_0 ePDF (OA/HV/LV) — see ETH_risk_premia_plan §1.3.1"
    )
    p.add_argument("--ttm", type=int, nargs="+", default=list(PRIMARY_TTMS), help="TTM days (e.g. 9 27 45)")
    p.add_argument(
        "--q-matrix",
        type=Path,
        default=None,
        help="Explicit Q_matrix CSV (default: ETH_Q_MATRIX_OUT_DIR/.../Q_matrix_{ttm}day.csv)",
    )
    p.add_argument(
        "--use-d15",
        action="store_true",
        help="Use Q_matrix_*_d15.csv names when --q-matrix is not set",
    )
    p.add_argument("--spot-csv", type=Path, default=None, help="ETH daily (default ETH_DAILY_CSV)")
    p.add_argument(
        "--cluster-csv",
        type=Path,
        default=None,
        help="S7 common_dates_cluster.csv (default: clustering_multivariate_run_dir()/common_dates_cluster.csv)",
    )
    p.add_argument(
        "--robust",
        action="store_true",
        help="Write under results/results_robust/ttm_XX/",
    )
    p.add_argument(
        "--method",
        choices=("kde", "btc_poly", "btc_poly_gev"),
        default="btc_poly_gev",
        help=(
            "默认 btc_poly_gev（+GEV 尾，S6_1 multivar）；btc_poly: 翼置0；kde: 备用 KDE"
        ),
    )
    p.add_argument(
        "--n-bin",
        type=int,
        default=10,
        help="仅 --write-csv 时使用的单档直方箱数（Excel 主表用 --excel-nb-min/max）",
    )
    p.add_argument(
        "--excel-nb-min",
        type=int,
        default=6,
        help="Excel 中 P_NB 列起始 n（BTC 默认 6）",
    )
    p.add_argument(
        "--excel-nb-max",
        type=int,
        default=15,
        help="Excel 中 P_NB 列结束 n（BTC 默认 15，含端点）",
    )
    p.add_argument(
        "--write-csv",
        action="store_true",
        help="另写单档直方 CSV 至 P_density/ePDF/（与 xlsx 同目录，单档 --n-bin）",
    )
    p.add_argument(
        "--ddof",
        type=int,
        default=1,
        help="Passed to numpy.var for var_full / var_hv / var_lv (default 1 = sample variance)",
    )
    p.add_argument(
        "--hv-lv-via-subset",
        action="store_true",
        help=(
            "HV/LV P densities use only overlapping returns with start date in that cluster "
            "(ETH_risk_premia_plan §1.3.1). Default: BTC c0/c1 variance rescaling on the full overlap sample."
        ),
    )
    p.add_argument(
        "--print-gev-diagnostics",
        action="store_true",
        help=(
            "With --method btc_poly_gev: after each regime, print one JSON line (prefix GEV_DIAG) "
            "with left-tail (k,σ,μ), constraint residuals, rmse_shape_vs_kde_on_segL, loglik on tail u=-r."
        ),
    )
    args = p.parse_args()
    if args.excel_nb_min > args.excel_nb_max:
        raise SystemExit("--excel-nb-min must be <= --excel-nb-max")

    cluster_path = args.cluster_csv or (clustering_multivariate_run_dir() / "common_dates_cluster.csv")
    if not cluster_path.is_file():
        raise SystemExit(f"missing cluster file (run S7 first): {cluster_path}")
    cluster_df = load_common_dates_cluster(cluster_path)

    spot_path = args.spot_csv or ETH_DAILY_CSV
    eth = load_eth_daily(spot_path)

    for ttm in args.ttm:
        q_path = args.q_matrix if args.q_matrix is not None else default_q_matrix_path(ttm, use_d15=args.use_d15)
        if not q_path.is_file():
            print(f"skip ttm={ttm}: missing Q_matrix {q_path}", file=sys.stderr)
            continue
        dates_s = _read_q_matrix_header_dates(q_path)
        dates = pd.to_datetime(pd.Series(dates_s), errors="coerce").dropna()
        if dates.empty:
            print(f"skip ttm={ttm}: no dates in header {q_path}", file=sys.stderr)
            continue

        r_all, start_dates = overlapping_simple_returns_with_start_dates(eth, ttm)
        if r_all.size < 20:
            print(f"skip ttm={ttm}: too few overlapping simple returns", file=sys.stderr)
            continue

        scales = oa_hv_lv_variance_scales(
            r_all, start_dates, cluster_df, ttm=ttm, ddof=args.ddof
        )
        var_full = scales["var_full"]
        var_hv = scales["var_hv"]
        var_lv = scales["var_lv"]
        if not np.isfinite(var_full) or var_full <= 0:
            print(f"skip ttm={ttm}: invalid var_full={var_full}", file=sys.stderr)
            continue

        if args.hv_lv_via_subset:
            mask_hv, mask_lv = cluster_start_masks(start_dates, cluster_df)
            r_hv = r_all[mask_hv]
            r_lv = r_all[mask_lv]
            regimes = {
                "OA": (r_all, var_full),
                "HV": (r_hv, var_hv),
                "LV": (r_lv, var_lv),
            }
            if r_hv.size < 20:
                print(
                    f"warning ttm={ttm}: HV subset n={r_hv.size} (<20); HV P may be unreliable",
                    file=sys.stderr,
                )
            if r_lv.size < 20:
                print(
                    f"warning ttm={ttm}: LV subset n={r_lv.size} (<20); LV P may be unreliable",
                    file=sys.stderr,
                )
        else:
            regimes = {
                "OA": (r_all, var_full),
                "HV": (
                    rescale_overlapping_simple_returns(r_all, var_full, var_hv),
                    var_hv,
                ),
                "LV": (
                    rescale_overlapping_simple_returns(r_all, var_full, var_lv),
                    var_lv,
                ),
            }
            if not np.isfinite(var_hv) or var_hv <= 0:
                print(
                    f"warning ttm={ttm}: HV variance invalid (n_HV small?); "
                    "HV P uses unscaled full-sample returns",
                    file=sys.stderr,
                )
                regimes["HV"] = (r_all, var_full)
            if not np.isfinite(var_lv) or var_lv <= 0:
                print(
                    f"warning ttm={ttm}: LV variance invalid; LV P uses unscaled full-sample returns",
                    file=sys.stderr,
                )
                regimes["LV"] = (r_all, var_full)

        grid = _GRID_FULL
        ttm_root = ensure_results_dir(ttm, robust=args.robust)
        excel_dir = ttm_root / ETH_P_DENSITY_EXCEL_SUBDIR
        excel_dir.mkdir(parents=True, exist_ok=True)
        csv_dir: Optional[Path] = excel_dir if args.write_csv else None

        engine = _excel_engine()

        epdf_grid_fn: Callable[[np.ndarray, np.ndarray, int], np.ndarray] = (
            epdf_on_grid_btc_poly_gev if args.method == "btc_poly_gev" else epdf_on_grid_btc_poly
        )

        wrote: List[str] = []
        for label, (r_samp, _vk) in regimes.items():
            if r_samp.size < 20:
                print(f"skip ttm={ttm} regime={label}: too few returns", file=sys.stderr)
                continue
            try:
                if args.method == "kde":
                    f_p = epdf_on_grid_kde(r_samp, grid)
                    xlsx_k = excel_dir / f"P_KDE_{label}_ttm{ttm}day.xlsx"
                    pd.DataFrame({"Returns": grid, "P_KDE": f_p}).to_excel(
                        xlsx_k, index=False, engine=engine
                    )
                    wrote.append(str(xlsx_k.relative_to(ttm_root)))
                else:
                    xlsx_p = excel_dir / f"P_ePDF_{label}_ttm{ttm}day.xlsx"
                    df_x = build_p_epdf_excel_table(
                        grid,
                        r_samp,
                        n_bin_min=args.excel_nb_min,
                        n_bin_max=args.excel_nb_max,
                        epdf_grid_fn=epdf_grid_fn,
                    )
                    df_x.to_excel(xlsx_p, index=False, engine=engine)
                    wrote.append(str(xlsx_p.relative_to(ttm_root)))
                    if args.print_gev_diagnostics:
                        xf, yf = histogram_poly_pdf_btc(r_samp, args.excel_nb_min)
                        _, _, det_gev = gev_tail_combine(
                            yf, xf, raw_returns=r_samp
                        )
                        meta_l = det_gev.get("gev_opt_meta_left") or {}
                        print(
                            "GEV_DIAG "
                            + json.dumps(
                                {
                                    "ttm": ttm,
                                    "regime": label,
                                    "n_bin": args.excel_nb_min,
                                    "solution_left": det_gev.get("solution_left"),
                                    "solution_right": det_gev.get("solution_right"),
                                    "btc_gev_conditions_pre_monotone": det_gev.get(
                                        "btc_gev_conditions_pre_monotone"
                                    ),
                                    "left_gev_diagnostic": det_gev.get("left_gev_diagnostic"),
                                    "gev_left_max_abs_eq": meta_l.get("max_abs_eq"),
                                    "gev_left_min_ineq": meta_l.get("min_ineq"),
                                    "gev_left_method": meta_l.get("primary_method"),
                                    "gev_right_max_abs_eq": (
                                        det_gev.get("gev_opt_meta_right") or {}
                                    ).get("max_abs_eq"),
                                    "gev_right_min_ineq": (
                                        det_gev.get("gev_opt_meta_right") or {}
                                    ).get("min_ineq"),
                                },
                                default=str,
                            ),
                            flush=True,
                        )
            except Exception as e:
                print(f"ttm={ttm} regime={label} output failed: {e}", file=sys.stderr)
                continue

            if args.write_csv and csv_dir is not None:
                try:
                    if args.method == "kde":
                        f_c = f_p
                    elif args.method == "btc_poly_gev":
                        f_c = epdf_on_grid_btc_poly_gev(r_samp, grid, args.n_bin)
                    else:
                        f_c = epdf_on_grid_btc_poly(r_samp, grid, args.n_bin)
                    nb_tag = f"_nb{args.n_bin}" if args.method in ("btc_poly", "btc_poly_gev") else ""
                    p_csv = csv_dir / f"P_empirical_{args.method}{nb_tag}_{label}_ttm{ttm}day.csv"
                    pd.DataFrame({"m": grid, "p_density": f_c}).to_csv(p_csv, index=False)
                    wrote.append(str(p_csv.relative_to(ttm_root)))
                except Exception as e:
                    print(f"ttm={ttm} regime={label} csv failed: {e}", file=sys.stderr)

        if wrote:
            print(
                f"ttm={ttm} var_full(ann, cluster-union starts)={var_full:.6g} "
                f"var_hv(ann)={var_hv:.6g} var_lv(ann)={var_lv:.6g} -> {ttm_root}"
            )
            for w in wrote:
                print(f"  {w}")

    print(
        "done. BTC: S6_1_RiskPremia_BP_write_QP_OA_*; HV/LV P default = full-sample overlap + "
        "variance rescale (c0/c1); optional --hv-lv-via-subset = plan §1.3.1 cluster-conditioned samples."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
