#!/usr/bin/env python3
"""
**S6_1 step 7**: ``peak_neighbor_ratio`` (peak height / mean of neighbors).

Default ``--peak-neighbor-max 2.5``; this step writes the final ``Q_matrix_{ttm}day.csv`` (copied by pipeline).
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from function import (  # noqa: E402
    DEFAULT_PEAK_NEIGHBOR_MAX,
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


def run_step7_peak(
    ttm: int,
    *,
    matrix_dir: Path,
    plot_root: Path,
    iv_surface_dir: Path,
    obs_csv: Path,
    peak_neighbor_max: float,
    out_q_matrix: Path,
    save_d15: bool,
) -> Optional[Path]:
    inp = intermediate_path(matrix_dir, ttm, "after_S5")
    if not inp.is_file():
        print(f"  missing {inp}", file=sys.stderr)
        return None
    df, _ = load_q_csv(inp)
    date_strs: List[str] = list(df.columns)
    Q = df.to_numpy(dtype=float)
    n = len(date_strs)
    vals = np.array(
        [curvature_metrics(Q[:, j])["peak_neighbor_ratio"] for j in range(n)]
    )
    pass_idx = []
    fail_idx = []
    for j in range(n):
        v = vals[j]
        if not np.isfinite(v):
            fail_idx.append(j)
            continue
        if v <= peak_neighbor_max:
            pass_idx.append(j)
        else:
            fail_idx.append(j)

    tol = 1e-6
    df_obs = load_obs_moneyness(obs_csv) if obs_csv.is_file() else pd.DataFrame(
        columns=["date", "moneyness", "tau", "IV"]
    )
    combined_dir = plot_root / f"Combined_tau_{ttm}"
    passed_dir, excl_dir, std_dir = step_subdirs(
        combined_dir, 6, "S6_peak_neighbor_passed", "S6_peak_neighbor_excluded"
    )
    for d in (passed_dir, excl_dir, std_dir):
        d.mkdir(parents=True, exist_ok=True)

    plot_histogram_with_threshold(
        vals[np.isfinite(vals)],
        peak_neighbor_max,
        f"S6 peak_neighbor_ratio distribution and threshold (TTM={ttm})",
        "peak_neighbor_ratio",
        std_dir / "S6_peak_neighbor_distribution.png",
        vertical_label="peak_neighbor_max",
    )
    rationale = (
        "[S6 peak_neighbor_ratio]\n"
        "Definition: k = argmax(q); peak_neighbor_ratio = q[k] / mean(q[k-1], q[k+1]) when peak is interior.\n"
        f"Rule: pass if finite and peak_neighbor_ratio <= {peak_neighbor_max:g}; non-finite fails.\n"
        "Default cap 2.5: sensitive to isolated needles from kinky IV; less so to bumps on broad shoulders.\n"
    )
    write_filter_standard(std_dir, rationale)
    pd.DataFrame({"date": date_strs, "peak_neighbor_ratio": vals}).to_csv(
        std_dir / "metric_values.csv", index=False
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
            left_title=f"S6 peak_neighbor passed ({len(pass_idx)})",
            right_title="IV",
            suptitle=f"S6 peak_neighbor passed TTM={ttm}",
            save_path=passed_dir / f"all_passed_S6_{ttm}day.png",
            xlim=(-1, 1),
            ylim_left=(0, _safe_ceil_max(Q, pass_idx)),
        )
        for i in pass_idx:
            plot_single_curve(
                i, Q, date_strs, _GRID_FULL, ttm, iv_surface_dir, df_obs, tol,
                passed_dir, group_label="S6_peak_neighbor_passed",
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
            left_title=f"S6 peak_neighbor excluded ({len(fail_idx)})",
            right_title="IV",
            suptitle=f"S6 peak_neighbor excluded TTM={ttm}",
            save_path=excl_dir / f"all_excluded_S6_{ttm}day.png",
            xlim=(-1, 1),
            ylim_left=(0, _safe_ceil_max(Q, fail_idx)),
        )
        for i in fail_idx:
            plot_single_curve(
                i, Q, date_strs, _GRID_FULL, ttm, iv_surface_dir, df_obs, tol,
                excl_dir, group_label="S6_peak_neighbor_excluded",
            )

    pd.DataFrame({"date": [date_strs[i] for i in fail_idx]}).to_csv(std_dir / "excluded_dates.csv", index=False)
    pd.DataFrame({"date": [date_strs[i] for i in pass_idx]}).to_csv(std_dir / "passed_dates.csv", index=False)

    dates_final = [date_strs[i] for i in pass_idx]
    Qf = Q[:, pass_idx]
    p6 = intermediate_path(matrix_dir, ttm, "after_S6")
    save_q_csv(Qf, _GRID_FULL, dates_final, p6)

    out_main = out_q_matrix / f"Q_matrix_{ttm}day.csv"
    shutil.copyfile(p6, out_main)

    from function import _GRID_D15
    pd15 = intermediate_path(matrix_dir, ttm, "d15_after_S5")
    if save_d15 and pd15.is_file():
        ddf, _ = load_q_csv(pd15)
        ddf = ddf[dates_final]
        out_d15 = out_q_matrix / f"Q_matrix_{ttm}day_d15.csv"
        save_q_csv(
            ddf.to_numpy(dtype=float),
            _GRID_D15,
            dates_final,
            out_d15,
        )

    print(f"  S6_1 step7 peak ttm={ttm}: final {len(dates_final)}/{n} columns -> {out_main.name}")
    return out_main


def main() -> None:
    p = argparse.ArgumentParser(description="S6_1 step 7: peak_neighbor + final Q_matrix")
    p.add_argument("--ttm", type=int, required=True)
    p.add_argument("--peak-neighbor-max", type=float, default=DEFAULT_PEAK_NEIGHBOR_MAX)
    p.add_argument("--matrix-dir", type=Path, default=ETH_Q_MATRIX_OUT_DIR / ETH_Q_MATRIX_MON_STEP_SUBDIR)
    p.add_argument(
        "--plot-root",
        type=Path,
        default=ETH_Q_FILTER_PLOT_OUT_DIR / ETH_Q_FILTER_MON_STEP_SUBDIR,
    )
    p.add_argument("--iv-surface-dir", type=Path, default=ETH_IV_SURFACE_FULL_DIR / ETH_IV_SURFACE_MON_STEP_SUBDIR)
    p.add_argument("--obs-csv", type=Path, default=ETH_PROCESSED_MONEYNESS_CSV)
    p.add_argument("--out-dir", type=Path, default=ETH_Q_MATRIX_OUT_DIR / ETH_Q_MATRIX_MON_STEP_SUBDIR)
    p.add_argument("--no-d15", action="store_true")
    args = p.parse_args()
    run_step7_peak(
        args.ttm,
        matrix_dir=args.matrix_dir.resolve(),
        plot_root=args.plot_root.resolve(),
        iv_surface_dir=args.iv_surface_dir.resolve(),
        obs_csv=args.obs_csv.resolve(),
        peak_neighbor_max=args.peak_neighbor_max,
        out_q_matrix=args.out_dir.resolve(),
        save_d15=not args.no_d15,
    )


if __name__ == "__main__":
    main()
