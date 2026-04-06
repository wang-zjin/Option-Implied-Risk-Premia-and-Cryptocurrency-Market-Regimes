#!/usr/bin/env python3
"""
S6_1: stack **S6_0** ``eth_Q_*.csv`` into ``Q_matrix_{ttm}day.csv``.

**Prerequisite**: ``--q-root`` contains ``tau_{ttm}/eth_Q_*.csv`` (run S6_0 first).

**Run** (from **deribit repo root**, next to ``function.py``)::

    python3 scripts/S6_1_build_Qmatrix.py

**Default CLI arguments** (nothing after ``S6_1_build_Qmatrix.py``). Values match ``main()`` /
``argparse`` defaults; **paths** are under the deribit repo root (``function.PROJECT_ROOT``).

- ``--q-root`` → ``results/Q_from_pure_SVI/moneyness_step_0d01`` (``ETH_Q_FROM_SVI_*``).
- ``--out-dir`` → ``results/Q_matrix/moneyness_step_0d01`` (``ETH_Q_MATRIX_*``).
- ``--plot-root`` → ``results/Q_filter_plot/moneyness_step_0d01`` (``ETH_Q_FILTER_PLOT_*``).
- ``--iv-surface-dir`` → ``results/IV/IV_surface_SVI/moneyness_step_0d01`` (``ETH_IV_SURFACE_*``).
- ``--obs-csv`` → ``data/eth_options_processed/prepare_moneyness_for_SVI/eth_processed_moneyness.csv``.
- ``--ttm-list`` → not set (``None``).
- ``--ttm-min`` / ``--ttm-max`` → not set (``None`` / ``None``).
- ``--all-ttm`` → **off** (false).
- ``--no-d15`` → **off** (false): write narrow ``d15_*`` intermediates when step1 produces them.
- ``--rough-max`` → **5000.0** (``DEFAULT_ROUGH_MAX``).
- ``--spike-ratio-max`` → **500.0** (``DEFAULT_SPIKE_RATIO_MAX``).
- ``--no-spike-filter`` → **off** (false): step6 applies spike cap (``spike_ratio_max`` not ``None``).
- ``--peak-neighbor-max`` → **2.0** (``DEFAULT_PEAK_NEIGHBOR_MAX``).
- ``--s1-nonneg-scope`` → **repaired_core** (``DEFAULT_S1_NONNEG_SCOPE``).
- ``--s1-core-mabs`` → **0.95** (``DEFAULT_S1_CORE_MONEYNESS_ABS_MAX``).
- ``--s1-min-q-floor`` → **-1e-6** (``DEFAULT_S1_MIN_Q_FLOOR``): repaired_core pass on strict ``|m|<0.95`` requires ``min(q)>=`` this.
- ``--s1-small-neg-band`` → **0.01** (``DEFAULT_S1_SMALL_NEG_BAND``): repaired_core sets ``q=0`` where ``-band < q < 0``, then renorm.

**TTM list resolution** (first match wins): ``--all-ttm`` → days **1 … 120** (``SVI_TAU_MIN_DAYS``–``SVI_TAU_MAX_DAYS``); else ``--ttm-list``; else both ``--ttm-min`` and ``--ttm-max`` → inclusive range; else **9, 27, 45** (``PRIMARY_TTMS``).

Examples::

    python3 scripts/S6_1_build_Qmatrix.py --ttm-list 27
    python3 scripts/S6_1_build_Qmatrix.py --ttm-list 9 27 45
    python3 scripts/S6_1_build_Qmatrix.py --ttm-min 1 --ttm-max 120
    python3 scripts/S6_1_build_Qmatrix.py --all-ttm

Further flag descriptions: ``python3 scripts/S6_1_build_Qmatrix.py --help`` (defaults are listed above).

Pipeline is **7 steps** (``S6_1_step*_*.py``; shared logic in ``function.py``):

1. **S6_1_step1_stack**: stack + S0 plots → ``intermediate/Q_after_S0_*``
2. **S6_1_step2_nonnegative**: nonnegative → ``after_S1``; plots ``S1_*`` under ``Combined_tau_{ttm}/``
3. **S6_1_step3_unimodal**: unimodal → ``after_S2``; ``S2_*``
4. **S6_1_step4_moment**: moments → ``after_S3``; ``S3_*``
5. **S6_1_step5_rough2**: ``rough_2`` → ``after_S4``; ``S4_*``
6. **S6_1_step6_spike_ratio**: ``spike_ratio`` (default cap ``function.DEFAULT_SPIKE_RATIO_MAX``) → ``after_S5``; ``S5_*``
7. **S6_1_step7_peak_neighbor**: ``peak_neighbor_ratio`` → final ``Q_matrix_{ttm}day.csv``; ``S6_*``

Plot root: ``results/Q_filter_plot/moneyness_step_0d01/Combined_tau_{ttm}/`` (each step's
``S{N}_*_passed`` / ``S{N}_*_excluded`` / ``S{N}_filter_standard`` sit directly under
``Combined_tau_{ttm}/``, no extra ``S{N}/`` folder).

This script runs all seven steps via ``function.run_full_pipeline``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from function import (  # noqa: E402
    DEFAULT_PEAK_NEIGHBOR_MAX,
    DEFAULT_ROUGH_MAX,
    DEFAULT_S1_CORE_MONEYNESS_ABS_MAX,
    DEFAULT_S1_MIN_Q_FLOOR,
    DEFAULT_S1_NONNEG_SCOPE,
    DEFAULT_S1_SMALL_NEG_BAND,
    DEFAULT_SPIKE_RATIO_MAX,
    run_full_pipeline,
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
    PRIMARY_TTMS,
    SVI_TAU_MAX_DAYS,
    SVI_TAU_MIN_DAYS,
)


def main() -> None:
    p = argparse.ArgumentParser(
        description="S6_1: seven-step filter → Q_matrix (or run S6_1_step*.py separately)"
    )
    p.add_argument(
        "--q-root",
        type=Path,
        default=ETH_Q_FROM_SVI_OUT_DIR / ETH_Q_FROM_SVI_MON_STEP_SUBDIR,
        help="S6_0 output root",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=ETH_Q_MATRIX_OUT_DIR / ETH_Q_MATRIX_MON_STEP_SUBDIR,
        help="directory for Q_matrix CSV output",
    )
    p.add_argument(
        "--plot-root",
        type=Path,
        default=ETH_Q_FILTER_PLOT_OUT_DIR / ETH_Q_FILTER_MON_STEP_SUBDIR,
        help="Q_filter_plot / moneyness_step_0d01",
    )
    p.add_argument("--iv-surface-dir", type=Path, default=ETH_IV_SURFACE_FULL_DIR / ETH_IV_SURFACE_MON_STEP_SUBDIR)
    p.add_argument("--obs-csv", type=Path, default=ETH_PROCESSED_MONEYNESS_CSV)
    p.add_argument("--ttm-list", type=int, nargs="+", default=None)
    p.add_argument("--ttm-min", type=int, default=None)
    p.add_argument("--ttm-max", type=int, default=None)
    p.add_argument("--all-ttm", action="store_true")
    p.add_argument("--no-d15", action="store_true")
    p.add_argument("--rough-max", type=float, default=DEFAULT_ROUGH_MAX)
    p.add_argument(
        "--spike-ratio-max",
        type=float,
        default=DEFAULT_SPIKE_RATIO_MAX,
        help=(
            f"step 6 spike_ratio upper cap (default {DEFAULT_SPIKE_RATIO_MAX:g}, loose; "
            "tighten after plots/tables)"
        ),
    )
    p.add_argument(
        "--no-spike-filter",
        action="store_true",
        help="disable step 6 spike_ratio filter (pass all; legacy behavior)",
    )
    p.add_argument("--peak-neighbor-max", type=float, default=DEFAULT_PEAK_NEIGHBOR_MAX)
    p.add_argument(
        "--s1-nonneg-scope",
        choices=("repaired_core", "full", "core"),
        default=DEFAULT_S1_NONNEG_SCOPE,
        help=(
            "step2: repaired_core=endpoint/tiny-neg repair, renorm, pass on strict |m|<core; "
            f"full/core=legacy (no repair). Core threshold default {DEFAULT_S1_CORE_MONEYNESS_ABS_MAX:g}"
        ),
    )
    p.add_argument(
        "--s1-core-mabs",
        type=float,
        default=DEFAULT_S1_CORE_MONEYNESS_ABS_MAX,
        help=(
            "step2: repaired_core uses strict |m|<this for pass rule; core mode uses |m|<=this (try 0.95 vs 0.99)"
        ),
    )
    p.add_argument(
        "--s1-min-q-floor",
        type=float,
        default=DEFAULT_S1_MIN_Q_FLOOR,
        help="step2 repaired_core: pass if min(q) on strict |m|<core >= this (default -1e-6)",
    )
    p.add_argument(
        "--s1-small-neg-band",
        type=float,
        default=DEFAULT_S1_SMALL_NEG_BAND,
        help="step2 repaired_core: set q=0 where -band < q < 0 (default 0.01), then renorm",
    )
    args = p.parse_args()

    q_root = args.q_root.resolve()
    out_dir = args.out_dir.resolve()
    plot_root = args.plot_root.resolve()
    iv_surface_dir = args.iv_surface_dir.resolve()
    obs_csv = args.obs_csv.resolve()
    matrix_dir = out_dir

    if args.all_ttm:
        ttms: Sequence[int] = tuple(range(SVI_TAU_MIN_DAYS, SVI_TAU_MAX_DAYS + 1))
    elif args.ttm_list is not None:
        ttms = tuple(args.ttm_list)
    elif args.ttm_min is not None and args.ttm_max is not None:
        if args.ttm_min > args.ttm_max:
            print("error: --ttm-min > --ttm-max", file=sys.stderr)
            raise SystemExit(2)
        ttms = tuple(range(args.ttm_min, args.ttm_max + 1))
    else:
        ttms = PRIMARY_TTMS

    spike_ratio_max = None if args.no_spike_filter else args.spike_ratio_max

    print(f"S6_1 (7 steps) q_root={q_root}")
    print(f"out={out_dir}; plots={plot_root}")
    print(f"IV surface={iv_surface_dir}; obs={obs_csv}")
    print(
        f"curvature: rough_max={args.rough_max}, spike_ratio_max={spike_ratio_max}, "
        f"peak_neighbor_max={args.peak_neighbor_max}"
    )
    print(f"TTM: {list(ttms)[:20]}{'...' if len(ttms) > 20 else ''} (n={len(ttms)})")

    save_d15 = not args.no_d15
    for ttm in ttms:
        run_full_pipeline(
            ttm,
            q_root=q_root,
            matrix_dir=matrix_dir,
            plot_root=plot_root,
            iv_surface_dir=iv_surface_dir,
            obs_csv=obs_csv,
            out_q_dir=out_dir,
            save_d15=save_d15,
            rough_max=args.rough_max,
            spike_ratio_max=spike_ratio_max,
            peak_neighbor_max=args.peak_neighbor_max,
            s1_nonneg_scope=args.s1_nonneg_scope,
            s1_core_moneyness_abs_max=args.s1_core_mabs,
            s1_min_q_floor=args.s1_min_q_floor,
            s1_small_neg_band=args.s1_small_neg_band,
        )

    print("done.")


if __name__ == "__main__":
    main()
