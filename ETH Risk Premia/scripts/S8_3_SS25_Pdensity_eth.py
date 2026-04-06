#!/usr/bin/env python3
"""
**``scripts/S8_3_SS25_Pdensity_eth.py``** — **§1.3.1** **S8_3**（**SS25 条件 P 密度**，可选）。

**估计**：对照 Schreindorfer & Sichert (2025) 复现包中 **块自助** 脚本所嵌入的同一套 **MLE + ``LL``**，
**不** import BTC 路径；按 TTM 在元数据中标注只读参照：

- **TTM 9** → ``data/bootstrap_BTC_ttm9.m``
- **TTM 27** → ``data/bootstrap.m``
- **TTM 45** → ``data/bootstrap_BTC_ttm45.m``

（上述脚本在 **估计** 段均调用 ``estimate_bench`` → ``LL`` / ``LL_fixed_b``；差别主要在预存自助结果文件名与 TTM 设定。）

**``LL`` 中归一化 P 密度**（与 ``data/LL.m`` 一致）::

  ``fP_raw = exp(ln_fQ - coef * (r_vec^j))``, ``mass = sum_G fP_raw * del``, ``fP_norm = fP_raw / mass``

**数据**：``Q_matrix`` 行 = 简单收益格点 **m**（与 ``function._GRID_FULL`` 一致）；**r_vec = 1 + m**（毛收益 **R**）。
样本日与 **S8_0** 相同：重叠简单收益 ``(S_{t+τ}-S_t)/S_t``，**OA / HV / LV** 与 ``S8_0_prepare_Pdensity.py`` 一致。

**输出**::

  ``results/ttm_XX/P_density/SS25/P_SS25_{OA|HV|LV}_ttm{τ}day.csv`` — 列 **``m``**, **``p_density``**
  （全样本点估计）；若 **``--bootstrap-reps > 0``**，另含 **``p_density_boot_p05/p50/p95``**（块自助下重估 **MLE+LL** 后对时间平均密度的分位数，索引生成同 ``bootstrap_*.m``）。

``--method kde`` 为 **非论文核** 备用；**不做** SS25 自助。
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
for _p in (_ROOT, _SCRIPTS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from function import (  # noqa: E402
    ETH_DAILY_CSV,
    ETH_P_DENSITY_ROOT,
    PRIMARY_TTMS,
    _GRID_FULL,
    clustering_multivariate_run_dir,
    ensure_results_dir,
    load_eth_daily,
)
from S8_0_prepare_Pdensity import (  # noqa: E402
    cluster_start_masks,
    default_q_matrix_path,
    load_common_dates_cluster,
    oa_hv_lv_variance_scales,
    overlapping_simple_returns_with_start_dates,
    rescale_overlapping_simple_returns,
    _read_q_matrix_header_dates,
)


def ss25_bootstrap_reference_name(ttm: int) -> str:
    """只读：与 BTC ``schreindorfer_sichert_2025_replication_code/data/`` 内文件名对应。"""
    if ttm == 9:
        return "bootstrap_BTC_ttm9.m"
    if ttm == 45:
        return "bootstrap_BTC_ttm45.m"
    if ttm == 27:
        return "bootstrap.m"
    return "bootstrap.m (fallback when ttm not 9/27/45)"


def ss25_default_block_length(ttm: int) -> int:
    """与 BTC main 一致：TTM 9 / 27 / 45 常用块长 = 持有期（天）。"""
    if ttm in (9, 27, 45):
        return int(ttm)
    return int(max(5, min(ttm, 45)))


def _build_rand_U_blocks(T: int, block: int, rng: np.random.Generator, reps: int) -> np.ndarray:
    """``numblock × reps``，与 ``bootstrap*.m`` 中 ``rand_U(1:numblock,1:reps)`` 同构。"""
    if T <= block:
        raise ValueError(f"block bootstrap requires T > block; got T={T}, block={block}")
    numblock = int(np.ceil(T / block))
    return rng.random((numblock, reps))


def _obs_indices_one_rep(rand_U_col: np.ndarray, T: int, block: int) -> np.ndarray:
    """单列 ``rand_U(:,b)`` → 拼接块行标（0-based），与 MATLAB ``round(u*(T-block+1)-0.5)+(1:block)`` 一致。"""
    chunks: List[np.ndarray] = []
    for i in range(len(rand_U_col)):
        u = float(rand_U_col[i])
        s_mat = int(np.round(u * (T - block + 1) - 0.5)) + 1
        s_py = int(np.clip(s_mat - 1, 0, T - block))
        chunks.append(np.arange(s_py, s_py + block, dtype=np.int64))
    return np.concatenate(chunks)


def _interp_p_to_grid_m(f_p: np.ndarray, m_grid: np.ndarray, grid_m: np.ndarray) -> np.ndarray:
    idx = np.argsort(m_grid)
    return np.interp(
        grid_m,
        m_grid[idx],
        f_p[idx],
        left=float(f_p[idx[0]]),
        right=float(f_p[idx[-1]]),
    )


def mean_p_density_on_grid(
    theta: np.ndarray,
    Np: int,
    ln_fQ: np.ndarray,
    r30_R: np.ndarray,
    ln_sig_t: np.ndarray,
    r_vec: np.ndarray,
    ln_fQ_t: np.ndarray,
    del_r: float,
    m_grid: np.ndarray,
    grid_m: np.ndarray,
) -> np.ndarray:
    """时间平均 ``fP_norm``，插值到 ``grid_m``，并对 ``r_vec`` _TRAPZ 归一。"""
    _, fp_n = _ll_and_fp(
        theta, Np, ln_fQ, r30_R, ln_sig_t, r_vec, ln_fQ_t, del_r, need_fp=True
    )
    assert fp_n is not None
    f_p = np.mean(fp_n, axis=0)
    f_p = np.maximum(f_p, 0.0)
    a_trap = np.trapz(f_p, r_vec)
    if a_trap > 0:
        f_p = f_p / a_trap
    return _interp_p_to_grid_m(f_p, m_grid, grid_m)


def _ll_and_fp(
    theta: np.ndarray,
    N: int,
    ln_fQ: np.ndarray,
    r30_R: np.ndarray,
    ln_sig_t: np.ndarray,
    r_vec: np.ndarray,
    ln_fQ_t: np.ndarray,
    del_r: float,
    *,
    need_fp: bool,
) -> Tuple[float, Optional[np.ndarray]]:
    """
    ``data/LL.m`` / ``LL_fixed_b.m`` 的 NumPy 版；``r30_R``、``r_vec`` 均为 **毛收益 R**。
    返回 mean log 似然；若 need_fp，返回 fP_norm (T, G)。
    """
    b = float(theta[0])
    a = np.asarray(theta[1 : N + 1], dtype=float)
    t_n, g_n = ln_fQ.shape
    j = np.arange(1, N + 1, dtype=float)
    if abs(b) < 1e-12:
        scale = np.ones((t_n, N), dtype=float)
    else:
        scale = np.exp(ln_sig_t[:, None] * j[None, :] * b)
    coef = a[None, :] / scale
    r_pow = r_vec[:, None] ** j[None, :]
    linear = coef @ r_pow.T
    f_raw = np.exp(ln_fQ - linear)
    mass = np.sum(f_raw, axis=1) * float(del_r)
    ln_mass = np.log(np.maximum(mass, 1e-300))
    r30_pow = r30_R[:, None] ** j[None, :]
    ln_m_real = np.sum(r30_pow * coef, axis=1)
    terms = ln_fQ_t - ln_m_real - ln_mass
    log_lik = float(np.mean(terms))
    if not need_fp:
        return log_lik, None
    fp = f_raw / np.maximum(mass[:, None], 1e-300)
    return log_lik, fp


def _neg_ll(theta: np.ndarray, N: int, *args: Any) -> float:
    ll, _ = _ll_and_fp(theta, N, *args, need_fp=False)
    return -ll


def _neg_ll_fixed_b(
    a: np.ndarray,
    b_fix: float,
    N: int,
    ln_fQ: np.ndarray,
    r30_R: np.ndarray,
    ln_sig_t: np.ndarray,
    r_vec: np.ndarray,
    ln_fQ_t: np.ndarray,
    del_r: float,
) -> float:
    theta = np.concatenate([[b_fix], np.asarray(a, dtype=float).ravel()])
    return _neg_ll(theta, N, ln_fQ, r30_R, ln_sig_t, r_vec, ln_fQ_t, del_r)


def _fminunc_like(
    fun,
    x0: np.ndarray,
) -> Tuple[np.ndarray, float]:
    from scipy.optimize import minimize

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        res = minimize(
            fun,
            x0,
            method="L-BFGS-B",
            options={"maxiter": 5000, "ftol": 1e-10, "gtol": 1e-12},
        )
    x = np.asarray(res.x, dtype=float)
    return x, float(res.fun)


def estimate_bench_eth(
    N: int,
    ln_fQ: np.ndarray,
    r30_R: np.ndarray,
    ln_sig_t: np.ndarray,
    r_vec: np.ndarray,
    ln_fQ_t: np.ndarray,
    del_r: float,
    b_vec: np.ndarray,
    theta_0_mat: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    对应 ``data/estimate_bench.m``：返回 ``theta_all`` 第一行为 **无约束** 解 (1, N+1)；
    若 ``len(b_vec)>0``，后续行为 **b 固定** 的解（与 MATLAB 行序一致：无约束在第 1 行）。
    """
    from scipy.optimize import minimize

    # --- b restricted (MATLAB bb loop → theta_all rows 2..) ---
    theta_rest = []
    for bb in range(len(b_vec)):
        b0 = float(b_vec[bb])
        a0 = np.ones(N, dtype=float) * 1e-5
        x_a, _ = _fminunc_like(
            lambda a: _neg_ll_fixed_b(a, b0, N, ln_fQ, r30_R, ln_sig_t, r_vec, ln_fQ_t, del_r),
            a0,
        )
        theta_rest.append(np.concatenate([[b0], x_a]))

    # --- unrestricted starting grid (MATLAB theta_0_mat) ---
    if theta_0_mat is None:
        theta_0_mat = np.array(
            [
                [1.001] + [-0.001] * N,
                [1.001] + [0.001] * N,
                [1.501] + [-0.001] * N,
                [1.501] + [0.001] * N,
                [-1.001] + [-0.001] * N,
                [-1.001] + [0.001] * N,
            ],
            dtype=float,
        )
        theta_0_mat = theta_0_mat[:, : N + 1]

    best_x: Optional[np.ndarray] = None
    best_obj = 1e300
    for i in range(theta_0_mat.shape[0]):
        x0 = np.asarray(theta_0_mat[i, : N + 1], dtype=float)
        try:

            def obj(th: np.ndarray) -> float:
                return _neg_ll(th, N, ln_fQ, r30_R, ln_sig_t, r_vec, ln_fQ_t, del_r)

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                res = minimize(
                    obj,
                    x0,
                    method="L-BFGS-B",
                    options={"maxiter": 5000, "ftol": 1e-10, "gtol": 1e-12},
                )
            if res.fun < best_obj:
                best_obj = float(res.fun)
                best_x = np.asarray(res.x, dtype=float)
        except Exception:
            continue

    if best_x is None:
        raise RuntimeError(f"fminunc-like: all starts failed for N={N}")

    theta_unres = best_x

    # optional: refine from b=1 restricted if b_vec contains 1 (MATLAB L88-95)
    if len(b_vec) > 0 and np.any(np.isclose(b_vec, 1.0)):
        ix = int(np.where(np.isclose(b_vec, 1.0))[0][0])
        theta_0_ref = np.concatenate([[1.001], theta_rest[ix][1:]])
        try:

            def obj2(th: np.ndarray) -> float:
                return _neg_ll(th, N, ln_fQ, r30_R, ln_sig_t, r_vec, ln_fQ_t, del_r)

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                res2 = minimize(
                    obj2,
                    theta_0_ref,
                    method="L-BFGS-B",
                    options={"maxiter": 5000, "ftol": 1e-10, "gtol": 1e-12},
                )
            if res2.fun < best_obj:
                theta_unres = np.asarray(res2.x, dtype=float)
        except Exception:
            pass

    out: List[np.ndarray] = [theta_unres]
    out.extend(theta_rest)
    theta_all = np.vstack(out)
    return theta_unres, theta_all


