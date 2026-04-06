#!/usr/bin/env python3
"""
S9_3：**Influential states / Table 3** — 对齐 BTC
``S6_2_RiskPremia_influential_state_report_multivar_9_27_45.m`` 与论文表
*Characteristics of BP, Q and P in influential states*（论文表；ETH 侧累积曲线列为 **EP**，与 Matlab **BP_overall** 同式）。

**每个制度**（Overall ← **OA**、HV、LV）在阴影区间上报告：

- **负区** \([a_1,b_1]\)（默认 **[-0.6, -0.2]**）：
  **EP**\((b_1)-\)**EP**\((a_1)\)（**归一化 EP** 子列首尾差，与 Matlab ``BP_sub(end)-BP_sub(1)`` 一致）、
  \(\int p\,dr\)、\((\int q\,dr)/(\int p\,dr)\)。
- **正区** \([a_2,b_2]\)（默认 **[0.2, 0.6]**）：
  **EP(0.6)−EP(0.2)**、同上 **∫p**、**∫q/∫p**。

**输入**：读 **S9_1** ``EP_Decomposition/Q_P_ePDF_*.csv`` 与 ``EP_SCA_ePDF_*.csv``（**优先**；若无则回退 **``BP_SCA_*.csv``** / **``BP_NB*``** 旧产物）。
列 ``Returns``、``Q_mean``、``P_NB*``、``EP_NB*``。**P_NB** 默认 ``S9_1_run_meta`` 的 ``best_P_NB``；可用 ``--p-nb`` 强制。

**输出**：``results/ttm_XX/influential_states/ePDF/influential_states_ttm{τ}day.csv``、
``S9_3_run_meta_ttm{τ}day.json``；默认另存 **Table 3 风格** PNG（``--no-plot`` 跳过）。

用法::

    python3 scripts/S9_3_influential_states.py
    python3 scripts/S9_3_influential_states.py --ttm 27 --p-nb 12
    python3 scripts/S9_3_influential_states.py --robust --no-plot
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
    ETH_EP_INFLUENTIAL_STATES_SUBDIR,
    PRIMARY_TTMS,
    ensure_results_dir,
)

_REGIMES_S9 = ("OA", "HV", "LV")
_REGIME_TABLE_ROW = {"OA": "Overall", "HV": "HV", "LV": "LV"}


def ep_interval_contrib(ret: np.ndarray, ep: np.ndarray, lo: float, hi: float) -> float:
    """Matlab: 子序列 end−first；ETH 为 **EP** 曲线。"""
    m = (ret >= lo) & (ret <= hi)
    if not np.any(m):
        return float("nan")
    sub = ep[m]
    return float(sub[-1] - sub[0])


def trapz_interval(ret: np.ndarray, y: np.ndarray, lo: float, hi: float) -> float:
    m = (ret >= lo) & (ret <= hi)
    if not np.any(m):
        return float("nan")
    r = ret[m].astype(float)
    v = y[m].astype(float)
    return float(np.trapz(v, r))


def resolve_p_nb(ep_dir: Path, ttm: int, p_nb_override: int | None) -> str:
    if p_nb_override is not None:
        return f"P_NB{p_nb_override}"
    meta_path = ep_dir / f"S9_1_run_meta_ttm{ttm}day.json"
    if meta_path.is_file():
        try:
            j = json.loads(meta_path.read_text(encoding="utf-8"))
            p = j.get("best_P_NB")
            if isinstance(p, str) and p.startswith("P_NB"):
                return p
        except (json.JSONDecodeError, OSError):
            pass
    return "P_NB12"


def _resolve_ep_col(db: pd.DataFrame, p_col: str) -> str | None:
    ec = "EP_" + p_col.replace("P_", "")
    bc = "BP_" + p_col.replace("P_", "")
    if ec in db.columns:
        return ec
    if bc in db.columns:
        return bc
    return None


def load_qp_ep_pair(
    ep_dir: Path, regime: str, ttm: int, p_col: str
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None:
    qp = ep_dir / f"Q_P_ePDF_{regime}_ttm{ttm}day.csv"
    ep_f = ep_dir / f"EP_SCA_ePDF_{regime}_ttm{ttm}day.csv"
    leg_f = ep_dir / f"BP_SCA_ePDF_{regime}_ttm{ttm}day.csv"
    curve_path = ep_f if ep_f.is_file() else leg_f if leg_f.is_file() else None
    if not qp.is_file() or curve_path is None:
        return None
    dq = pd.read_csv(qp)
    db = pd.read_csv(curve_path)
    if "Returns" not in dq.columns or "Q_mean" not in dq.columns:
        return None
    if p_col not in dq.columns:
        return None
    ep_col = _resolve_ep_col(db, p_col)
    if ep_col is None:
        return None
    merged = pd.merge(
        dq[["Returns", "Q_mean", p_col]].rename(columns={p_col: "P_sel"}),
        db[["Returns", ep_col]].rename(columns={ep_col: "EP_sel"}),
        on="Returns",
        how="inner",
    )
    merged = merged.sort_values("Returns")
    ret = merged["Returns"].to_numpy(dtype=float)
    qv = merged["Q_mean"].to_numpy(dtype=float)
    pv = merged["P_sel"].to_numpy(dtype=float)
    epv = merged["EP_sel"].to_numpy(dtype=float)
    return ret, qv, pv, epv


def one_regime_row(
    ret: np.ndarray,
    q: np.ndarray,
    p: np.ndarray,
    ep: np.ndarray,
    neg: Tuple[float, float],
    pos: Tuple[float, float],
) -> Dict[str, float]:
    lo_n, hi_n = neg
    lo_p, hi_p = pos
    ep_neg = ep_interval_contrib(ret, ep, lo_n, hi_n)
    ep_pos = ep_interval_contrib(ret, ep, lo_p, hi_p)
    int_p_neg = trapz_interval(ret, p, lo_n, hi_n)
    int_q_neg = trapz_interval(ret, q, lo_n, hi_n)
    int_p_pos = trapz_interval(ret, p, lo_p, hi_p)
    int_q_pos = trapz_interval(ret, q, lo_p, hi_p)
    eps = 1e-20
    rp_neg = float(int_q_neg / int_p_neg) if np.isfinite(int_p_neg) and abs(int_p_neg) > eps else float("nan")
    rp_pos = float(int_q_pos / int_p_pos) if np.isfinite(int_p_pos) and abs(int_p_pos) > eps else float("nan")
    return {
        "EP_contrib_neg": ep_neg,
        "int_P_neg": int_p_neg,
        "int_Q_neg": int_q_neg,
        "risk_price_neg_Q_over_P": rp_neg,
        "EP_contrib_pos": ep_pos,
        "int_P_pos": int_p_pos,
        "int_Q_pos": int_q_pos,
        "risk_price_pos_Q_over_P": rp_pos,
    }


def write_table3_png(
    df: pd.DataFrame,
    out_path: Path,
    *,
    ep_neg_header: str,
    ep_pos_header: str,
    subtitle: str,
) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11.5, 2.8))
    ax.axis("off")
    ax.set_title(f"Influential states (Table 3 style)\n{subtitle}", fontsize=11, pad=12)
    hdr = [
        "regime",
        ep_neg_header,
        "∫p\ndr\n(neg)",
        "∫q/∫p\n(neg)",
        ep_pos_header,
        "∫p\ndr\n(pos)",
        "∫q/∫p\n(pos)",
    ]
    rows_txt: List[List[str]] = []
    for _, r in df.iterrows():
        rows_txt.append(
            [
                str(r["regime"]),
                f"{r['EP_contrib_neg']:.3f}",
                f"{r['int_P_neg']:.3f}",
                f"{r['risk_price_neg_Q_over_P']:.3f}",
                f"{r['EP_contrib_pos']:.3f}",
                f"{r['int_P_pos']:.3f}",
                f"{r['risk_price_pos_Q_over_P']:.3f}",
            ]
        )
    tab = ax.table(
        cellText=rows_txt,
        colLabels=hdr,
        loc="center",
        cellLoc="center",
    )
    tab.auto_set_font_size(False)
    tab.set_fontsize(9)
    tab.scale(1.05, 1.4)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="S9_3: influential states / Table 3 from S9_1 CSVs")
    ap.add_argument("--ttm", type=int, nargs="+", default=list(PRIMARY_TTMS))
    ap.add_argument("--robust", action="store_true")
    ap.add_argument(
        "--ep-decomposition-dir",
        type=Path,
        default=None,
        help="Override …/EP_Decomposition (default: ttm_root/EP_Decomposition)",
    )
    ap.add_argument(
        "--p-nb",
        type=int,
        default=None,
        dest="p_nb",
        help="Force P_NB{n} (default: S9_1_run_meta best_P_NB or 12)",
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
    ap.add_argument("--no-plot", action="store_true", help="Skip Table-3-style PNG")
    args = ap.parse_args()

    rows: List[Dict[str, object]] = []

    for ttm in args.ttm:
        ttm_root = ensure_results_dir(ttm, robust=args.robust)
        ep_dir = args.ep_decomposition_dir or (ttm_root / ETH_EP_DECOMPOSITION_SUBDIR)
        out_root = ttm_root / ETH_EP_INFLUENTIAL_STATES_SUBDIR
        out_root.mkdir(parents=True, exist_ok=True)

        p_col = resolve_p_nb(ep_dir, ttm, args.p_nb)
        neg = (float(args.shadow_neg[0]), float(args.shadow_neg[1]))
        pos = (float(args.shadow_pos[0]), float(args.shadow_pos[1]))

        meta: Dict[str, object] = {
            "ttm": ttm,
            "P_NB_column": p_col,
            "shadow_neg": list(neg),
            "shadow_pos": list(pos),
            "source_EP_Decomposition": str(ep_dir),
            "note_EP_pos": "EP_contrib_pos = EP(0.6)-EP(0.2) on [0.2,0.6] (Matlab BP_sub; BTC S6_2)",
            "note_EP_neg": "EP_contrib_neg = EP(-0.2)-EP(-0.6) on [-0.6,-0.2]",
            "note_risk_price": "risk_price = (int_Q) / (int_P) on same interval (not int of Q/P)",
        }

        block_rows: List[Dict[str, object]] = []
        for regime in _REGIMES_S9:
            loaded = load_qp_ep_pair(ep_dir, regime, ttm, p_col)
            if loaded is None:
                print(
                    f"skip ttm={ttm} regime={regime}: missing Q_P/EP_SCA (or legacy BP_SCA) or column {p_col}",
                    file=sys.stderr,
                )
                continue
            ret, qv, pv, epv = loaded
            d = one_regime_row(ret, qv, pv, epv, neg, pos)
            rec = {
                "ttm": ttm,
                "regime": _REGIME_TABLE_ROW[regime],
                "regime_code": regime,
                "P_NB": p_col,
                **{k: d[k] for k in d},
            }
            block_rows.append(rec)
            rows.append(rec)

        if not block_rows:
            print(f"skip ttm={ttm}: no rows (run S9_1 first for {ep_dir})", file=sys.stderr)
            continue

        out_csv = out_root / f"influential_states_ttm{ttm}day.csv"
        pd.DataFrame(block_rows).to_csv(out_csv, index=False, encoding="utf-8")
        meta["n_regimes"] = len(block_rows)
        meta_path = out_root / f"S9_3_run_meta_ttm{ttm}day.json"
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print(f"ttm={ttm} -> {out_csv}")

        if not args.no_plot:
            try:
                import matplotlib.pyplot  # noqa: F401
            except ImportError:
                print("warning: matplotlib missing, skip table PNG", file=sys.stderr)
            else:
                plot_df = pd.DataFrame(block_rows)
                ep_neg_h = f"EP({neg[1]:.2f})\n−EP({neg[0]:.2f})"
                ep_pos_h = f"EP({pos[1]:.2f})\n−EP({pos[0]:.2f})"
                sub = (
                    f"Negative [{neg[0]:.2f},{neg[1]:.2f}], "
                    f"positive [{pos[0]:.2f},{pos[1]:.2f}], {p_col}"
                )
                png_path = out_root / f"influential_states_table3_ttm{ttm}day.png"
                write_table3_png(
                    plot_df,
                    png_path,
                    ep_neg_header=ep_neg_h,
                    ep_pos_header=ep_pos_h,
                    subtitle=sub,
                )
                print(f"  figure -> {png_path}")

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
