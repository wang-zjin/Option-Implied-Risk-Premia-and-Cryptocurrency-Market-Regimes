#!/usr/bin/env python3
"""
**S6_1 step 3**: unimodal filter (global argmax + non-decreasing left arm, non-increasing right arm;
same spirit as BTC ``S2_v1_9``).

**Input:** ``intermediate/Q_after_S1_{ttm}day.csv`` under ``--matrix-dir``.

**Output:** ``intermediate/Q_after_S2_{ttm}day.csv``, ``d15_after_S2_*``; under ``Combined_tau_{ttm}/``:
``S2_unimodal_passed/``, ``S2_nonmonotonic_excluded/``, ``S2_filter_standard/`` (incl. ``S2_unimodal_diagnostics.png``).

**How to run** (from ``deribit/`` repo root, next to ``function.py``)::

    python3 scripts/S6_1_step3_unimodal.py --ttm 27
    python3 scripts/S6_1_step3_unimodal.py --ttm 9 27 45

``--ttm`` accepts one or more horizons (space-separated). Defaults for paths match ``function`` (same as step2).

**Prerequisite:** ``intermediate/Q_after_S1_{ttm}day.csv`` must exist (run ``S6_1_step2_nonnegative.py`` for the same ``ttm`` first).

**CLI:** ``python3 scripts/S6_1_step3_unimodal.py --help``
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from function import (  # noqa: E402
    _GRID_D15,
    _GRID_FULL,
    _is_unimodal_monotone,
    intermediate_path,
    load_obs_moneyness,
    load_q_csv,
    plot_combined_curves,
    plot_s2_unimodal_diagnostics,
    plot_single_curve,
    save_q_csv,
    step_subdirs,
    write_filter_standard,
    _safe_ceil_max,
)

from function import (  # noqa: E402
    ETH_IV_SURFACE_FULL_DIR,
    ETH_IV_SURFACE_MON_STEP_SUBDIR,
    ETH_PROCESSED_MONEYNESS_CSV,
    ETH_Q_FILTER_MON_STEP_SUBDIR,
    ETH_Q_FILTER_PLOT_OUT_DIR,
    ETH_Q_MATRIX_MON_STEP_SUBDIR,
    ETH_Q_MATRIX_OUT_DIR,
)


def run_step3_unimodal(
    ttm: int,
    *,
    matrix_dir: Path,
    plot_root: Path,
    iv_surface_dir: Path,
    obs_csv: Path,
) -> Optional[Path]:
    inp = intermediate_path(matrix_dir, ttm, "after_S1")
    if not inp.is_file():
        print(f"  missing {inp} (run S6_1_step2_nonnegative.py first)", file=sys.stderr)
        return None
    df, _grid = load_q_csv(inp)
    date_strs: List[str] = list(df.columns)
    Q = df.to_numpy(dtype=float)
    n = len(date_strs)
    tol = 1e-6
    df_obs = load_obs_moneyness(obs_csv) if obs_csv.is_file() else pd.DataFrame(
        columns=["date", "moneyness", "tau", "IV"]
    )

    combined_dir = plot_root / f"Combined_tau_{ttm}"
    passed_dir, excl_dir, std_dir = step_subdirs(
        combined_dir, 2, "S2_unimodal_passed", "S2_nonmonotonic_excluded"
    )
    for d in (passed_dir, excl_dir, std_dir):
        d.mkdir(parents=True, exist_ok=True)

    mono_idx: List[int] = []
    nonmono_idx: List[int] = []
    for j in range(n):
        dens = Q[:, j]
        if not np.all(np.isfinite(dens)):
            nonmono_idx.append(j)
            continue
        if _is_unimodal_monotone(dens):
            mono_idx.append(j)
        else:
            nonmono_idx.append(j)

    rationale = (
        "[S2 unimodal (monotone)]\n"
        "Rule: with k = argmax(q), pass if [0:k] is non-decreasing and [k:] is non-increasing.\n"
        "Threshold: none (structural boolean constraint; same spirit as BTC ``S2_v1_9``).\n"
        "Plot S2_unimodal_diagnostics.png: pass/fail counts, local-maxima count histogram, peak moneyness.\n"
        "Excluded dates: excluded_dates.csv.\n"
    )
    write_filter_standard(std_dir, rationale)
    plot_s2_unimodal_diagnostics(
        Q, mono_idx, nonmono_idx, std_dir / "S2_unimodal_diagnostics.png"
    )

    if mono_idx:
        plot_combined_curves(
            indices=mono_idx,
            Q_array=Q,
            date_strs=date_strs,
            grid_full=_GRID_FULL,
            ttm=ttm,
            iv_surface_dir=iv_surface_dir,
            df_obs=df_obs,
            tol=tol,
            left_title=f"S2 unimodal passed ({len(mono_idx)})",
            right_title="IV",
            suptitle=f"S2 unimodal passed TTM={ttm}",
            save_path=passed_dir / f"all_passed_S2_{ttm}day.png",
            xlim=(-1, 1),
            ylim_left=(0, _safe_ceil_max(Q, mono_idx)),
        )
        for i in mono_idx:
            plot_single_curve(
                i, Q, date_strs, _GRID_FULL, ttm, iv_surface_dir, df_obs, tol,
                passed_dir, group_label="S2_unimodal_passed",
            )
    if nonmono_idx:
        plot_combined_curves(
            indices=nonmono_idx,
            Q_array=Q,
            date_strs=date_strs,
            grid_full=_GRID_FULL,
            ttm=ttm,
            iv_surface_dir=iv_surface_dir,
            df_obs=df_obs,
            tol=tol,
            left_title=f"S2 nonmonotonic excluded ({len(nonmono_idx)})",
            right_title="IV",
            suptitle=f"S2 nonmonotonic excluded TTM={ttm}",
            save_path=excl_dir / f"all_excluded_S2_{ttm}day.png",
            xlim=(-1, 1),
            ylim_left=(0, _safe_ceil_max(Q, nonmono_idx)),
        )
        for i in nonmono_idx:
            plot_single_curve(
                i, Q, date_strs, _GRID_FULL, ttm, iv_surface_dir, df_obs, tol,
                excl_dir, group_label="S2_nonmonotonic_excluded",
            )

    pd.DataFrame({"date": [date_strs[i] for i in nonmono_idx]}).to_csv(std_dir / "excluded_dates.csv", index=False)
    pd.DataFrame({"date": [date_strs[i] for i in mono_idx]}).to_csv(std_dir / "passed_dates.csv", index=False)

    dates_pass = [date_strs[i] for i in mono_idx]
    Q2 = Q[:, mono_idx]
    p2 = intermediate_path(matrix_dir, ttm, "after_S2")
    save_q_csv(Q2, _GRID_FULL, dates_pass, p2)

    # align d15 grid
    pd15 = intermediate_path(matrix_dir, ttm, "d15_after_S1")
    if pd15.is_file():
        ddf, _ = load_q_csv(pd15)
        ddf = ddf[dates_pass]
        save_q_csv(
            ddf.to_numpy(dtype=float),
            _GRID_D15,
            dates_pass,
            intermediate_path(matrix_dir, ttm, "d15_after_S2"),
        )

    print(f"  S6_1 step3 unimodal ttm={ttm}: {len(dates_pass)}/{n} passed -> {p2.name}")
    return p2


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "S6_1 step 3: keep columns whose q is unimodal on the grid (argmax split + monotone arms). "
            "Reads intermediate/Q_after_S1_{ttm}day.csv; writes Q_after_S2_* and plots under Combined_tau_{ttm}/."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Prerequisite: intermediate/Q_after_S1_{ttm}day.csv under --matrix-dir "
            "(run S6_1_step2_nonnegative.py for each TTM first)."
        ),
    )
    p.add_argument(
        "--ttm",
        type=int,
        nargs="+",
        required=True,
        metavar="DAYS",
        help=(
            "One or more time-to-maturity horizons in days (e.g. --ttm 27 or --ttm 9 27 45). "
            "Matches intermediate filenames and Combined_tau_{ttm}/."
        ),
    )
    p.add_argument(
        "--matrix-dir",
        type=Path,
        default=ETH_Q_MATRIX_OUT_DIR / ETH_Q_MATRIX_MON_STEP_SUBDIR,
        help=(
            "Q_matrix root; must contain intermediate/Q_after_S1_{ttm}day.csv; "
            "writes Q_after_S2_{ttm}day.csv (default: function.ETH_Q_MATRIX_*)."
        ),
    )
    p.add_argument(
        "--plot-root",
        type=Path,
        default=ETH_Q_FILTER_PLOT_OUT_DIR / ETH_Q_FILTER_MON_STEP_SUBDIR,
        help="Q_filter_plot root (moneyness_step_0d01); writes Combined_tau_{ttm}/S2_* (default: ETH_Q_FILTER_PLOT_*).",
    )
    p.add_argument(
        "--iv-surface-dir",
        type=Path,
        default=ETH_IV_SURFACE_FULL_DIR / ETH_IV_SURFACE_MON_STEP_SUBDIR,
        help="IV surface CSVs for diagnostic plot overlays (default: ETH_IV_SURFACE_*).",
    )
    p.add_argument(
        "--obs-csv",
        type=Path,
        default=ETH_PROCESSED_MONEYNESS_CSV,
        help="Observed IV long table for scatter on plots (default: eth_processed_moneyness path).",
    )
    args = p.parse_args()
    md = args.matrix_dir.resolve()
    pr = args.plot_root.resolve()
    ivd = args.iv_surface_dir.resolve()
    obs = args.obs_csv.resolve()
    for ttm in args.ttm:
        run_step3_unimodal(
            ttm,
            matrix_dir=md,
            plot_root=pr,
            iv_surface_dir=ivd,
            obs_csv=obs,
        )


if __name__ == "__main__":
    main()