def estimate_ss25_theta_sequence(
    orders: Sequence[int],
    ln_fQ: np.ndarray,
    r30_R: np.ndarray,
    ln_sig_t: np.ndarray,
    r_vec: np.ndarray,
    ln_fQ_t: np.ndarray,
    del_r: float,
    *,
    warm_starts: Optional[Dict[int, np.ndarray]] = None,
) -> Dict[int, np.ndarray]:
    """
    对照 ``bootstrap*_BTC*.m`` 中对 ``N(i)=1,2,...`` 逐阶估计的写法；此处返回每阶 **无约束** ``theta``。
    ``warm_starts``：全样本估计值，用作自助样本上的 **首选起点**（与 MATLAB 用 ``theta_0`` 热启动一致）。
    """
    thetas: Dict[int, np.ndarray] = {}
    theta_prev: Optional[np.ndarray] = None
    for N in orders:
        if N == 2:
            b_vec = np.array([0.0], dtype=float)
            theta_0_mat = np.array(
                [
                    [1.001, -0.001, 0.001],
                    [1.001, 0.001, -0.001],
                    [-1.001, -0.001, 0.001],
                    [-1.001, 0.001, -0.001],
                ],
                dtype=float,
            )
            if warm_starts is not None and N in warm_starts:
                w = np.asarray(warm_starts[N], dtype=float).reshape(1, N + 1)
                theta_0_mat = np.vstack([w, theta_0_mat])
        else:
            b_vec = np.array([], dtype=float)
            if theta_prev is not None:
                pad = np.zeros(N + 1)
                pad[: len(theta_prev)] = theta_prev
                pad[len(theta_prev)] = 1e-5
                pad2 = pad.copy()
                pad2[len(theta_prev)] = -1e-5
                theta_0_mat = np.vstack([pad, pad2])
            else:
                theta_0_mat = None
            if warm_starts is not None and N in warm_starts:
                w = np.asarray(warm_starts[N], dtype=float).reshape(1, N + 1)
                if theta_0_mat is None:
                    theta_0_mat = w
                else:
                    theta_0_mat = np.vstack([w, theta_0_mat])
        theta_u, _ = estimate_bench_eth(
            N, ln_fQ, r30_R, ln_sig_t, r_vec, ln_fQ_t, del_r, b_vec, theta_0_mat
        )
        thetas[N] = theta_u
        theta_prev = theta_u
    return thetas


