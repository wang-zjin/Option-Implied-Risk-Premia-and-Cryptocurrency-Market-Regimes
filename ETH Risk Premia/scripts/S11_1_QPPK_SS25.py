#!/usr/bin/env python3
"""
**S11_1**：**Q / P / PK（SS25）图** — 与 **S11_0** 同版式（实线 \(\hat q\)、虚线 \(\hat p\)、点划 PK），
**\(\hat p\)** 仅来自 **S8_3** ``P_density/SS25/P_SS25_{OA|HV|LV}_ttm{τ}day.csv``（列 **`m`**, **`p_density`**）。

**\(\hat q\)** 与 **S11_0** 一致：优先 **S9_1** ``EP_Decomposition/Q_P_ePDF_*.csv`` 的 ``Returns`` + ``Q_mean``；
否则 **Q_matrix** + **S7** 制度日平均。

**输出**：``results/ttm_XX/Q_P_PK/SS25/``

- ``Q_P_PK_SS25_{OA|HV|LV}_ttm{τ}day.png``
- ``Q_P_PK_SS25_OAHVLV_panel_ttm{τ}day.png``

用法::

    python3 scripts/S11_1_QPPK_SS25.py
    python3 scripts/S11_1_QPPK_SS25.py --ttm 27 --robust
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

_SCRIPTS = Path(__file__).resolve().parent
_ROOT = _SCRIPTS.parent
for _p in (_ROOT, _SCRIPTS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from function import (  # noqa: E402
    ETH_EP_DECOMPOSITION_SUBDIR,
    ETH_P_DENSITY_ROOT,
    ETH_Q_MATRIX_MON_STEP_SUBDIR,
    ETH_Q_MATRIX_OUT_DIR,
    ETH_Q_P_PK_SS25_SUBDIR,
    PRIMARY_TTMS,
    clustering_multivariate_run_dir,
    ensure_results_dir,
)
from S11_0_QPPK_ePDF import (  # noqa: E402
    _REGIMES,
    load_cluster,
    load_q_matrix,
    mean_q_on_grid,
    plot_regime_qp_pk,
    regime_date_strings,
)

P_SS25_COL_M = "m"
P_SS25_COL_P = "p_density"


def default_q_matrix_path(ttm: int, *, use_d15: bool) -> Path:
    base = ETH_Q_MATRIX_OUT_DIR / ETH_Q_MATRIX_MON_STEP_SUBDIR
    suffix = "_d15" if use_d15 else ""
    return base / f"Q_matrix_{ttm}day{suffix}.csv"


def align_p_ss25_on_grid(m_src: np.ndarray, p_src: np.ndarray, grid: np.ndarray) -> np.ndarray:
    """将 S8_3 CSV 在 **m** 上的密度插值到 **grid**。

    与 **S11_0** ``align_p_on_grid`` 一致：**端点常值外推**（``left/right`` 取端点密度），
    避免 ``left=0`` 在尾端把 \\(\\hat p\\) 打成 0、令 \\(\\widehat{\\mathrm{PK}}=\\hat q/\\max(\\hat p,\\epsilon)\\) 失真。
    """
    order = np.argsort(m_src)
    m_s = m_src[order].astype(float)
    p_s = p_src[order].astype(float)
    lo = float(np.maximum(p_s[0], 0.0))
    hi = float(np.maximum(p_s[-1], 0.0))
    p_i = np.interp(grid, m_s, p_s, left=lo, right=hi)
    p_i = np.maximum(p_i, 0.0)
    a = float(np.trapz(p_i, grid))
    if a > 0:
        p_i /= a
    return p_i.astype(float)


def load_p_ss25_csv(path: Path) -> Tuple[np.ndarray, np.ndarray]:
    df = pd.read_csv(path)
    if P_SS25_COL_M not in df.columns or P_SS25_COL_P not in df.columns:
        raise ValueError(f"need columns {P_SS25_COL_M}, {P_SS25_COL_P}: {path}")
    m = df[P_SS25_COL_M].to_numpy(dtype=float)
    p = df[P_SS25_COL_P].to_numpy(dtype=float)
    return m, p


def qp_from_ep_csv_ss25(csv_path: Path, p_ss25_path: Path) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    df = pd.read_csv(csv_path)
    if "Returns" not in df.columns or "Q_mean" not in df.columns:
        raise ValueError(f"need Returns, Q_mean: {csv_path}")
    grid = df["Returns"].to_numpy(dtype=float)
    q = np.maximum(df["Q_mean"].to_numpy(dtype=float), 0.0)
    m, p_raw = load_p_ss25_csv(p_ss25_path)
    p = align_p_ss25_on_grid(m, p_raw, grid)
    return grid, q, p


def qp_compute_ss25(
    regime: str,
    q_df: pd.DataFrame,
    cluster_df: pd.DataFrame,
    p_ss25_path: Path,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    ds = regime_date_strings(cluster_df, regime)
    grid, q_mean, _ = mean_q_on_grid(q_df, ds)
    m, p_raw = load_p_ss25_csv(p_ss25_path)
    p = align_p_ss25_on_grid(m, p_raw, grid)
    return grid, q_mean, p


def main() -> int:
    ap = argparse.ArgumentParser(description="S11_1: QPPK with S8_3 SS25 P → Q_P_PK/SS25/")
    ap.add_argument("--ttm", type=int, nargs="+", default=list(PRIMARY_TTMS))
    ap.add_argument("--robust", action="store_true")
    ap.add_argument("--cluster-csv", type=Path, default=None)
    ap.add_argument("--q-matrix", type=Path, default=None)
    ap.add_argument("--use-d15", action="store_true")
    ap.add_argument(
        "--p-ss25-dir",
        type=Path,
        default=None,
        help="S8_3 输出目录（默认 results/ttm_XX/P_density/SS25/）",
    )
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
    args = ap.parse_args()

    cluster_path = args.cluster_csv or (clustering_multivariate_run_dir() / "common_dates_cluster.csv")
    cluster_df: pd.DataFrame | None
    if cluster_path.is_file():
        cluster_df = load_cluster(cluster_path)
    else:
        cluster_df = None

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise SystemExit("matplotlib is required for S11_1")

    for ttm in args.ttm:
        ttm_root = ensure_results_dir(ttm, robust=args.robust)
        out_dir = ttm_root / ETH_Q_P_PK_SS25_SUBDIR
        out_dir.mkdir(parents=True, exist_ok=True)
        ss25_dir = args.p_ss25_dir or (ttm_root / ETH_P_DENSITY_ROOT / "SS25")
        ep_dir = ttm_root / ETH_EP_DECOMPOSITION_SUBDIR
        q_path = args.q_matrix or default_q_matrix_path(ttm, use_d15=args.use_d15)
        q_df: pd.DataFrame | None = None
        if q_path.is_file():
            try:
                q_df = load_q_matrix(q_path)
            except Exception:
                q_df = None

        meta: Dict[str, object] = {"ttm": int(ttm), "p_source": "S8_3 P_density/SS25 CSV", "regimes": {}}
        curves: Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray]] = {}

        for regime in _REGIMES:
            csv_qp = ep_dir / f"Q_P_ePDF_{regime}_ttm{ttm}day.csv"
            p_ss25 = ss25_dir / f"P_SS25_{regime}_ttm{ttm}day.csv"
            if not p_ss25.is_file():
                print(f"skip ttm={ttm} regime={regime}: missing {p_ss25}", file=sys.stderr)
                continue
            try:
                if csv_qp.is_file():
                    grid, qv, pv = qp_from_ep_csv_ss25(csv_qp, p_ss25)
                    src = "EP_csv_Q_plus_SS25_P"
                else:
                    if cluster_df is None:
                        print(f"skip ttm={ttm} regime={regime}: no {csv_qp} and no cluster csv", file=sys.stderr)
                        continue
                    if q_df is None:
                        print(f"skip ttm={ttm} regime={regime}: need Q_matrix or {csv_qp}", file=sys.stderr)
                        continue
                    grid, qv, pv = qp_compute_ss25(regime, q_df, cluster_df, p_ss25)
                    src = "Q_matrix_SS25_P"
            except ValueError as e:
                print(f"skip ttm={ttm} regime={regime}: {e}", file=sys.stderr)
                continue

            curves[regime] = (grid, qv, pv)
            meta["regimes"][regime] = {"source": src, "p_csv": str(p_ss25.resolve())}

            fig, ax = plt.subplots(figsize=(4.5, 3))
            plot_regime_qp_pk(
                ax,
                grid,
                qv,
                pv,
                regime,
                shadow_neg=tuple(args.shadow_neg),
                shadow_pos=tuple(args.shadow_pos),
            )
            fig.tight_layout()
            fig.savefig(out_dir / f"Q_P_PK_SS25_{regime}_ttm{ttm}day.png", dpi=150)
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
                )
            fig.tight_layout()
            fig.savefig(out_dir / f"Q_P_PK_SS25_OAHVLV_panel_ttm{ttm}day.png", dpi=150)
            plt.close(fig)

        meta_path = out_dir / f"S11_1_run_meta_ttm{ttm}day.json"
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print(f"ttm={ttm} -> {out_dir}")

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
