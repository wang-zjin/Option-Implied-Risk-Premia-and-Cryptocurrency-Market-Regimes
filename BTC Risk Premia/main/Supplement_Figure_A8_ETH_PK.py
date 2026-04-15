#!/usr/bin/env python3
"""
S11_0：**Q / P / PK（ePDF）图** — 对齐 BTC ``S6_2_RiskPremia_BP_plot_QP_multivar_9_27_45.m``。**S11_1**（规划）：同版式，\(\hat p\) 来自 **S8_3** SS25，见 ``ETH_risk_premia_plan.md`` **§1.4.2**。
在收益网格上画 **\\hat{q}**（实线）、**\\hat{p}**（虚线）、**\\widehat{PK}=\\hat{q}/\\hat{p}**（点划线），
阴影带 ``[-0.6,-0.2]``、``[0.2,0.6]``；**OA 黑 / HV 蓝 / LV 红**。

**数据**：

- **\\hat{q}**：若存在 ``EP_Decomposition/Q_P_ePDF_*.csv``，用其 ``Returns`` + ``Q_mean``（与 **S9_1** 一致）；否则由 **S6_1** ``Q_matrix`` + **S7** 聚类日平均。
- **\\hat{p}**：只要存在 **S8_0** ``P_density/ePDF/P_ePDF_*.xlsx``，**一律从 xlsx 重新插值**到上述网格（保证换 **btc_poly_gev** 或重跑 S8_0 后图与最新 P 一致）；仅当无 xlsx 时才回退 csv 里的 ``P_NB*``。

**BTC 收益变换**：HV/LV 的样本与 **S8_0** 相同，为重叠简单收益再 ``r * sqrt(var_簇 / var_全)``，对应 Matlab ``rescale_shift_return_exp(...,0,0,var_overall,var_cluster,τ)`` 在均值项为 0 时的分支；**无**再对 ePDF 做 ``exp(ret)-1`` 变换（BTC 里该步已注释）。

**输出**：``results/ttm_XX/Q_P_PK/ePDF/``

- ``Q_P_PK_ePDF_{OA|HV|LV}_ttm{τ}day.png``
- ``Q_P_PK_ePDF_OAHVLV_panel_ttm{τ}day.png``（三制度叠成一张：3 行子图，每行该制度的 Q/P/PK）
- ``PK_ePDF_OAHVLV_panel_ttm{τ}day.png``（同上版式，仅 ``\\widehat{PK}`` 三行）
- ``PK_ePDF_OAHVLV_ttm{τ}day.png``（OA/HV/LV 三条 ``\\widehat{PK}`` **同轴叠图**，版式对齐 ``EP_curves_OAHVLV_ttm{τ}day.png``）

用法::

    python3 scripts/S11_0_QPPK_ePDF.py
    python3 scripts/S11_0_QPPK_ePDF.py --ttm 27
    python3 scripts/S11_0_QPPK_ePDF.py --p-nb 12 --robust
    python3 scripts/S11_0_QPPK_ePDF.py --pk-plot-xmin -0.8   # 改截断阈值；不截断需 ``--pk-plot-xmin -1``
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from function import (  # noqa: E402
    ETH_EP_DECOMPOSITION_SUBDIR,
    ETH_P_DENSITY_EXCEL_SUBDIR,
    ETH_Q_MATRIX_MON_STEP_SUBDIR,
    ETH_Q_MATRIX_OUT_DIR,
    ETH_Q_P_PK_SUBDIR,
    PRIMARY_TTMS,
    clustering_multivariate_run_dir,
    ensure_results_dir,
)

_REGIMES = ("OA", "HV", "LV")
_REGIME_COLORS = {"OA": "#000000", "HV": "#1f77b4", "LV": "#d62728"}
_REGIME_LEGEND_SUFFIX = {
    "OA": (r"$\hat{q}_{OA}$", r"$\hat{p}_{OA}$", r"$\widehat{PK}_{OA}$"),
    "HV": (r"$\hat{q}_{HV}$", r"$\hat{p}_{HV}$", r"$\widehat{PK}_{HV}$"),
    "LV": (r"$\hat{q}_{LV}$", r"$\hat{p}_{LV}$", r"$\widehat{PK}_{LV}$"),
}

_RET_AXIS_TICKS = (-1.0, -0.8, -0.6, -0.4, -0.2, 0.0, 0.2, 0.4, 0.6, 0.8, 1.0)


def _mask_pk_left_tail(grid: np.ndarray, pk: np.ndarray, pk_plot_xmin: float | None) -> np.ndarray:
    """Set PK to NaN for Return < pk_plot_xmin so the left tail is not drawn."""
    if pk_plot_xmin is None:
        return pk
    g = np.asarray(grid, dtype=float)
    out = np.asarray(pk, dtype=float).copy()
    out[g < float(pk_plot_xmin)] = np.nan
    return out


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


def regime_date_strings(cluster_df: pd.DataFrame, regime: str) -> List[str]:
    d = pd.to_datetime(cluster_df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    if regime == "OA":
        m = cluster_df["cluster"].isin((0, 1))
    elif regime == "HV":
        m = cluster_df["cluster"] == 0
    elif regime == "LV":
        m = cluster_df["cluster"] == 1
    else:
        raise ValueError(regime)
    return d[m].tolist()


def load_q_matrix(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, index_col=0)
    df.columns = [str(c).strip() for c in df.columns]
    idx = pd.to_numeric(df.index, errors="coerce")
    df = df.assign(_i=idx).dropna(subset=["_i"]).sort_values("_i").drop(columns=["_i"])
    df.index = pd.to_numeric(df.index, errors="coerce")
    df = df[~df.index.duplicated(keep="last")]
    return df.sort_index()


def mean_q_on_grid(
    q_df: pd.DataFrame,
    date_strs: List[str],
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    grid = q_df.index.to_numpy(dtype=float)
    ok = [c for c in date_strs if c in q_df.columns]
    if not ok:
        raise ValueError("no Q_matrix columns intersect regime dates")
    mat = q_df[ok].to_numpy(dtype=float)
    mat = np.maximum(mat, 0.0)
    qm = np.mean(mat, axis=1)
    a = float(np.trapz(qm, grid))
    if a > 0:
        qm = qm / a
    return grid, qm.astype(float), ok


def load_p_epdf_xlsx(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, engine="openpyxl")
    if "Returns" not in df.columns:
        raise ValueError(f"Returns missing: {path}")
    return df


def align_p_on_grid(df: pd.DataFrame, grid: np.ndarray, p_col: str) -> np.ndarray:
    ret = df["Returns"].to_numpy(dtype=float)
    p = df[p_col].to_numpy(dtype=float)
    order = np.argsort(ret)
    ret_s = ret[order]
    p_s = p[order]
    # 常值外推：避免 ``grid`` 略超出 Excel 端点时 ``left=0`` 把 \\(\\hat p\\) 打成 0、\\(\\widehat{PK}\\) 失真
    lo = float(np.maximum(p_s[0], 0.0))
    hi = float(np.maximum(p_s[-1], 0.0))
    p_i = np.interp(grid, ret_s, p_s, left=lo, right=hi)
    p_i = np.maximum(p_i, 0.0)
    a = float(np.trapz(p_i, grid))
    if a > 0:
        p_i /= a
    return p_i.astype(float)


def qp_from_ep_csv(
    csv_path: Path,
    p_col: str,
    p_xlsx: Path | None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """读 S9_1 的 Q；P 优先从 **当前** ``P_ePDF_*.xlsx`` 对齐（避免 csv 里仍是旧版无 GEV 的 P）。"""
    df = pd.read_csv(csv_path)
    if "Returns" not in df.columns or "Q_mean" not in df.columns:
        raise ValueError(f"need Returns, Q_mean: {csv_path}")
    grid = df["Returns"].to_numpy(dtype=float)
    q = np.maximum(df["Q_mean"].to_numpy(dtype=float), 0.0)
    if p_xlsx is not None and p_xlsx.is_file():
        pdf = load_p_epdf_xlsx(p_xlsx)
        if p_col not in pdf.columns:
            raise ValueError(f"{p_col} missing in {p_xlsx}")
        p = align_p_on_grid(pdf, grid, p_col)
    else:
        if p_col not in df.columns:
            raise ValueError(f"missing {p_col} in {csv_path} (no {p_xlsx})")
        p = np.maximum(df[p_col].to_numpy(dtype=float), 0.0)
    return grid, q, p


def qp_compute(
    regime: str,
    q_df: pd.DataFrame,
    cluster_df: pd.DataFrame,
    p_xlsx: Path,
    p_col: str,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    ds = regime_date_strings(cluster_df, regime)
    grid, q_mean, _ = mean_q_on_grid(q_df, ds)
    pdf = load_p_epdf_xlsx(p_xlsx)
    if p_col not in pdf.columns:
        raise ValueError(f"{p_col} missing in {p_xlsx}")
    p_al = align_p_on_grid(pdf, grid, p_col)
    return grid, q_mean, p_al


def pricing_kernel_ratio(q: np.ndarray, p: np.ndarray) -> np.ndarray:
    den = np.maximum(p, 1e-15)
    return (q / den).astype(float)


def _draw_shadow(ax, color: str, y0: float, y1: float, neg: Tuple[float, float], pos: Tuple[float, float]) -> None:
    ax.fill_betweenx([y0, y1], neg[0], neg[1], color=color, alpha=0.05, linewidth=0)
    ax.fill_betweenx([y0, y1], pos[0], pos[1], color=color, alpha=0.05, linewidth=0)


def _draw_shadow_neutral(
    ax,
    y0: float,
    y1: float,
    neg: Tuple[float, float],
    pos: Tuple[float, float],
) -> None:
    """Same shadow bands as regime plots but a single neutral fill (for multi-regime overlay)."""
    for lo, hi in (neg, pos):
        ax.fill_betweenx([y0, y1], lo, hi, color="#888888", alpha=0.07, linewidth=0)


def plot_regime_qp_pk(
    ax,
    grid: np.ndarray,
    q: np.ndarray,
    p: np.ndarray,
    regime: str,
    *,
    shadow_neg: Tuple[float, float],
    shadow_pos: Tuple[float, float],
    pk_plot_xmin: float | None = None,
) -> None:
    col = _REGIME_COLORS[regime]
    pk = pricing_kernel_ratio(q, p)
    pk = _mask_pk_left_tail(grid, pk, pk_plot_xmin)
    _draw_shadow(ax, col, -0.5, 6.0, shadow_neg, shadow_pos)
    ax.plot(grid, q, "-", color=col, linewidth=2, label=_REGIME_LEGEND_SUFFIX[regime][0])
    ax.plot(grid, p, "--", color=col, linewidth=2, label=_REGIME_LEGEND_SUFFIX[regime][1])
    ax.plot(grid, pk, "-", color=col, linewidth=1.5, label=_REGIME_LEGEND_SUFFIX[regime][2])
    ax.set_xlim(-1, 1)
    ax.set_ylim(0, 4)
    ax.set_xticks(list(_RET_AXIS_TICKS))
    ax.set_xlabel("Return")
    ax.tick_params(labelsize=12)
    ax.legend(frameon=False, fontsize=11, loc="upper left")


def plot_regime_pk_only(
    ax,
    grid: np.ndarray,
    q: np.ndarray,
    p: np.ndarray,
    regime: str,
    *,
    shadow_neg: Tuple[float, float],
    shadow_pos: Tuple[float, float],
    pk_plot_xmin: float | None = None,
) -> None:
    col = _REGIME_COLORS[regime]
    pk = pricing_kernel_ratio(q, p)
    pk = _mask_pk_left_tail(grid, pk, pk_plot_xmin)
    _draw_shadow(ax, col, -0.5, 6.0, shadow_neg, shadow_pos)
    ax.plot(
        grid,
        pk,
        "-",
        color=col,
        linewidth=2,
        label=_REGIME_LEGEND_SUFFIX[regime][2],
    )
    ax.set_xlim(-1, 1)
    ax.set_ylim(0, 4)
    ax.set_xticks(list(_RET_AXIS_TICKS))
    ax.set_xlabel("Return")
    ax.tick_params(labelsize=12)
    ax.legend(frameon=False, fontsize=11, loc="upper left")


def plot_oahvlv_pk_overlay(
    ax,
    curves: Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray]],
    *,
    shadow_neg: Tuple[float, float],
    shadow_pos: Tuple[float, float],
    pk_plot_xmin: float | None = None,
) -> None:
    """OA/HV/LV pricing kernel on one axes (same spirit as ``EP_curves_OAHVLV``)."""
    _draw_shadow_neutral(ax, -0.5, 6.0, shadow_neg, shadow_pos)
    for regime in _REGIMES:
        g, qv, pv = curves[regime]
        pk = pricing_kernel_ratio(qv, pv)
        pk = _mask_pk_left_tail(g, pk, pk_plot_xmin)
        col = _REGIME_COLORS[regime]
        ax.plot(
            g,
            pk,
            "-",
            color=col,
            linewidth=1.5,
            label=_REGIME_LEGEND_SUFFIX[regime][2],
        )
    ax.set_xlim(-1, 1)
    ax.set_ylim(0, 4)
    ax.set_xticks(list(_RET_AXIS_TICKS))
    ax.set_xlabel("Return")
    ax.tick_params(labelsize=12)
    ax.legend(frameon=False, fontsize=9, loc="upper right")


def default_q_matrix_path(ttm: int, *, use_d15: bool) -> Path:
    base = ETH_Q_MATRIX_OUT_DIR / ETH_Q_MATRIX_MON_STEP_SUBDIR
    suffix = "_d15" if use_d15 else ""
    return base / f"Q_matrix_{ttm}day{suffix}.csv"


def main() -> int:
    ap = argparse.ArgumentParser(description="S11_0: Q / P / PK ePDF figures → Q_P_PK/ePDF/")
    ap.add_argument("--ttm", type=int, nargs="+", default=list(PRIMARY_TTMS))
    ap.add_argument("--robust", action="store_true")
    ap.add_argument("--cluster-csv", type=Path, default=None)
    ap.add_argument("--q-matrix", type=Path, default=None)
    ap.add_argument("--use-d15", action="store_true")
    ap.add_argument("--p-density-dir", type=Path, default=None)
    ap.add_argument("--p-nb", type=int, default=12, help="N for P_NB{N} (default 12, like Matlab NB12)")
    ap.add_argument(
        "--shadow-neg",
        type=float,
        nargs=2,
        default=[-0.6, -0.2],
        metavar=("LO", "HI"),
    )
    ap.add_argument(
        "--shadow-pos",
        type=float,
        nargs=2,
        default=[0.2, 0.6],
        metavar=("LO", "HI"),
    )
    ap.add_argument(
        "--pk-plot-xmin",
        type=float,
        default=-0.85,
        metavar="R",
        help="By default R=-0.85: PK is NaN (not drawn) where Return<R; x-axis still [-1,1] with full ticks. "
        "Use -1 to draw PK on the whole grid (no left masking).",
    )
    args = ap.parse_args()
    p_col = f"P_NB{args.p_nb}"
    pk_plot_xmin: float | None = None if args.pk_plot_xmin <= -1.0 + 1e-12 else float(args.pk_plot_xmin)

    cluster_path = args.cluster_csv or (clustering_multivariate_run_dir() / "common_dates_cluster.csv")
    cluster_df: pd.DataFrame | None
    if cluster_path.is_file():
        cluster_df = load_cluster(cluster_path)
    else:
        cluster_df = None

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise SystemExit("matplotlib is required for S11_0")

    for ttm in args.ttm:
        ttm_root = ensure_results_dir(ttm, robust=args.robust)
        out_dir = ttm_root / ETH_Q_P_PK_SUBDIR
        out_dir.mkdir(parents=True, exist_ok=True)
        ep_dir = ttm_root / ETH_EP_DECOMPOSITION_SUBDIR
        pdir = args.p_density_dir or (ttm_root / ETH_P_DENSITY_EXCEL_SUBDIR)
        q_path = args.q_matrix or default_q_matrix_path(ttm, use_d15=args.use_d15)
        q_df: pd.DataFrame | None = None
        if q_path.is_file():
            try:
                q_df = load_q_matrix(q_path)
            except Exception:
                q_df = None

        meta: Dict[str, object] = {
            "ttm": ttm,
            "p_col": p_col,
            "pk_plot_xmin": pk_plot_xmin,
            "regimes": {},
        }
        curves: Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray]] = {}

        for regime in _REGIMES:
            csv_qp = ep_dir / f"Q_P_ePDF_{regime}_ttm{ttm}day.csv"
            p_xlsx = pdir / f"P_ePDF_{regime}_ttm{ttm}day.xlsx"
            try:
                if csv_qp.is_file():
                    grid, qv, pv = qp_from_ep_csv(csv_qp, p_col, p_xlsx if p_xlsx.is_file() else None)
                    src = "EP_csv_Q_plus_xlsx_P" if p_xlsx.is_file() else "EP_Decomposition_csv"
                else:
                    if cluster_df is None:
                        print(f"skip ttm={ttm} regime={regime}: no {csv_qp} and no cluster csv", file=sys.stderr)
                        continue
                    if q_df is None:
                        print(f"skip ttm={ttm} regime={regime}: need Q_matrix or {csv_qp}", file=sys.stderr)
                        continue
                    if not p_xlsx.is_file():
                        print(f"skip ttm={ttm} regime={regime}: missing {p_xlsx}", file=sys.stderr)
                        continue
                    grid, qv, pv = qp_compute(regime, q_df, cluster_df, p_xlsx, p_col)
                    src = "Q_matrix_xlsx"
            except ValueError as e:
                print(f"skip ttm={ttm} regime={regime}: {e}", file=sys.stderr)
                continue

            curves[regime] = (grid, qv, pv)
            meta["regimes"][regime] = {"source": src}

            fig, ax = plt.subplots(figsize=(4.5, 3))
            plot_regime_qp_pk(
                ax,
                grid,
                qv,
                pv,
                regime,
                shadow_neg=tuple(args.shadow_neg),
                shadow_pos=tuple(args.shadow_pos),
                pk_plot_xmin=pk_plot_xmin,
            )
            fig.tight_layout()
            fig.savefig(out_dir / f"Q_P_PK_ePDF_{regime}_ttm{ttm}day.png", dpi=150)
            plt.close(fig)

        if len(curves) == 3:
            fig, axes = plt.subplots(3, 1, figsize=(4.5, 8.5), sharex=True)
            for ax, regime in zip(axes, _REGIMES):
                g, qv, pv = curves[regime]
                plot_regime_qp_pk(
                    ax,
                    g,
                    qv,
                    pv,
                    regime,
                    shadow_neg=tuple(args.shadow_neg),
                    shadow_pos=tuple(args.shadow_pos),
                    pk_plot_xmin=pk_plot_xmin,
                )
            fig.tight_layout()
            fig.savefig(out_dir / f"Q_P_PK_ePDF_OAHVLV_panel_ttm{ttm}day.png", dpi=150)
            plt.close(fig)

            fig_pk, axes_pk = plt.subplots(3, 1, figsize=(4.5, 8.5), sharex=True)
            for ax_pk, regime in zip(axes_pk, _REGIMES):
                g, qv, pv = curves[regime]
                plot_regime_pk_only(
                    ax_pk,
                    g,
                    qv,
                    pv,
                    regime,
                    shadow_neg=tuple(args.shadow_neg),
                    shadow_pos=tuple(args.shadow_pos),
                    pk_plot_xmin=pk_plot_xmin,
                )
            fig_pk.tight_layout()
            fig_pk.savefig(out_dir / f"PK_ePDF_OAHVLV_panel_ttm{ttm}day.png", dpi=150)
            plt.close(fig_pk)

            fig_1, ax_1 = plt.subplots(figsize=(6, 4))
            plot_oahvlv_pk_overlay(
                ax_1,
                curves,
                shadow_neg=tuple(args.shadow_neg),
                shadow_pos=tuple(args.shadow_pos),
                pk_plot_xmin=pk_plot_xmin,
            )
            fig_1.tight_layout()
            fig_1.savefig(out_dir / f"PK_ePDF_OAHVLV_ttm{ttm}day.png", dpi=150)
            plt.close(fig_1)

        meta_path = out_dir / f"S11_0_run_meta_ttm{ttm}day.json"
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print(f"ttm={ttm} -> {out_dir}")

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