def run_block_bootstrap_p_density(
    *,
    reps: int,
    block: int,
    seed: int,
    ln_fQ: np.ndarray,
    r30_R: np.ndarray,
    ln_sig_t: np.ndarray,
    r_vec: np.ndarray,
    ln_fQ_t: np.ndarray,
    del_r: float,
    m_grid: np.ndarray,
    grid_m: np.ndarray,
    orders: Sequence[int],
    Np: int,
    warm_thetas: Dict[int, np.ndarray],
) -> Tuple[np.ndarray, int]:
    """
    块自助 ``reps`` 次；每次重估 ``estimate_ss25_theta_sequence``，返回 ``(reps, len(grid_m))``，
    行为失败行填 **NaN**；返回 **有效** 次数。
    """
    rng = np.random.default_rng(seed)
    T = ln_fQ.shape[0]
    rand_U = _build_rand_U_blocks(T, block, rng, reps)
    curves: List[np.ndarray] = []
    n_ok = 0
    for b in range(reps):
        obs = _obs_indices_one_rep(rand_U[:, b], T, block)
        try:
            thetas_b = estimate_ss25_theta_sequence(
                orders,
                ln_fQ[obs],
                r30_R[obs],
                ln_sig_t[obs],
                r_vec,
                ln_fQ_t[obs],
                del_r,
                warm_starts=warm_thetas,
            )
            th = thetas_b[Np]
            f_ord = mean_p_density_on_grid(
                th,
                Np,
                ln_fQ[obs],
                r30_R[obs],
                ln_sig_t[obs],
                r_vec,
                ln_fQ_t[obs],
                del_r,
                m_grid,
                grid_m,
            )
            curves.append(f_ord)
            n_ok += 1
        except Exception:
            curves.append(np.full(grid_m.shape[0], np.nan, dtype=float))
    return np.vstack(curves), n_ok


