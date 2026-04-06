#!/usr/bin/env python3
"""
**S6_1 step 5**: ``rough_2`` upper bound (second-difference RMS / h^2).

Default ``--rough-max 5000`` (same as diagnostics; tighten via quantiles if needed).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from function import (  # noqa: E402
    DEFAULT_ROUGH_MAX,
    _GRID_FULL,
    curvature_metrics,
    intermediate_path,
    load_obs_moneyness,
    load_q_csv,
    plot_combined_curves,
    plot_histogram_with_threshold,
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


def run_step5_rough2(
    ttm: int,
    *,
    matrix_dir: Path,
    plot_root: Path,
    iv_surface_dir: Path,
    obs_csv: Path,
    rough_max: float,
) -> Optional[Path]:
    inp = intermediate_path(matrix_dir, ttm, "after_S3")
    if not inp.is_file():
        print(f"  missing {inp}", file=sys.stderr)
        return None
    df, _ = load_q_csv(inp)
    date_strs: List[str] = list(df.columns)
    Q = df.to_numpy(dtype=float)
    n = len(date_strs)
    vals = np.array([curvature_metrics(Q[:, j])["rough_2"] for j in range(n)])
    pass_idx = [j for j in range(n) if vals[j] <= rough_max]
    fail_idx = [j for j in range(n) if vals[j] > rough_max]

    tol = 1e-6
    df_obs = load_obs_moneyness(obs_csv) if obs_csv.is_file() else pd.DataFrame(
        columns=["date", "moneyness", "tau", "IV"]
    )
    combined_dir = plot_root / f"Combined_tau_{ttm}"
    passed_dir, excl_dir, std_dir = step_subdirs(
        combined_dir, 4, "S4_rough2_passed", "S4_rough2_excluded"
    )
    for d in (passed_dir, excl_dir, std_dir):
        d.mkdir(parents=True, exist_ok=True)

    plot_histogram_with_threshold(
        vals,
        rough_max,
        f"S4 rough_2 distribution and threshold (TTM={ttm})",
        "rough_2",
        std_dir / "S4_rough2_distribution.png",
        vertical_label="rough_max",
    )
    rationale = (
        "[S4 rough_2]\n"
        "Definition: d2 = second difference of q; rough_2 = sqrt(mean(d2^2))/h^2 with h=0.01.\n"
        f"Rule: pass if rough_2 <= {rough_max:g}.\n"
        "Default cap matches earlier diagnostics; override with quantiles on this step's columns if desired.\n"
    )
    write_filter_standard(std_dir, rationale)

    pd.DataFrame({"date": date_strs, "rough_2": vals}).to_csv(std_dir / "metric_values.csv", index=False)

    if pass_idx:
        plot_combined_curves(
            indices=pass_idx,
            Q_array=Q,
            date_strs=date_strs,
            grid_full=_GRID_FULL,
            ttm=ttm,
            iv_surface_dir=iv_surface_dir,
            df_obs=df_obs,
            tol=tol,
            left_title=f"S4 rough2 passed ({len(pass_idx)})",
            right_title="IV",
            suptitle=f"S4 rough2 passed TTM={ttm}",
            save_path=passed_dir / f"all_passed_S4_{ttm}day.png",
            xlim=(-1, 1),
            ylim_left=(0, _safe_ceil_max(Q, pass_idx)),
        )
        for i in pass_idx:
            plot_single_curve(
                i, Q, date_strs, _GRID_FULL, ttm, iv_surface_dir, df_obs, tol,
                passed_dir, group_label="S4_rough2_passed",
            )
    if fail_idx:
        plot_combined_curves(
            indices=fail_idx,
            Q_array=Q,
            date_strs=date_strs,
            grid_full=_GRID_FULL,
            ttm=ttm,
            iv_surface_dir=iv_surface_dir,
            df_obs=df_obs,
            tol=tol,
            left_title=f"S4 rough2 excluded ({len(fail_idx)})",
            right_title="IV",
            suptitle=f"S4 rough2 excluded TTM={ttm}",
            save_path=excl_dir / f"all_excluded_S4_{ttm}day.png",
            xlim=(-1, 1),
            ylim_left=(0, _safe_ceil_max(Q, fail_idx)),
        )
        for i in fail_idx:
            plot_single_curve(
                i, Q, date_strs, _GRID_FULL, ttm, iv_surface_dir, df_obs, tol,
                excl_dir, group_label="S4_rough2_excluded",
            )

    pd.DataFrame(
        {
            "date": [date_strs[i] for i in fail_idx],
            "rough_2": [float(vals[i]) for i in fail_idx],
        }
    ).to_csv(std_dir / "excluded_dates.csv", index=False)
    pd.DataFrame({"date": [date_strs[i] for i in pass_idx]}).to_csv(std_dir / "passed_dates.csv", index=False)

    dates_pass = [date_strs[i] for i in pass_idx]
    p4 = intermediate_path(matrix_dir, ttm, "after_S4")
    save_q_csv(Q[:, pass_idx], _GRID_FULL, dates_pass, p4)

    from function import _GRID_D15
    pd15 = intermediate_path(matrix_dir, ttm, "d15_after_S3")
    if pd15.is_file():
        ddf, _ = load_q_csv(pd15)
        ddf = ddf[dates_pass]
        save_q_csv(
            ddf.to_numpy(dtype=float),
            _GRID_D15,
            dates_pass,
            intermediate_path(matrix_dir, ttm, "d15_after_S4"),
        )

    print(f"  S6_1 step5 rough2 ttm={ttm}: {len(dates_pass)}/{n} passed -> {p4.name}")
    return p4


def main() -> None:
    p = argparse.ArgumentParser(description="S6_1 step 5: rough_2")
    p.add_argument("--ttm", type=int, required=True)
    p.add_argument("--rough-max", type=float, default=DEFAULT_ROUGH_MAX)
    p.add_argument("--matrix-dir", type=Path, default=ETH_Q_MATRIX_OUT_DIR / ETH_Q_MATRIX_MON_STEP_SUBDIR)
    p.add_argument(
        "--plot-root",
        type=Path,
        default=ETH_Q_FILTER_PLOT_OUT_DIR / ETH_Q_FILTER_MON_STEP_SUBDIR,
    )
    p.add_argument("--iv-surface-dir", type=Path, default=ETH_IV_SURFACE_FULL_DIR / ETH_IV_SURFACE_MON_STEP_SUBDIR)
    p.add_argument("--obs-csv", type=Path, default=ETH_PROCESSED_MONEYNESS_CSV)
    args = p.parse_args()
    run_step5_rough2(
        args.ttm,
        matrix_dir=args.matrix_dir.resolve(),
        plot_root=args.plot_root.resolve(),
        iv_surface_dir=args.iv_surface_dir.resolve(),
        obs_csv=args.obs_csv.resolve(),
        rough_max=args.rough_max,
    )


if __name__ == "__main__":
    main()
