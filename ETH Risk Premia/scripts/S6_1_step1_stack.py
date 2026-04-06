#!/usr/bin/env python3
"""
**S6_1 step 1**: stack ``eth_Q`` from S6_0 → **S0 raw plots** (no nonnegative filter yet).

Under ``Combined_tau_{ttm}/``::

- ``S0_raw/``: stacked densities and per-day plots

Intermediate: ``intermediate/Q_after_S0_{ttm}day.csv``, ``Q_d15_after_S0_*``, ``all_dates_{ttm}.txt``
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from function import (  # noqa: E402
    _GRID_D15,
    _GRID_FULL,
    build_q_stack,
    intermediate_path,
    load_obs_moneyness,
    plot_combined_curves,
    plot_single_curve,
    save_q_csv,
)

from function import (  # noqa: E402
    ETH_IV_SURFACE_FULL_DIR,
    ETH_IV_SURFACE_MON_STEP_SUBDIR,
    ETH_PROCESSED_MONEYNESS_CSV,
    ETH_Q_FILTER_MON_STEP_SUBDIR,
    ETH_Q_FILTER_PLOT_OUT_DIR,
    ETH_Q_FROM_SVI_MON_STEP_SUBDIR,
    ETH_Q_FROM_SVI_OUT_DIR,
    ETH_Q_MATRIX_MON_STEP_SUBDIR,
    ETH_Q_MATRIX_OUT_DIR,
)


def run_step1_stack(
    ttm: int,
    *,
    q_root: Path,
    matrix_dir: Path,
    plot_root: Path,
    iv_surface_dir: Path,
    obs_csv: Path,
) -> Tuple[Optional[Path], Optional[Path], Optional[Path]]:
    """
    Return ``(Q_after_S0_csv, Q_d15_after_S0_csv, all_dates_txt)`` or ``(None, None, None)``.
    """
    q_arr, q_d15, date_strs = build_q_stack(ttm, q_root)
    if q_arr is None or not date_strs:
        return None, None, None

    combined_dir = plot_root / f"Combined_tau_{ttm}"
    s0 = combined_dir / "S0_raw"
    s0.mkdir(parents=True, exist_ok=True)

    tol = 1e-6
    df_obs = load_obs_moneyness(obs_csv) if obs_csv.is_file() else pd.DataFrame(
        columns=["date", "moneyness", "tau", "IV"]
    )

    n_dates = q_arr.shape[1]
    all_idx = list(range(n_dates))

    plot_combined_curves(
        indices=all_idx,
        Q_array=q_arr,
        date_strs=date_strs,
        grid_full=_GRID_FULL,
        ttm=ttm,
        iv_surface_dir=iv_surface_dir,
        df_obs=df_obs,
        tol=tol,
        left_title=f"S0 Raw Q Densities TTM={ttm}d",
        right_title="IV",
        suptitle=f"S0 Raw (TTM={ttm} days)",
        save_path=s0 / f"raw_all_density_{ttm}day.png",
    )
    for i in all_idx:
        plot_single_curve(
            i, q_arr, date_strs, _GRID_FULL, ttm, iv_surface_dir, df_obs, tol, s0, group_label="S0_raw"
        )

    p0 = intermediate_path(matrix_dir, ttm, "after_S0")
    pd0 = intermediate_path(matrix_dir, ttm, "d15_after_S0")
    save_q_csv(q_arr, _GRID_FULL, date_strs, p0)
    save_q_csv(q_d15, _GRID_D15, date_strs, pd0)

    all_dates_path = matrix_dir / "intermediate" / f"all_dates_{ttm}.txt"
    all_dates_path.parent.mkdir(parents=True, exist_ok=True)
    all_dates_path.write_text("\n".join(date_strs), encoding="utf-8")

    print(f"  S6_1 step1 stack ttm={ttm}: {n_dates} columns -> {p0.name}, {all_dates_path.name}")
    return p0, pd0, all_dates_path


def main() -> None:
    p = argparse.ArgumentParser(description="S6_1 step 1: stack + S0 (nonnegative: S6_1_step2_nonnegative)")
    p.add_argument("--ttm", type=int, required=True)
    p.add_argument("--q-root", type=Path, default=ETH_Q_FROM_SVI_OUT_DIR / ETH_Q_FROM_SVI_MON_STEP_SUBDIR)
    p.add_argument("--matrix-dir", type=Path, default=ETH_Q_MATRIX_OUT_DIR / ETH_Q_MATRIX_MON_STEP_SUBDIR)
    p.add_argument(
        "--plot-root",
        type=Path,
        default=ETH_Q_FILTER_PLOT_OUT_DIR / ETH_Q_FILTER_MON_STEP_SUBDIR,
    )
    p.add_argument("--iv-surface-dir", type=Path, default=ETH_IV_SURFACE_FULL_DIR / ETH_IV_SURFACE_MON_STEP_SUBDIR)
    p.add_argument("--obs-csv", type=Path, default=ETH_PROCESSED_MONEYNESS_CSV)
    args = p.parse_args()
    run_step1_stack(
        args.ttm,
        q_root=args.q_root.resolve(),
        matrix_dir=args.matrix_dir.resolve(),
        plot_root=args.plot_root.resolve(),
        iv_surface_dir=args.iv_surface_dir.resolve(),
        obs_csv=args.obs_csv.resolve(),
    )


if __name__ == "__main__":
    main()