def load_q_panel_r_vec_m(
    q_path: Path,
) -> Tuple[pd.DataFrame, np.ndarray, np.ndarray, List[str]]:
    """读 Q_matrix：索引 m，列日期；``r_vec=1+m``。"""
    df = pd.read_csv(q_path, index_col=0)
    m_grid = pd.to_numeric(df.index, errors="coerce").to_numpy(dtype=float)
    if np.any(np.isnan(m_grid)):
        raise ValueError(f"non-numeric Q_matrix index: {q_path}")
    r_vec = 1.0 + m_grid
    if r_vec.size < 3:
        raise ValueError("Q grid too small")
    del_r = float(np.nanmean(np.diff(np.sort(r_vec))))
    if not np.isfinite(del_r) or del_r <= 0:
        del_r = 0.01
    dates_norm = []
    cols_out = []
    for c in df.columns:
        d = pd.to_datetime(c, errors="coerce")
        if pd.isna(d):
            continue
        dates_norm.append(d.normalize())
        cols_out.append(c)
    df2 = df[cols_out].apply(pd.to_numeric, errors="coerce")
    return df2, r_vec, m_grid, [str(c) for c in cols_out]


def align_q_R_ln_sig(
    q_df: pd.DataFrame,
    r_vec: np.ndarray,
    m_grid: np.ndarray,
    dates_cols: List[str],
    eth: pd.DataFrame,
    ttm: int,
    *,
    sig_window: int,
) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    """内连接 Q 列日历与重叠毛收益 R；构造 ln_fQ、ln_fQ_t、ln_sig_t。"""
    r_simp, starts = overlapping_simple_returns_with_start_dates(eth, ttm)
    ret = pd.DataFrame(
        {"date": pd.DatetimeIndex(starts).normalize(), "R": 1.0 + r_simp.astype(float)}
    )
    ret = ret[np.isfinite(ret["R"].to_numpy())]
    ret = ret.drop_duplicates(subset=["date"], keep="last")

    cols_t = []
    for c in dates_cols:
        d = pd.to_datetime(c, errors="coerce")
        if pd.isna(d):
            continue
        cols_t.append((d.normalize(), c))

    eth_s = eth.sort_values("date").copy()
    eth_s["date"] = pd.to_datetime(eth_s["date"], errors="coerce").dt.normalize()
    eth_s["logp"] = np.log(eth_s["price"].astype(float))
    eth_s["lr"] = eth_s["logp"].diff()
    eth_s["sig_d"] = eth_s["lr"].rolling(sig_window, min_periods=max(5, sig_window // 3)).std()
    d2sig = dict(zip(eth_s["date"], eth_s["sig_d"].to_numpy()))

    d_list: List[Any] = []
    R_list: List[float] = []
    q_blocks: List[np.ndarray] = []
    for dnorm, c in cols_t:
        hit = ret.loc[ret["date"] == dnorm, "R"]
        if hit.empty:
            continue
        r_gross = float(hit.iloc[-1])
        qcol = pd.to_numeric(q_df[c], errors="coerce").to_numpy(dtype=float)
        if np.any(~np.isfinite(qcol)) or np.all(qcol <= 0):
            continue
        sig = d2sig.get(dnorm, np.nan)
        if not (np.isfinite(sig) and sig > 0):
            continue
        d_list.append(dnorm)
        R_list.append(float(np.clip(r_gross, r_vec.min(), r_vec.max())))
        q_blocks.append(qcol)

    if len(R_list) < 30:
        return None

    qm = np.vstack(q_blocks)
    R_ar = np.array(R_list, dtype=float)
    ln_fQ = np.log(np.maximum(qm, 1e-300))
    ln_fQ_t = np.array(
        [
            float(
                np.interp(
                    np.clip(R_ar[i], r_vec.min(), r_vec.max()),
                    r_vec,
                    ln_fQ[i],
                    left=ln_fQ[i, 0],
                    right=ln_fQ[i, -1],
                )
            )
            for i in range(len(R_ar))
        ]
    )
    ln_sig = np.log(
        np.array([d2sig[d] for d in d_list], dtype=float)
    )
    if np.min(ln_sig) >= 0:
        ln_sig = np.log(np.exp(ln_sig) / (1.0 + np.exp(ln_sig)))  # should not trigger
    return ln_fQ, R_ar, ln_fQ_t, ln_sig, m_grid


def align_q_R_ln_sig_masked(
    q_df: pd.DataFrame,
    r_vec: np.ndarray,
    m_grid: np.ndarray,
    dates_cols: List[str],
    eth: pd.DataFrame,
    ttm: int,
    *,
    sig_window: int,
    regime_start_dates: pd.DatetimeIndex,
) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    """仅保留起点日落在 ``regime_start_dates`` 的观测。"""
    r_simp, starts = overlapping_simple_returns_with_start_dates(eth, ttm)
    ret = pd.DataFrame(
        {"date": pd.DatetimeIndex(starts).normalize(), "R": 1.0 + r_simp.astype(float)}
    )
    ret = ret[np.isfinite(ret["R"].to_numpy())]
    ret = ret.drop_duplicates(subset=["date"], keep="last")
    reg_set = set(pd.DatetimeIndex(regime_start_dates).normalize())

    cols_t = []
    for c in dates_cols:
        d = pd.to_datetime(c, errors="coerce")
        if pd.isna(d):
            continue
        cols_t.append((d.normalize(), c))

    eth_s = eth.sort_values("date").copy()
    eth_s["date"] = pd.to_datetime(eth_s["date"], errors="coerce").dt.normalize()
    eth_s["logp"] = np.log(eth_s["price"].astype(float))
    eth_s["lr"] = eth_s["logp"].diff()
    eth_s["sig_d"] = eth_s["lr"].rolling(sig_window, min_periods=max(5, sig_window // 3)).std()
    d2sig = dict(zip(eth_s["date"], eth_s["sig_d"].to_numpy()))

    d_list: List[Any] = []
    R_list: List[float] = []
    q_blocks: List[np.ndarray] = []
    for dnorm, c in cols_t:
        if dnorm not in reg_set:
            continue
        hit = ret.loc[ret["date"] == dnorm, "R"]
        if hit.empty:
            continue
        r_gross = float(hit.iloc[-1])
        qcol = pd.to_numeric(q_df[c], errors="coerce").to_numpy(dtype=float)
        if np.any(~np.isfinite(qcol)) or np.all(qcol <= 0):
            continue
        sig = d2sig.get(dnorm, np.nan)
        if not (np.isfinite(sig) and sig > 0):
            continue
        d_list.append(dnorm)
        R_list.append(float(np.clip(r_gross, r_vec.min(), r_vec.max())))
        q_blocks.append(qcol)

    if len(R_list) < 30:
        return None
    qm = np.vstack(q_blocks)
    R_ar = np.array(R_list, dtype=float)
    ln_fQ = np.log(np.maximum(qm, 1e-300))
    ln_fQ_t = np.array(
        [
            float(
                np.interp(
                    np.clip(R_ar[i], r_vec.min(), r_vec.max()),
                    r_vec,
                    ln_fQ[i],
                    left=ln_fQ[i, 0],
                    right=ln_fQ[i, -1],
                )
            )
            for i in range(len(R_ar))
        ]
    )
    ln_sig = np.log(np.array([d2sig[d] for d in d_list], dtype=float))
    return ln_fQ, R_ar, ln_fQ_t, ln_sig, m_grid


def ss25_rescale_R(R: np.ndarray, var_full: float, var_k: float) -> np.ndarray:
    """HV/LV 方差缩放：简单收益缩放 → 毛收益 ``R' = 1 + (R-1)*sqrt(var_k/var_full)``。"""
    if not np.isfinite(var_full) or var_full <= 0 or not np.isfinite(var_k) or var_k <= 0:
        return R
    s = np.sqrt(float(var_k) / float(var_full))
    return 1.0 + (R - 1.0) * s


def ss25_kde_on_grid(
    samples_m: np.ndarray,
    grid_m: np.ndarray,
    *,
    bw_method: str,
    bw_factor: float,
) -> np.ndarray:
    from scipy.stats import gaussian_kde

    d = np.asarray(samples_m, dtype=float)
    d = d[np.isfinite(d)]
    if d.size < 5:
        raise ValueError("KDE needs at least 5 finite returns")
    kde = gaussian_kde(d, bw_method=bw_method)
    if bw_factor != 1.0:
        kde.set_bandwidth(kde.factor * float(bw_factor))
    f = kde.evaluate(np.asarray(grid_m, dtype=float))
    f = np.maximum(f, 0.0)
    g = np.asarray(grid_m, dtype=float)
    a = np.trapz(f, g)
    if a > 0:
        f = f / a
    return f


def main() -> int:
    ap = argparse.ArgumentParser(description="S8_3 SS25 P density — P_density/SS25, see SS25.md")
    ap.add_argument("--ttm", type=int, nargs="+", default=list(PRIMARY_TTMS), help="TTM days")
    ap.add_argument("--q-matrix", type=Path, default=None, help="Q_matrix CSV")
    ap.add_argument("--use-d15", action="store_true", help="Q_matrix_*_d15.csv")
    ap.add_argument("--spot-csv", type=Path, default=None, help="ETH daily")
    ap.add_argument("--cluster-csv", type=Path, default=None, help="S7 common_dates_cluster.csv")
    ap.add_argument("--robust", action="store_true", help="results/results_robust/ttm_XX/")
    ap.add_argument(
        "--method",
        choices=("ss25", "kde"),
        default="ss25",
        help="ss25: MLE+LL (paper); kde: empirical KDE on m (backup)",
    )
    ap.add_argument("--poly-orders", type=int, nargs="+", default=[1, 2], help="SS25 多项式阶，默认 1 2")
    ap.add_argument(
        "--p-report-order",
        type=int,
        default=2,
        help="写出 P 密度所用 N（须已包含在 --poly-orders）",
    )
    ap.add_argument("--sig-window", type=int, default=21, help="ln_sig：日对数收益 rolling std 窗口")
    ap.add_argument("--bw-method", choices=("scott", "silverman"), default="scott")
    ap.add_argument("--bw-factor", type=float, default=1.0)
    ap.add_argument("--hv-lv-via-subset", action="store_true")
    ap.add_argument("--ddof", type=int, default=1)
    ap.add_argument(
        "--bootstrap-reps",
        type=int,
        default=0,
        help=">0：块自助次数（与 bootstrap_*.m 同型重抽样+重估）；0=仅点估计。仅 --method ss25。",
    )
    ap.add_argument(
        "--bootstrap-block",
        type=int,
        default=None,
        help="块长；默认与 TTM 一致（9/27/45→9/27/45，否则 min(ttm,45) 下界 5）",
    )
    ap.add_argument("--bootstrap-seed", type=int, default=42, help="numpy 随机种子")
    args = ap.parse_args()

    if args.p_report_order not in args.poly_orders:
        raise SystemExit("--p-report-order must be one of --poly-orders")
    if args.bootstrap_reps > 0 and args.method != "ss25":
        raise SystemExit("--bootstrap-reps 仅支持 --method ss25（KDE 不做 SS25 自助）")

    cluster_path = args.cluster_csv or (clustering_multivariate_run_dir() / "common_dates_cluster.csv")
    if not cluster_path.is_file():
        raise SystemExit(f"missing cluster file (run S7 first): {cluster_path}")
    cluster_df = load_common_dates_cluster(cluster_path)

    spot_path = args.spot_csv or ETH_DAILY_CSV
    eth = load_eth_daily(spot_path)

    for ttm in args.ttm:
        q_path = args.q_matrix if args.q_matrix is not None else default_q_matrix_path(ttm, use_d15=args.use_d15)
        run_entry: Dict[str, Any] = {"csv": [], "errors": []}

        if not q_path.is_file():
            print(f"skip ttm={ttm}: missing Q_matrix {q_path}", file=sys.stderr)
            continue

        dates_s = _read_q_matrix_header_dates(q_path)
        if not dates_s:
            print(f"skip ttm={ttm}: empty Q header {q_path}", file=sys.stderr)
            continue

        try:
            q_df, r_vec, m_grid, date_cols = load_q_panel_r_vec_m(q_path)
        except Exception as e:
            print(f"skip ttm={ttm}: load Q failed: {e}", file=sys.stderr)
            continue

        if not np.allclose(np.sort(m_grid), np.sort(_GRID_FULL), rtol=0, atol=1e-6):
            print(f"warning ttm={ttm}: Q m grid may differ from _GRID_FULL", file=sys.stderr)

        r_all, start_dates = overlapping_simple_returns_with_start_dates(eth, ttm)
        if r_all.size < 20:
            print(f"skip ttm={ttm}: too few overlapping returns", file=sys.stderr)
            continue

        scales = oa_hv_lv_variance_scales(
            r_all, start_dates, cluster_df, ttm=ttm, ddof=args.ddof
        )
        var_full, var_hv, var_lv = scales["var_full"], scales["var_hv"], scales["var_lv"]
        if not np.isfinite(var_full) or var_full <= 0:
            print(f"skip ttm={ttm}: invalid var_full", file=sys.stderr)
            continue

        mask_hv, mask_lv = cluster_start_masks(start_dates, cluster_df)
        hv_dates = pd.DatetimeIndex(start_dates[mask_hv]).normalize()
        lv_dates = pd.DatetimeIndex(start_dates[mask_lv]).normalize()

        if args.hv_lv_via_subset:
            regimes: Dict[str, Tuple[str, Any]] = {
                "OA": ("all", None),
                "HV": ("subset", hv_dates),
                "LV": ("subset", lv_dates),
            }
        else:
            regimes = {
                "OA": ("all", None),
                "HV": ("scale", var_hv),
                "LV": ("scale", var_lv),
            }

        grid_m = _GRID_FULL
        boot_block = args.bootstrap_block if args.bootstrap_block is not None else ss25_default_block_length(ttm)
        ttm_root = ensure_results_dir(ttm, robust=args.robust)
        out_dir = ttm_root / ETH_P_DENSITY_ROOT / "SS25"
        out_dir.mkdir(parents=True, exist_ok=True)
        bootstrap_ok_by_regime: Dict[str, int] = {}

        for label, (mode, aux) in regimes.items():
            try:
                if args.method == "kde":
                    if mode == "subset" and aux is not None:
                        r_reg = r_all[mask_hv] if label == "HV" else (r_all[mask_lv] if label == "LV" else r_all)
                        if label == "OA":
                            r_reg = r_all
                    elif mode == "scale" and aux is not None and label != "OA":
                        vk = float(aux)
                        r_reg = (r_all * np.sqrt(vk / var_full)) if np.isfinite(vk) and vk > 0 else r_all
                    else:
                        r_reg = r_all
                    if r_reg.size < 20:
                        raise ValueError("too few returns for KDE")
                    f_p = ss25_kde_on_grid(
                        r_reg, grid_m, bw_method=args.bw_method, bw_factor=args.bw_factor
                    )
                    f_ord = f_p
                    rowdict = {"m": grid_m, "p_density": f_ord}
                else:
                    if mode == "subset" and aux is not None:
                        aligned = align_q_R_ln_sig_masked(
                            q_df,
                            r_vec,
                            m_grid,
                            date_cols,
                            eth,
                            ttm,
                            sig_window=args.sig_window,
                            regime_start_dates=aux,
                        )
                    else:
                        aligned = align_q_R_ln_sig(
                            q_df,
                            r_vec,
                            m_grid,
                            date_cols,
                            eth,
                            ttm,
                            sig_window=args.sig_window,
                        )
                        if aligned is not None and mode == "scale" and aux is not None and label != "OA":
                            ln_fQ, R_ar, ln_fQ_t, ln_sig, _mg = aligned
                            vk = float(aux)
                            R_ar = ss25_rescale_R(R_ar, var_full, vk) if np.isfinite(vk) and vk > 0 else R_ar
                            ln_fQ_t = np.array(
                                [
                                    float(
                                        np.interp(
                                            np.clip(R_ar[i], r_vec.min(), r_vec.max()),
                                            r_vec,
                                            ln_fQ[i],
                                            left=ln_fQ[i, 0],
                                            right=ln_fQ[i, -1],
                                        )
                                    )
                                    for i in range(len(R_ar))
                                ]
                            )
                            aligned = (ln_fQ, R_ar, ln_fQ_t, ln_sig, _mg)

                    if aligned is None:
                        raise ValueError("insufficient aligned Q–R–sig rows")
                    ln_fQ, R_ar, ln_fQ_t, ln_sig, _mg = aligned

                    del_r = float(np.mean(np.diff(np.sort(r_vec))))
                    orders = sorted(set(int(x) for x in args.poly_orders))
                    thetas = estimate_ss25_theta_sequence(
                        orders, ln_fQ, R_ar, ln_sig, r_vec, ln_fQ_t, del_r, warm_starts=None
                    )
                    Np = args.p_report_order
                    th = thetas[Np]
                    f_ord = mean_p_density_on_grid(
                        th, Np, ln_fQ, R_ar, ln_sig, r_vec, ln_fQ_t, del_r, m_grid, grid_m
                    )
                    rowdict: Dict[str, Any] = {"m": grid_m, "p_density": f_ord}
                    if args.bootstrap_reps > 0:
                        boot_mat, n_ok = run_block_bootstrap_p_density(
                            reps=args.bootstrap_reps,
                            block=boot_block,
                            seed=args.bootstrap_seed,
                            ln_fQ=ln_fQ,
                            r30_R=R_ar,
                            ln_sig_t=ln_sig,
                            r_vec=r_vec,
                            ln_fQ_t=ln_fQ_t,
                            del_r=del_r,
                            m_grid=m_grid,
                            grid_m=grid_m,
                            orders=orders,
                            Np=Np,
                            warm_thetas=thetas,
                        )
                        rowdict["p_density_boot_p05"] = np.nanpercentile(boot_mat, 5, axis=0)
                        rowdict["p_density_boot_p50"] = np.nanpercentile(boot_mat, 50, axis=0)
                        rowdict["p_density_boot_p95"] = np.nanpercentile(boot_mat, 95, axis=0)
                        bootstrap_ok_by_regime[label] = int(n_ok)
                p_csv = out_dir / f"P_SS25_{label}_ttm{ttm}day.csv"
                out_df = pd.DataFrame({k: v for k, v in rowdict.items() if not k.startswith("_")})
                out_df.to_csv(p_csv, index=False)
                run_entry["csv"].append(str(p_csv.relative_to(ttm_root)))
                print(f"ttm={ttm} {label} -> {p_csv}")
            except Exception as e:
                run_entry["errors"].append(f"{label}: {e}")
                print(f"ttm={ttm} regime={label} failed: {e}", file=sys.stderr)

        meta_ttm: Dict[str, Any] = {
            "stage": "S8_3",
            "bootstrap_reference_readonly": ss25_bootstrap_reference_name(ttm),
            "bootstrap_note": (
                "With --bootstrap-reps>0: block resampling matches bootstrap_*.m; each rep re-runs MLE+LL. "
                "Point estimate always on full sample."
            ),
            "bootstrap_reps": int(args.bootstrap_reps),
            "bootstrap_block": int(boot_block),
            "bootstrap_seed": int(args.bootstrap_seed),
            "bootstrap_ok_by_regime": bootstrap_ok_by_regime,
            "method": args.method,
            "poly_orders": [int(x) for x in args.poly_orders],
            "p_report_order": int(args.p_report_order),
            "ttm": int(ttm),
            "sig_window": int(args.sig_window),
            "hv_lv_via_subset": bool(args.hv_lv_via_subset),
            "robust": bool(args.robust),
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "cluster_csv": str(cluster_path.resolve()),
            "spot_csv": str(Path(spot_path).resolve()),
            "q_matrix": str(q_path.resolve()),
            "output_dir": str(out_dir.relative_to(ttm_root)),
            "r_vec_definition": "1 + m (gross return), LL.m / estimate_bench.m",
            "var_full": float(var_full),
            "var_hv": float(var_hv),
            "var_lv": float(var_lv),
            "outputs_csv": run_entry["csv"],
            "errors": run_entry["errors"],
        }
        if args.method == "kde":
            meta_ttm["kde_bw_method"] = args.bw_method
            meta_ttm["kde_bw_factor"] = float(args.bw_factor)
        (out_dir / "s8_3_run_meta.json").write_text(
            json.dumps(meta_ttm, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    print(
        "done. …/P_density/SS25/: --method ss25 = LL/MLE; "
        "add --bootstrap-reps for block bootstrap like bootstrap_*.m."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
