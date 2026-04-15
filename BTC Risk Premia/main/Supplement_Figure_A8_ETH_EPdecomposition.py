#!/usr/bin/env python3
"""
S9_1：**EP 分解（density-difference 路径，Ethereum Premium）** — 用 **Q 密度（``Q_matrix`` 按聚类日平均）** 与 **P ePDF（S8_0）**
对标 BTC
``S6_1_RiskPremia_BP_write_QP_*_NB_xlsx_multivar_9_27_45.m`` / ``S6_2_RiskPremia_BP_plot_BP_multivar_9_27_45.m``。
Matlab/BTC 将该归一化累积曲线记为 **``BP_overall``**（Bitcoin Premium）；本仓库 ETH 侧产物与图例统一称 **EP**（**Ethereum Premium**），**公式相同**。

**定义**（与 Matlab ``BP_overall`` / 此处 **EP** 同构）::

    EP(r_j) =  ∫_{-1}^{r_j} (P(x) - Q(x)) \\, x \\, dx  \\Big/  \\int_{-1}^{1} (P(x) - Q(x)) \\, x \\, dx

即 **加权密度差** ``(P-Q)x`` 的 **从左到 r 的累积**，再 **除以全区间累积**（末点规范为 1）。

**Q**：对 ``Q_matrix_{τ}`` 中与制度匹配的 **日期列** 逐行**算术平均**，再 **梯形归一**（``trapz``=1）。
**制度**（与 BTC）：**OA** = 聚类日 **HV∪LV**；**HV** = 仅 **cluster 0**；**LV** = 仅 **cluster 1**。

**P**：读 ``P_ePDF_{OA|HV|LV}_ttm{τ}day.xlsx``，列 ``P_NB6``…``P_NB15``；负值截断后再在 ``Returns`` 网格上归一。

**输出**（``results/ttm_XX/EP_Decomposition/``）::

- ``Q_P_ePDF_{OA|HV|LV}_ttm{τ}day.csv``：``Returns``, ``Q_mean``, ``P_NB6``…
- ``EP_SCA_ePDF_{OA|HV|LV}_ttm{τ}day.csv``：``Returns``, ``EP_NB6``…（曲线名 **EP**，对应 BTC 文件里的 **BP** 列）
- ``EP_decomposition_summary_ttm{τ}day.csv``：``delta_EP_shadow_*``、``EP_int_x_P_minus_Q_denom_before_norm`` 等
- 默认写 **EP 图**：``EP_curves_OAHVLV_ttm{τ}day.png``（与 S11 阴影带一致）、``EP_curves_{OA|HV|LV}_best_NB_{k}_*.png``、``EP_curves_{OA|HV|LV}_all_NB_*.png``。``S9_1_run_meta`` 中 ``best_EP_col``。**``--no-plot``** 跳过 PNG

先决：**S6_1** ``Q_matrix``；**S7** ``common_dates_cluster.csv``；**S8_0** ``P_density/ePDF/P_ePDF_*.xlsx``。

用法::

    python3 scripts/S9_1_EP_decomposition_ePDF.py
    python3 scripts/S9_1_EP_decomposition_ePDF.py --ttm 27
    python3 scripts/S9_1_EP_decomposition_ePDF.py --use-d15 --no-plot   # 跳过 PNG
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
    PRIMARY_TTMS,
    clustering_multivariate_run_dir,
    ensure_results_dir,
)

_REGIMES = ("OA", "HV", "LV")
# 叠图曲线颜色（与 BTC 多制度图常见约定一致）
_REGIME_LINE_COLORS = {"OA": "#000000", "HV": "#1f77b4", "LV": "#d62728"}
# OAHVLV 叠图图例：Ethereum Premium（mathtext）
_REGIME_EP_LEGEND_MATH = {
    "OA": r"$EP_{\mathrm{OA}}$",
    "HV": r"$EP_{\mathrm{HV}}$",
    "LV": r"$EP_{\mathrm{LV}}$",
}
# 横轴 Return 刻度（与 scripts/S11_0_QPPK_ePDF.py 中 PK/Q/P 图一致）
_RET_AXIS_TICKS = (-1.0, -0.8, -0.6, -0.4, -0.2, 0.0, 0.2, 0.4, 0.6, 0.8, 1.0)


def _draw_ep_shadow_bands(
    ax,
    shadow_neg: Tuple[float, float],
    shadow_pos: Tuple[float, float],
) -> None:
    """Grey vertical bands (same style as S11 Q/P/PK figures). Draw before curves so lines stay on top."""
    for lo, hi in (shadow_neg, shadow_pos):
        ax.axvspan(lo, hi, facecolor="#888888", alpha=0.07, linewidth=0, zorder=0)


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
    if not path.is_file():
        raise FileNotFoundError(path)
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
        raise ValueError("no Q_matrix columns intersect regime dates; check date format / S6_1")
    mat = q_df[ok].to_numpy(dtype=float)
    mat = np.maximum(mat, 0.0)
    qm = np.mean(mat, axis=1)
    a = float(np.trapz(qm, grid))
    if a > 0:
        qm = qm / a
    elif np.isfinite(a):
        pass
    return grid, qm.astype(float), ok


def load_p_epdf_xlsx(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(path)
    df = pd.read_excel(path, engine="openpyxl")
    if "Returns" not in df.columns:
        raise ValueError(f"Returns missing: {path}")
    return df


def p_nb_columns(df: pd.DataFrame) -> List[str]:
    return sorted(
        [c for c in df.columns if str(c).startswith("P_NB")],
        key=lambda s: int(str(s).replace("P_NB", "")),
    )


def align_p_on_grid(df: pd.DataFrame, grid: np.ndarray, p_col: str) -> np.ndarray:
    if p_col not in df.columns:
        raise ValueError(f"{p_col} missing in P excel")
    ret = df["Returns"].to_numpy(dtype=float)
    p = df[p_col].to_numpy(dtype=float)
    order = np.argsort(ret)
    ret_s = ret[order]
    p_s = p[order]
    lo = float(np.maximum(p_s[0], 0.0))
    hi = float(np.maximum(p_s[-1], 0.0))
    p_i = np.interp(grid, ret_s, p_s, left=lo, right=hi)
    p_i = np.maximum(p_i, 0.0)
    a = float(np.trapz(p_i, grid))
    if a > 0:
        p_i /= a
    return p_i.astype(float)


def ep_overall_normalized(
    ret: np.ndarray,
    p: np.ndarray,
    q: np.ndarray,
) -> Tuple[np.ndarray, float]:
    """与 Matlab ``BP_overall`` 同式；此处为 **EP** 曲线。末元素归一为 1；返回 (ep_curve, raw_den)。"""
    integrand = (p - q) * ret
    ep = np.zeros_like(ret, dtype=float)
    for i in range(1, len(ret)):
        ep[i] = float(np.trapz(integrand[: i + 1], ret[: i + 1]))
    den = float(ep[-1])
    if not np.isfinite(den) or abs(den) < 1e-20:
        return ep, float("nan")
    return ep / den, den


def ep_subvector_increment(
    ret: np.ndarray,
    ep: np.ndarray,
    x_lo: float,
    x_hi: float,
) -> float:
    """Matlab: 子序列 end−first（``BP_sub``）；此处 **EP** 曲线同样适用。"""
    m = (ret >= x_lo) & (ret <= x_hi)
    if not np.any(m):
        return float("nan")
    sub = ep[m]
    return float(sub[-1] - sub[0])


def _ref_ep_nb_column(bdf: pd.DataFrame) -> str | None:
    if "EP_NB12" in bdf.columns:
        return "EP_NB12"
    if "BP_NB12" in bdf.columns:
        return "BP_NB12"
    cols = [
        c
        for c in bdf.columns
        if str(c).startswith("EP_NB") or str(c).startswith("BP_NB")
    ]
    return cols[len(cols) // 2] if cols else None


def _sorted_ep_nb_columns(bdf: pd.DataFrame) -> List[str]:
    ep = [c for c in bdf.columns if str(c).startswith("EP_NB")]
    if ep:
        return sorted(ep, key=lambda s: int(str(s).replace("EP_NB", "")))
    bp = [c for c in bdf.columns if str(c).startswith("BP_NB")]
    return sorted(bp, key=lambda s: int(str(s).replace("BP_NB", "")))


def pick_best_p_nb(denom_by_regime: Dict[str, Dict[str, float]]) -> Tuple[str, str]:
    """
    在 **各已成功制度** 的 ``P_NB*`` **交集**上，使 **Σ |∫(P−Q)x dx|（EP 归一化前分母）** 最大的列
    （OAHVLV 叠图三线同一 NB 且各 CSV 均有该列）。若交集为空则退化为并集上同样规则。

    返回 ``(P_NBk, EP_NBk)``；若无可用数据则退回 ``P_NB12`` / ``EP_NB12``。
    """
    if not denom_by_regime:
        return "P_NB12", "EP_NB12"

    def p_nb_sort_key(s: str) -> int:
        return int(str(s).replace("P_NB", ""))

    regs = list(denom_by_regime.keys())
    common = set(denom_by_regime[regs[0]])
    for r in regs[1:]:
        common &= set(denom_by_regime[r])
    candidates = common if common else set().union(*[set(denom_by_regime[r]) for r in regs])
    if not candidates:
        return "P_NB12", "EP_NB12"

    best_p: str | None = None
    best_score = -1.0
    for pcol in sorted(candidates, key=p_nb_sort_key):
        score = 0.0
        for r in denom_by_regime:
            if pcol not in denom_by_regime[r]:
                continue
            v = denom_by_regime[r][pcol]
            if np.isfinite(v):
                score += abs(float(v))
        if score > best_score:
            best_score, best_p = score, pcol

    if best_p is None:
        best_p = "P_NB12" if "P_NB12" in candidates else sorted(candidates, key=p_nb_sort_key)[0]
    ep_col = "EP_" + best_p.replace("P_", "")
    return best_p, ep_col


def write_ep_figures(
    out_dir: Path,
    ttm: int,
    best_ep_col: str,
    *,
    shadow_neg: Tuple[float, float] = (-0.6, -0.2),
    shadow_pos: Tuple[float, float] = (0.2, 0.6),
) -> None:
    """与 BTC BP 多图一致版式；曲线为 **EP（Ethereum Premium）**。"""
    import matplotlib.pyplot as plt
    from matplotlib import cm

    # --- OA/HV/LV 叠图：统一 **best_ep_col**，黑 / 蓝 / 红 ---
    fig, ax = plt.subplots(figsize=(6, 4))
    _draw_ep_shadow_bands(ax, shadow_neg, shadow_pos)
    for regime in _REGIMES:
        ep_csv = out_dir / f"EP_SCA_ePDF_{regime}_ttm{ttm}day.csv"
        if not ep_csv.is_file():
            continue
        edf = pd.read_csv(ep_csv)
        col = best_ep_col if best_ep_col in edf.columns else _ref_ep_nb_column(edf)
        if col is None:
            continue
        color = _REGIME_LINE_COLORS[regime]
        ax.plot(
            edf["Returns"],
            edf[col],
            label=_REGIME_EP_LEGEND_MATH[regime],
            color=color,
            linewidth=1.5,
        )
    ax.set_xlim(-1, 1)
    ax.set_xticks(list(_RET_AXIS_TICKS))
    ax.set_xlabel("Return")
    ax.set_ylabel("normalized cumulative EP")
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(out_dir / f"EP_curves_OAHVLV_ttm{ttm}day.png", dpi=150)
    plt.close(fig)

    cmap_by_regime = {"OA": cm.Greys, "HV": cm.Blues, "LV": cm.Reds}
    lo_hi = {"OA": (0.15, 0.92), "HV": (0.35, 0.98), "LV": (0.35, 0.98)}

    for regime in _REGIMES:
        ep_csv = out_dir / f"EP_SCA_ePDF_{regime}_ttm{ttm}day.csv"
        if not ep_csv.is_file():
            continue
        edf = pd.read_csv(ep_csv)
        # --- 各制度：全部 EP_NB*（``all_NB``）---
        ep_cols = _sorted_ep_nb_columns(edf)
        if ep_cols:
            fig, ax = plt.subplots(figsize=(6, 4))
            cmap = cmap_by_regime[regime]
            t0, t1 = lo_hi[regime]
            ts = np.linspace(t0, t1, len(ep_cols))
            for ci, cname in enumerate(ep_cols):
                ax.plot(
                    edf["Returns"],
                    edf[cname],
                    label=cname,
                    color=cmap(ts[ci]),
                    linewidth=1.2,
                )
            ax.set_xlim(-1, 1)
            ax.set_xticks(list(_RET_AXIS_TICKS))
            ax.set_xlabel("Return")
            ax.set_ylabel("normalized cumulative EP")
            ax.set_title(f"{regime} — EP (all NB)", fontsize=11)
            ax.legend(frameon=False, fontsize=7, loc="best", ncol=2)
            fig.tight_layout()
            fig.savefig(out_dir / f"EP_curves_{regime}_all_NB_ttm{ttm}day.png", dpi=150)
            plt.close(fig)

        # --- 各制度：仅 **best_ep_col** 一条；**k** 与 **实际列** 一致 ---
        col1 = best_ep_col if best_ep_col in edf.columns else _ref_ep_nb_column(edf)
        if col1 is not None:
            scol = str(col1)
            if scol.startswith("EP_NB"):
                file_nb_infix = scol[len("EP_NB") :]
            elif scol.startswith("BP_NB"):
                file_nb_infix = scol[len("BP_NB") :]
            else:
                file_nb_infix = scol.removeprefix("EP_").removeprefix("BP_") or "ref"
            fig2, ax2 = plt.subplots(figsize=(6, 4))
            ax2.plot(
                edf["Returns"],
                edf[col1],
                color=_REGIME_LINE_COLORS[regime],
                label=col1,
                linewidth=1.6,
            )
            ax2.set_xlim(-1, 1)
            ax2.set_xticks(list(_RET_AXIS_TICKS))
            ax2.set_xlabel("Return")
            ax2.set_ylabel("normalized cumulative EP")
            ax2.set_title(f"{regime} — {col1} (best NB)", fontsize=11)
            ax2.legend(frameon=False, fontsize=9)
            fig2.tight_layout()
            fig2.savefig(
                out_dir / f"EP_curves_{regime}_best_NB_{file_nb_infix}_ttm{ttm}day.png",
                dpi=150,
            )
            plt.close(fig2)


def default_q_matrix_path(ttm: int, *, use_d15: bool) -> Path:
    base = ETH_Q_MATRIX_OUT_DIR / ETH_Q_MATRIX_MON_STEP_SUBDIR
    suffix = "_d15" if use_d15 else ""
    return base / f"Q_matrix_{ttm}day{suffix}.csv"


def main() -> int:
    p = argparse.ArgumentParser(description="S9_1: EP decomposition Q vs P ePDF → EP_Decomposition/")
    p.add_argument("--ttm", type=int, nargs="+", default=list(PRIMARY_TTMS))
    p.add_argument("--robust", action="store_true")
    p.add_argument("--cluster-csv", type=Path, default=None)
    p.add_argument("--q-matrix", type=Path, default=None)
    p.add_argument("--use-d15", action="store_true", help="Q_matrix_*_d15.csv")
    p.add_argument(
        "--p-density-dir",
        type=Path,
        default=None,
        help="Override directory for P_ePDF_*.xlsx",
    )
    p.add_argument(
        "--shadow-neg",
        type=float,
        nargs=2,
        default=[-0.6, -0.2],
        metavar=("LO", "HI"),
        help="Negative return band for delta_EP in summary (default -0.6 -0.2)",
    )
    p.add_argument(
        "--shadow-pos",
        type=float,
        nargs=2,
        default=[0.2, 0.6],
        metavar=("LO", "HI"),
        help="Positive return band for delta_EP in summary (default 0.2 0.6)",
    )
    p.add_argument(
        "--no-plot",
        action="store_true",
        help="Do not write EP_curves_*.png (OAHVLV / all_NB / best_NB)",
    )
    p.add_argument(
        "--plot",
        action="store_true",
        help=argparse.SUPPRESS,
    )  # 兼容旧命令；默认已开图，无需再传
    args = p.parse_args()
    do_plot = not args.no_plot

    cluster_path = args.cluster_csv or (clustering_multivariate_run_dir() / "common_dates_cluster.csv")
    if not cluster_path.is_file():
        raise SystemExit(f"missing {cluster_path}")
    cluster_df = load_cluster(cluster_path)

    summary_rows: List[Dict[str, object]] = []

    for ttm in args.ttm:
        ttm_root = ensure_results_dir(ttm, robust=args.robust)
        out_dir = ttm_root / ETH_EP_DECOMPOSITION_SUBDIR
        out_dir.mkdir(parents=True, exist_ok=True)

        q_path = args.q_matrix or default_q_matrix_path(ttm, use_d15=args.use_d15)
        try:
            q_df = load_q_matrix(q_path)
        except FileNotFoundError as e:
            print(f"skip ttm={ttm}: {e}", file=sys.stderr)
            continue

        pdir = args.p_density_dir or (ttm_root / ETH_P_DENSITY_EXCEL_SUBDIR)
        summ_meta: Dict[str, object] = {"ttm": ttm, "q_matrix": str(q_path), "regimes": {}}
        denom_by_regime: Dict[str, Dict[str, float]] = {}

        for regime in _REGIMES:
            p_xlsx = pdir / f"P_ePDF_{regime}_ttm{ttm}day.xlsx"
            if not p_xlsx.is_file():
                print(f"skip ttm={ttm} regime={regime}: missing {p_xlsx}", file=sys.stderr)
                continue
            ds = regime_date_strings(cluster_df, regime)
            try:
                grid, q_mean, ok_cols = mean_q_on_grid(q_df, ds)
            except ValueError as e:
                print(f"skip ttm={ttm} regime={regime}: {e}", file=sys.stderr)
                continue

            pdf = load_p_epdf_xlsx(p_xlsx)
            nb_cols = p_nb_columns(pdf)
            if not nb_cols:
                print(f"skip ttm={ttm} regime={regime}: no P_NB* columns", file=sys.stderr)
                continue

            q_block = {"Returns": grid, "Q_mean": q_mean}
            ep_block: Dict[str, np.ndarray] = {"Returns": grid}
            pref = "P_NB12" if "P_NB12" in nb_cols else nb_cols[len(nb_cols) // 2]
            raw_den_pref = float("nan")
            denom_by_regime[regime] = {}

            for pcol in nb_cols:
                pv = align_p_on_grid(pdf, grid, pcol)
                q_block[pcol] = pv
                ep_curve, raw_den = ep_overall_normalized(grid, pv, q_mean)
                ep_name = "EP_" + pcol.replace("P_", "")
                ep_block[ep_name] = ep_curve
                denom_by_regime[regime][pcol] = float(raw_den)
                if pcol == pref:
                    raw_den_pref = raw_den

            q_p_csv = out_dir / f"Q_P_ePDF_{regime}_ttm{ttm}day.csv"
            ep_csv = out_dir / f"EP_SCA_ePDF_{regime}_ttm{ttm}day.csv"
            pd.DataFrame(q_block).to_csv(q_p_csv, index=False, encoding="utf-8")
            pd.DataFrame(ep_block).to_csv(ep_csv, index=False, encoding="utf-8")

            ep_key = "EP_" + pref.replace("P_", "")
            ep_ref = ep_block[ep_key]
            pv12 = np.asarray(q_block[pref], dtype=float)
            integrand = (pv12 - q_mean) * grid
            total_int = float(np.trapz(integrand, grid))
            d_neg = ep_subvector_increment(grid, ep_ref, args.shadow_neg[0], args.shadow_neg[1])
            d_pos = ep_subvector_increment(grid, ep_ref, args.shadow_pos[0], args.shadow_pos[1])
            summary_rows.append(
                {
                    "ttm": ttm,
                    "regime": regime,
                    "p_nb_ref": pref,
                    "n_Q_dates": len(ok_cols),
                    "total_int_x_P_minus_Q": total_int,
                    "delta_EP_shadow_neg": d_neg,
                    "delta_EP_shadow_pos": d_pos,
                    "EP_int_x_P_minus_Q_denom_before_norm": raw_den_pref,
                }
            )
            summ_meta["regimes"][regime] = {
                "q_p_csv": str(q_p_csv.name),
                "ep_csv": str(ep_csv.name),
                "p_nb_columns": nb_cols,
            }

        best_p, best_ep_col = pick_best_p_nb(denom_by_regime)
        summ_meta["best_P_NB"] = best_p
        summ_meta["best_EP_col"] = best_ep_col
        summ_meta["best_P_NB_criterion"] = (
            "max over P_NB of sum_over_regimes |EP_denom_before_norm| "
            "where EP_denom = int_{-1}^{1} (P_NB - Q) x dx (Matlab BP_overall denominator)"
        )

        summ_path = out_dir / f"EP_decomposition_summary_ttm{ttm}day.csv"
        rows_ttm = [r for r in summary_rows if r["ttm"] == ttm]
        if rows_ttm:
            pd.DataFrame(rows_ttm).to_csv(summ_path, index=False, encoding="utf-8")
        meta_path = out_dir / f"S9_1_run_meta_ttm{ttm}day.json"
        meta_path.write_text(json.dumps(summ_meta, indent=2), encoding="utf-8")
        print(f"ttm={ttm} -> {out_dir}")

        if do_plot:
            try:
                import matplotlib.pyplot  # noqa: F401 — 探测用
            except ImportError:
                print("warning: matplotlib missing, skip figures", file=sys.stderr)
            else:
                write_ep_figures(
                    out_dir,
                    ttm,
                    best_ep_col,
                    shadow_neg=tuple(args.shadow_neg),
                    shadow_pos=tuple(args.shadow_pos),
                )

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
