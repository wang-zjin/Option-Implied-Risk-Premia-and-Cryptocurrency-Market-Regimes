#!/usr/bin/env python3
"""
**S6_1 step 6**: ``spike_ratio = max(q)/median(q)``.

Default **``--spike-ratio-max``** is ``function.DEFAULT_SPIKE_RATIO_MAX`` (loose; tighten using
``S5_spike_ratio_distribution.png`` and ``metric_values.csv``).
**``--no-spike-filter``** disables filtering here (pass all).
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
    DEFAULT_SPIKE_RATIO_MAX,
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


def run_step6_spike(
    ttm: int,
    *,
    matrix_dir: Path,
    plot_root: Path,
    iv_surface_dir: Path,
    obs_csv: Path,
    spike_ratio_max: Optional[float],
) -> Optional[Path]:
    inp = intermediate_path(matrix_dir, ttm, "after_S4")
    if not inp.is_file():
        print(f"  missing {inp}", file=sys.stderr)
        return None
    df, _ = load_q_csv(inp)
    date_strs: List[str] = list(df.columns)
    Q = df.to_numpy(dtype=float)
    n = len(date_strs)
    vals = np.array([curvature_metrics(Q[:, j])["spike_ratio"] for j in range(n)])

    if spike_ratio_max is None:
        pass_idx = list(range(n))
        fail_idx: List[int] = []
    else:
        pass_idx = [j for j in range(n) if vals[j] <= spike_ratio_max]
        fail_idx = [j for j in range(n) if vals[j] > spike_ratio_max]

    tol = 1e-6
    df_obs = load_obs_moneyness(obs_csv) if obs_csv.is_file() else pd.DataFrame(
        columns=["date", "moneyness", "tau", "IV"]
    )
    combined_dir = plot_root / f"Combined_tau_{ttm}"
    passed_dir, excl_dir, std_dir = step_subdirs(
        combined_dir, 5, "S5_spike_ratio_passed", "S5_spike_ratio_excluded"
    )
    for d in (passed_dir, excl_dir, std_dir):
        d.mkdir(parents=True, exist_ok=True)

    plot_histogram_with_threshold(
        vals,
        spike_ratio_max,
        f"S5 spike_ratio distribution and threshold (TTM={ttm})",
        "spike_ratio",
        std_dir / "S5_spike_ratio_distribution.png",
        vertical_label="spike_ratio_max",
    )
    rationale = (
        "[S5 spike_ratio]\n"
        "Definition: spike_ratio = max(q) / median(q).\n"
        + (
            f"Rule: pass if spike_ratio <= {spike_ratio_max:g}.\n"
            if spike_ratio_max is not None
            else "Rule: **no upper cap set — this step does not drop any column** (all pass).\n"
        )
        + "Note: among S3-passing days this often relates to concentration; medians ~20+ are common; "
        "use only as optional outlier control, not one-to-one with IV kinks.\n"
    )
    write_filter_standard(std_dir, rationale)
    pd.DataFrame({"date": date_strs, "spike_ratio": vals}).to_csv(std_dir / "metric_values.csv", index=False)

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
            left_title=f"S5 spike_ratio passed ({len(pass_idx)})",
            right_title="IV",
            suptitle=f"S5 spike_ratio passed TTM={ttm}",
            save_path=passed_dir / f"all_passed_S5_{ttm}day.png",
            xlim=(-1, 1),
            ylim_left=(0, _safe_ceil_max(Q, pass_idx)),
        )
        for i in pass_idx:
            plot_single_curve(
                i, Q, date_strs, _GRID_FULL, ttm, iv_surface_dir, df_obs, tol,
                passed_dir, group_label="S5_spike_ratio_passed",
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
            left_title=f"S5 spike_ratio excluded ({len(fail_idx)})",
            right_title="IV",
            suptitle=f"S5 spike_ratio excluded TTM={ttm}",
            save_path=excl_dir / f"all_excluded_S5_{ttm}day.png",
            xlim=(-1, 1),
            ylim_left=(0, _safe_ceil_max(Q, fail_idx)),
        )
        for i in fail_idx:
            plot_single_curve(
                i, Q, date_strs, _GRID_FULL, ttm, iv_surface_dir, df_obs, tol,
                excl_dir, group_label="S5_spike_ratio_excluded",
            )

    pd.DataFrame(
        {
            "date": [date_strs[i] for i in fail_idx],
            "spike_ratio": [float(vals[i]) for i in fail_idx],
        }
    ).to_csv(std_dir / "excluded_dates.csv", index=False)
    pd.DataFrame({"date": [date_strs[i] for i in pass_idx]}).to_csv(std_dir / "passed_dates.csv", index=False)

    dates_pass = [date_strs[i] for i in pass_idx]
    p5 = intermediate_path(matrix_dir, ttm, "after_S5")
    save_q_csv(Q[:, pass_idx], _GRID_FULL, dates_pass, p5)

    from function import _GRID_D15
    pd15 = intermediate_path(matrix_dir, ttm, "d15_after_S4")
    if pd15.is_file():
        ddf, _ = load_q_csv(pd15)
        ddf = ddf[dates_pass]
        save_q_csv(
            ddf.to_numpy(dtype=float),
            _GRID_D15,
            dates_pass,
            intermediate_path(matrix_dir, ttm, "d15_after_S5"),
        )

    print(f"  S6_1 step6 spike ttm={ttm}: {len(dates_pass)}/{n} passed -> {p5.name}")
    return p5


def main() -> None:
    p = argparse.ArgumentParser(description="S6_1 step 6: spike_ratio")
    p.add_argument("--ttm", type=int, required=True)
    p.add_argument(
        "--spike-ratio-max",
        type=float,
        default=DEFAULT_SPIKE_RATIO_MAX,
        help=f"upper cap (default {DEFAULT_SPIKE_RATIO_MAX:g}, loose)",
    )
    p.add_argument(
        "--no-spike-filter",
        action="store_true",
        help="skip filtering this step (pass all)",
    )
    p.add_argument("--matrix-dir", type=Path, default=ETH_Q_MATRIX_OUT_DIR / ETH_Q_MATRIX_MON_STEP_SUBDIR)
    p.add_argument(
        "--plot-root",
        type=Path,
        default=ETH_Q_FILTER_PLOT_OUT_DIR / ETH_Q_FILTER_MON_STEP_SUBDIR,
    )
    p.add_argument("--iv-surface-dir", type=Path, default=ETH_IV_SURFACE_FULL_DIR / ETH_IV_SURFACE_MON_STEP_SUBDIR)
    p.add_argument("--obs-csv", type=Path, default=ETH_PROCESSED_MONEYNESS_CSV)
    args = p.parse_args()
    spike_ratio_max = None if args.no_spike_filter else args.spike_ratio_max
    run_step6_spike(
        args.ttm,
        matrix_dir=args.matrix_dir.resolve(),
        plot_root=args.plot_root.resolve(),
        iv_surface_dir=args.iv_surface_dir.resolve(),
        obs_csv=args.obs_csv.resolve(),
        spike_ratio_max=spike_ratio_max,
    )


if __name__ == "__main__":
    main()
