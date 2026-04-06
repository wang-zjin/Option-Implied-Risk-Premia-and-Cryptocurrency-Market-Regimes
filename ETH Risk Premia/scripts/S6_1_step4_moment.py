#!/usr/bin/env python3
"""
**S6_1 step 4**: moment conditions (same box as BTC ``S2_v1_9``).

Input: ``intermediate/Q_after_S2_{ttm}day.csv``

Output: ``Q_after_S3_*``; ``S3_moment_passed``, ``S3_moment_fail_excluded``, ``S3_filter_standard``
(under ``Combined_tau_{ttm}/``).
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
    _GRID_FULL,
    _KURTOSIS_RANGE,
    _MEAN_RANGE,
    _SKEWNESS_THRESHOLD,
    _VARIANCE_RANGE,
    compute_density_moments,
    intermediate_path,
    load_obs_moneyness,
    load_q_csv,
    plot_combined_curves,
    plot_moment_panel,
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


def run_step4_moment(
    ttm: int,
    *,
    matrix_dir: Path,
    plot_root: Path,
    iv_surface_dir: Path,
    obs_csv: Path,
) -> Optional[Path]:
    inp = intermediate_path(matrix_dir, ttm, "after_S2")
    if not inp.is_file():
        print(f"  missing {inp}", file=sys.stderr)
        return None
    df, _ = load_q_csv(inp)
    date_strs: List[str] = list(df.columns)
    Q = df.to_numpy(dtype=float)
    n = len(date_strs)
    tol = 1e-6
    df_obs = load_obs_moneyness(obs_csv) if obs_csv.is_file() else pd.DataFrame(
        columns=["date", "moneyness", "tau", "IV"]
    )

    combined_dir = plot_root / f"Combined_tau_{ttm}"
    passed_dir, excl_dir, std_dir = step_subdirs(
        combined_dir, 3, "S3_moment_passed", "S3_moment_fail_excluded"
    )
    for d in (passed_dir, excl_dir, std_dir):
        d.mkdir(parents=True, exist_ok=True)

    moments_list = [compute_density_moments(_GRID_FULL, Q[:, j], ttm) for j in range(n)]
    moments = np.array(moments_list)
    plot_moment_panel(moments, std_dir / "S3_moments_distribution_vs_bounds.png")

    valid_mask = (
        (moments[:, 0] >= _MEAN_RANGE[0])
        & (moments[:, 0] <= _MEAN_RANGE[1])
        & (moments[:, 1] >= _VARIANCE_RANGE[0])
        & (moments[:, 1] <= _VARIANCE_RANGE[1])
        & (np.abs(moments[:, 2]) <= _SKEWNESS_THRESHOLD)
        & (moments[:, 3] >= _KURTOSIS_RANGE[0])
        & (moments[:, 3] <= _KURTOSIS_RANGE[1])
    )
    pass_idx = [j for j in range(n) if valid_mask[j]]
    fail_idx = [j for j in range(n) if not valid_mask[j]]

    rationale = (
        "[S3 moments] Box from ``function._MEAN_RANGE`` etc. (ETH defaults; see module comment).\n"
        f"Mean (ann.) in [{_MEAN_RANGE[0]}, {_MEAN_RANGE[1]}]\n"
        f"Variance (ann.) in [{_VARIANCE_RANGE[0]}, {_VARIANCE_RANGE[1]}]\n"
        f"|Skewness| <= {_SKEWNESS_THRESHOLD}\n"
        f"Excess Kurtosis in [{_KURTOSIS_RANGE[0]}, {_KURTOSIS_RANGE[1]}]\n"
        "Plot S3_moments_distribution_vs_bounds.png: four histograms; red dashed lines are bounds.\n"
    )
    write_filter_standard(std_dir, rationale)

    pd.DataFrame(moments, columns=["Mean", "Variance", "Skewness", "Kurtosis"], index=date_strs).to_csv(
        std_dir / "moments_timetable_input.csv"
    )

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
            left_title=f"S3 moment passed ({len(pass_idx)})",
            right_title="IV",
            suptitle=f"S3 moment passed TTM={ttm}",
            save_path=passed_dir / f"all_passed_S3_{ttm}day.png",
            xlim=(-1, 1),
            ylim_left=(0, _safe_ceil_max(Q, pass_idx)),
        )
        for i in pass_idx:
            plot_single_curve(
                i, Q, date_strs, _GRID_FULL, ttm, iv_surface_dir, df_obs, tol,
                passed_dir, group_label="S3_moment_passed",
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
            left_title=f"S3 moment fail excluded ({len(fail_idx)})",
            right_title="IV",
            suptitle=f"S3 moment fail excluded TTM={ttm}",
            save_path=excl_dir / f"all_excluded_S3_{ttm}day.png",
            xlim=(-1, 1),
            ylim_left=(0, _safe_ceil_max(Q, fail_idx)),
        )
        for i in fail_idx:
            plot_single_curve(
                i, Q, date_strs, _GRID_FULL, ttm, iv_surface_dir, df_obs, tol,
                excl_dir, group_label="S3_moment_fail_excluded",
            )

    pd.DataFrame({"date": [date_strs[i] for i in fail_idx]}).to_csv(std_dir / "excluded_dates.csv", index=False)
    pd.DataFrame({"date": [date_strs[i] for i in pass_idx]}).to_csv(std_dir / "passed_dates.csv", index=False)

    dates_pass = [date_strs[i] for i in pass_idx]
    Q3 = Q[:, pass_idx]
    p3 = intermediate_path(matrix_dir, ttm, "after_S3")
    save_q_csv(Q3, _GRID_FULL, dates_pass, p3)

    pd15 = intermediate_path(matrix_dir, ttm, "d15_after_S2")
    if pd15.is_file():
        from function import _GRID_D15
        ddf, _ = load_q_csv(pd15)
        ddf = ddf[dates_pass]
        save_q_csv(
            ddf.to_numpy(dtype=float),
            _GRID_D15,
            dates_pass,
            intermediate_path(matrix_dir, ttm, "d15_after_S3"),
        )

    print(f"  S6_1 step4 moment ttm={ttm}: {len(dates_pass)}/{n} passed -> {p3.name}")
    return p3


def main() -> None:
    p = argparse.ArgumentParser(description="S6_1 step 4: moments")
    p.add_argument("--ttm", type=int, required=True)
    p.add_argument("--matrix-dir", type=Path, default=ETH_Q_MATRIX_OUT_DIR / ETH_Q_MATRIX_MON_STEP_SUBDIR)
    p.add_argument(
        "--plot-root",
        type=Path,
        default=ETH_Q_FILTER_PLOT_OUT_DIR / ETH_Q_FILTER_MON_STEP_SUBDIR,
    )
    p.add_argument("--iv-surface-dir", type=Path, default=ETH_IV_SURFACE_FULL_DIR / ETH_IV_SURFACE_MON_STEP_SUBDIR)
    p.add_argument("--obs-csv", type=Path, default=ETH_PROCESSED_MONEYNESS_CSV)
    args = p.parse_args()
    run_step4_moment(
        args.ttm,
        matrix_dir=args.matrix_dir.resolve(),
        plot_root=args.plot_root.resolve(),
        iv_surface_dir=args.iv_surface_dir.resolve(),
        obs_csv=args.obs_csv.resolve(),
    )


if __name__ == "__main__":
    main()
