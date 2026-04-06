#!/usr/bin/env python3
"""
**S6_1 step 2**: nonnegative filter (reads ``Q_after_S0``).

Output dirs under ``Combined_tau_{ttm}/``::

- ``S1_nonnegative_passed/``, ``S1_negative_excluded/``, ``S1_filter_standard/``

Intermediate: ``intermediate/Q_after_S1_{ttm}day.csv``, ``Q_d15_after_S1_*``

**How to run** (from ``deribit/`` repo root, same level as ``function.py``)::

    python3 scripts/S6_1_step2_nonnegative.py --ttm 27
    python3 scripts/S6_1_step2_nonnegative.py --ttm 9 27 45

``--ttm`` accepts **one or more** horizons (space-separated, not the word ``list``).
Paths default to
``function.ETH_Q_MATRIX_*``, ``ETH_Q_FILTER_PLOT_*``, etc.; override with ``--matrix-dir``,
``--plot-root``, ``--iv-surface-dir``, ``--obs-csv`` if needed.

**Prerequisite:** ``intermediate/Q_after_S0_{ttm}day.csv`` must exist under ``--matrix-dir``
(run ``python3 scripts/S6_1_step1_stack.py --ttm <same>`` first).

**Nonnegative rule (step2 flags):**

- ``--nonneg-scope repaired_core`` (default ``function.DEFAULT_S1_NONNEG_SCOPE``): clip m=±1 negatives to 0; if ``-small_neg_band < q < 0`` (default band **0.01**) set ``q=0``; trapezoid renormalize; **drop** column unless ``min(q)>=floor`` on strict **|m|<core_abs** (``--min-q-floor`` default **-1e-6**). Saved ``after_S1`` is the **repaired** density; ``d15`` is sliced from it.
- ``--nonneg-scope full``: legacy — no repair; pass iff ``min(q)>=floor`` on full grid.
- ``--nonneg-scope core``: legacy — no repair; pass iff ``min(q)>=floor`` on ``|m|<=`` ``--core-moneyness-abs-max``.

**Tunable parameters (defaults from ``function.py``):**

- ``--core-moneyness-abs-max`` (default ``DEFAULT_S1_CORE_MONEYNESS_ABS_MAX``, **0.95**): band used for the **core** rule. For ``repaired_core``, pass/fail uses ``min(q)`` on **strict** ``|m| <`` this value. For ``core``, ``min(q)`` is on **inclusive** ``|m|<=`` this value.
- ``--small-neg-band`` (default ``DEFAULT_S1_SMALL_NEG_BAND``, **0.01**; ``repaired_core``): set ``q=0`` where ``-band < q < 0``, then renorm.
- ``--min-q-floor`` (default ``DEFAULT_S1_MIN_Q_FLOOR``, **-1e-6**): pass requires ``min(q)`` under the rule ``>=`` this floor (strict **|m|<core** for ``repaired_core``).

**CLI reference:** ``python3 scripts/S6_1_step2_nonnegative.py --help``
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
    DEFAULT_S1_CORE_MONEYNESS_ABS_MAX,
    DEFAULT_S1_MIN_Q_FLOOR,
    DEFAULT_S1_NONNEG_SCOPE,
    DEFAULT_S1_SMALL_NEG_BAND,
    ETH_IV_SURFACE_FULL_DIR,
    ETH_IV_SURFACE_MON_STEP_SUBDIR,
    ETH_PROCESSED_MONEYNESS_CSV,
    ETH_Q_FILTER_MON_STEP_SUBDIR,
    ETH_Q_FILTER_PLOT_OUT_DIR,
    ETH_Q_MATRIX_MON_STEP_SUBDIR,
    ETH_Q_MATRIX_OUT_DIR,
    _GRID_D15,
    _GRID_FULL,
    _s61_trapz,
    intermediate_path,
    load_obs_moneyness,
    load_q_csv,
    plot_combined_curves,
    plot_min_q_histogram,
    plot_s1_argmin_m_where_full_min_negative,
    plot_single_curve,
    repair_q_density_column,
    s61_min_q_and_argmin_m,
    save_q_csv,
    step_subdirs,
    write_filter_standard,
    _safe_ceil_max,
)

# |m|<=0.15 slice on full grid (aligns with _GRID_D15)
_MASK_D15_ON_FULL = np.abs(_GRID_FULL) <= 0.15 + 1e-12


def _min_q_on_abs_m_lt(q_col: np.ndarray, grid: np.ndarray, cap: float) -> float:
    mask = np.abs(grid) < float(cap)
    if not np.any(mask):
        return float("nan")
    return float(np.nanmin(q_col[mask]))


def run_step2_nonneg(
    ttm: int,
    *,
    matrix_dir: Path,
    plot_root: Path,
    iv_surface_dir: Path,
    obs_csv: Path,
    nonneg_scope: str = DEFAULT_S1_NONNEG_SCOPE,
    core_moneyness_abs_max: float = DEFAULT_S1_CORE_MONEYNESS_ABS_MAX,
    min_q_floor: float = DEFAULT_S1_MIN_Q_FLOOR,
    small_neg_band: float = DEFAULT_S1_SMALL_NEG_BAND,
) -> Tuple[Optional[Path], Optional[Path]]:
    """
    Read ``after_S0``; return ``(Q_after_S1_csv, Q_d15_after_S1_csv)`` or ``(None, None)``.

    ``nonneg_scope``: ``repaired_core`` = repair endpoints / tiny negatives, renormalize, then pass iff
    ``min(q)>=floor`` on strict ``|m|<core_moneyness_abs_max``. ``full`` / ``core`` = legacy (no repair).
    """
    inp = intermediate_path(matrix_dir, ttm, "after_S0")
    if not inp.is_file():
        print(f"  missing {inp} (run S6_1_step1_stack first)", file=sys.stderr)
        return None, None
    df, _ = load_q_csv(inp)
    date_strs: List[str] = list(df.columns)
    q_arr = df.to_numpy(dtype=float)
    n_dates = q_arr.shape[1]

    pd0 = intermediate_path(matrix_dir, ttm, "d15_after_S0")
    q_d15: Optional[np.ndarray] = None
    if pd0.is_file():
        ddf, _ = load_q_csv(pd0)
        q_d15 = ddf.to_numpy(dtype=float)

    combined_dir = plot_root / f"Combined_tau_{ttm}"
    passed_dir, excl_dir, std_dir = step_subdirs(
        combined_dir, 1, "S1_nonnegative_passed", "S1_negative_excluded"
    )
    for d in (passed_dir, excl_dir, std_dir):
        d.mkdir(parents=True, exist_ok=True)

    tol = 1e-6
    df_obs = load_obs_moneyness(obs_csv) if obs_csv.is_file() else pd.DataFrame(
        columns=["date", "moneyness", "tau", "IV"]
    )

    scope = nonneg_scope.strip().lower()
    if scope not in ("full", "core", "repaired_core"):
        print(
            f"  error: nonneg_scope must be 'full', 'core', or 'repaired_core', got {nonneg_scope!r}",
            file=sys.stderr,
        )
        return None, None

    all_idx = list(range(n_dates))
    min_q_full = np.full(n_dates, np.nan, dtype=float)
    min_q_core = np.full(n_dates, np.nan, dtype=float)
    m_at_argmin_full = np.full(n_dates, np.nan, dtype=float)
    rule_min = np.full(n_dates, np.nan, dtype=float)
    min_q_after_repair_full = np.full(n_dates, np.nan, dtype=float)
    min_q_after_repair_core_lt = np.full(n_dates, np.nan, dtype=float)
    integ_after_repair = np.full(n_dates, np.nan, dtype=float)
    pass_mask = np.zeros(n_dates, dtype=bool)
    q_fixed = q_arr.copy()

    for j in all_idx:
        col = q_arr[:, j]
        if not np.all(np.isfinite(col)):
            continue
        mf, maf = s61_min_q_and_argmin_m(col, _GRID_FULL, core_abs_max=None)
        mc, _ = s61_min_q_and_argmin_m(
            col, _GRID_FULL, core_abs_max=core_moneyness_abs_max
        )
        min_q_full[j] = mf
        min_q_core[j] = mc
        m_at_argmin_full[j] = maf

        if scope == "repaired_core":
            qf = repair_q_density_column(
                col, _GRID_FULL, small_neg_band=small_neg_band
            )
            q_fixed[:, j] = qf
            integ = _s61_trapz(qf, _GRID_FULL)
            integ_after_repair[j] = integ
            min_q_after_repair_full[j] = float(np.nanmin(qf))
            min_q_after_repair_core_lt[j] = _min_q_on_abs_m_lt(
                qf, _GRID_FULL, core_moneyness_abs_max
            )
            rule_min[j] = min_q_after_repair_core_lt[j]
            if integ <= 0 or not np.isfinite(integ):
                pass_mask[j] = False
            else:
                pass_mask[j] = bool(rule_min[j] >= min_q_floor)
        elif scope == "full":
            rule_min[j] = mf
            pass_mask[j] = bool(mf >= min_q_floor)
        else:
            rule_min[j] = mc
            pass_mask[j] = bool(mc >= min_q_floor)

    nonneg_idx = [i for i in all_idx if pass_mask[i]]
    neg_idx = [i for i in all_idx if not pass_mask[i]]

    hist_title = (
        f"min(q) per column — rule={scope}"
        + (
            f" (|m|<{core_moneyness_abs_max:g} after repair)"
            if scope == "repaired_core"
            else (f" (|m|<={core_moneyness_abs_max:g})" if scope == "core" else " (full grid)")
        )
        + f"; pass if >= {min_q_floor:g}"
    )
    plot_min_q_histogram(
        rule_min,
        std_dir / "S1_min_q_distribution.png",
        floor=min_q_floor,
        title=hist_title,
        xlabel="min(q) used in nonnegative rule",
    )

    has_neg_on_full_grid = min_q_full < 0
    if np.any(has_neg_on_full_grid):
        plot_s1_argmin_m_where_full_min_negative(
            m_at_argmin_full[has_neg_on_full_grid],
            std_dir / "S1_argmin_m_where_full_min_negative.png",
            core_abs_max=core_moneyness_abs_max,
        )

    per_col = {
        "date": date_strs,
        "min_q_full_grid": min_q_full,
        "min_q_core_band": min_q_core,
        "m_at_argmin_full": m_at_argmin_full,
        "min_q_rule": rule_min,
        "pass": pass_mask,
    }
    if scope == "repaired_core":
        per_col["min_q_after_repair_full"] = min_q_after_repair_full
        per_col["min_q_after_repair_core_lt"] = min_q_after_repair_core_lt
        per_col["integral_after_repair"] = integ_after_repair
    pd.DataFrame(per_col).to_csv(std_dir / "S1_per_column_min_q.csv", index=False)

    n_any_neg_full = int(np.sum(min_q_full < 0))
    mask_neg = min_q_full < 0
    frac_tail = (
        float(np.mean(np.abs(m_at_argmin_full[mask_neg]) > core_moneyness_abs_max))
        if n_any_neg_full
        else float("nan")
    )

    if scope == "repaired_core":
        rationale = (
            f"[S1 nonnegative]\n"
            f"Rule: nonneg_scope={scope!r}. "
            f"Per column: m=±1 negatives → 0; q with -{small_neg_band:g} < q < 0 → 0; trapezoid renormalize on full grid. "
            f"Pass iff integral>0 and min(q) on strict |m|<{core_moneyness_abs_max:g} >= {min_q_floor:g}.\n"
            f"Saved after_S1 columns are repaired densities; d15_after_S1 is sliced from repaired full grid.\n"
            f"Diagnostics: S1_per_column_min_q.csv; "
            f"S1_argmin_m_where_full_min_negative.png (raw min q locations before repair).\n"
            f"This run: days with raw min(q)<0 on full grid: {n_any_neg_full}/{n_dates}; "
            f"among those, frac |argmin m|>{core_moneyness_abs_max:g}: {frac_tail:.3f}.\n"
        )
    else:
        rationale = (
            f"[S1 nonnegative]\n"
            f"Rule: nonneg_scope={scope!r}. "
            f"full = min(q) on full grid; core = min(q) only on |m|<={core_moneyness_abs_max:g} (no repair).\n"
            f"Pass when min(q) used in rule >= {min_q_floor:g} (floor).\n"
            f"Diagnostics: S1_per_column_min_q.csv (all days); "
            f"S1_argmin_m_where_full_min_negative.png: m at argmin(q) on full grid, "
            f"only for days with min(q)<0 on full grid (shows where negatives sit).\n"
            f"This run: days with any min(q)<0 on full grid: {n_any_neg_full}/{n_dates}; "
            f"among those, frac |argmin m|>{core_moneyness_abs_max:g}: {frac_tail:.3f} "
            f"(0.95 vs 0.99: compare core-band fail counts in logs; boundary mass often at m=±1).\n"
        )
    write_filter_standard(std_dir, rationale)

    if nonneg_idx:
        plot_combined_curves(
            indices=nonneg_idx,
            Q_array=q_fixed,
            date_strs=date_strs,
            grid_full=_GRID_FULL,
            ttm=ttm,
            iv_surface_dir=iv_surface_dir,
            df_obs=df_obs,
            tol=tol,
            left_title=f"S1 nonnegative passed ({len(nonneg_idx)})",
            right_title="IV",
            suptitle=f"S1 nonnegative passed TTM={ttm}",
            save_path=passed_dir / f"all_passed_S1_{ttm}day.png",
            xlim=(-1, 1),
            ylim_left=(0, _safe_ceil_max(q_fixed, nonneg_idx)),
        )
        for i in nonneg_idx:
            plot_single_curve(
                i, q_fixed, date_strs, _GRID_FULL, ttm, iv_surface_dir, df_obs, tol,
                passed_dir, group_label="S1_nonnegative_passed",
            )
    if neg_idx:
        plot_combined_curves(
            indices=neg_idx,
            Q_array=q_fixed,
            date_strs=date_strs,
            grid_full=_GRID_FULL,
            ttm=ttm,
            iv_surface_dir=iv_surface_dir,
            df_obs=df_obs,
            tol=tol,
            left_title=f"S1 negative excluded ({len(neg_idx)})",
            right_title="IV",
            suptitle=f"S1 negative excluded TTM={ttm}",
            save_path=excl_dir / f"all_excluded_S1_{ttm}day.png",
            xlim=(-1, 1),
            ylim_left=(
                float(np.floor(np.nanmin(q_fixed[:, neg_idx]))),
                float(np.ceil(np.nanmax(q_fixed[:, neg_idx]))),
            ),
        )
        for i in neg_idx:
            plot_single_curve(
                i, q_fixed, date_strs, _GRID_FULL, ttm, iv_surface_dir, df_obs, tol,
                excl_dir, group_label="S1_negative_excluded",
            )

    excl_base = {
        "date": [date_strs[i] for i in neg_idx],
        "min_q_rule": [float(rule_min[i]) for i in neg_idx],
        "min_q_full_grid": [float(min_q_full[i]) for i in neg_idx],
        "min_q_core_band": [float(min_q_core[i]) for i in neg_idx],
        "m_at_argmin_full": [float(m_at_argmin_full[i]) for i in neg_idx],
    }
    if scope == "repaired_core":
        excl_base["min_q_after_repair_core_lt"] = [
            float(min_q_after_repair_core_lt[i]) for i in neg_idx
        ]
        excl_base["integral_after_repair"] = [float(integ_after_repair[i]) for i in neg_idx]
    pd.DataFrame(excl_base).to_csv(std_dir / "excluded_dates.csv", index=False)
    pd.DataFrame({"date": [date_strs[i] for i in nonneg_idx]}).to_csv(std_dir / "passed_dates.csv", index=False)

    dates_pass = [date_strs[i] for i in nonneg_idx]
    Q1 = q_fixed[:, nonneg_idx]
    p1 = intermediate_path(matrix_dir, ttm, "after_S1")
    pd1 = intermediate_path(matrix_dir, ttm, "d15_after_S1")
    save_q_csv(Q1, _GRID_FULL, dates_pass, p1)
    if scope == "repaired_core":
        Qd1 = q_fixed[_MASK_D15_ON_FULL, :][:, nonneg_idx]
        save_q_csv(Qd1, _GRID_D15, dates_pass, pd1)
    elif q_d15 is not None:
        Qd1 = q_d15[:, nonneg_idx]
        save_q_csv(Qd1, _GRID_D15, dates_pass, pd1)
    else:
        pd1 = None

    print(f"  S6_1 step2 nonnegative ttm={ttm}: {len(dates_pass)}/{n_dates} passed -> {p1.name}")
    return p1, pd1


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "S6_1 step 2: nonnegative filter on stacked Q. "
            "Reads intermediate/Q_after_S0_{ttm}day.csv; writes Q_after_S1_* and S1_filter_standard diagnostics."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Prerequisite: run S6_1_step1_stack for each TTM so that "
            "intermediate/Q_after_S0_{ttm}day.csv exists under --matrix-dir."
        ),
    )
    p.add_argument(
        "--ttm",
        type=int,
        nargs="+",
        required=True,
        metavar="DAYS",
        help=(
            "One or more time-to-maturity horizons in days, space-separated "
            "(e.g. --ttm 27 or --ttm 9 27 45). Matches tau_{ttm} in S6_0 and intermediate filenames."
        ),
    )
    p.add_argument(
        "--matrix-dir",
        type=Path,
        default=ETH_Q_MATRIX_OUT_DIR / ETH_Q_MATRIX_MON_STEP_SUBDIR,
        help=(
            "Root for Q_matrix outputs; must contain intermediate/Q_after_S0_{ttm}day.csv "
            "and receives intermediate/Q_after_S1_{ttm}day.csv (default: function.ETH_Q_MATRIX_*)."
        ),
    )
    p.add_argument(
        "--plot-root",
        type=Path,
        default=ETH_Q_FILTER_PLOT_OUT_DIR / ETH_Q_FILTER_MON_STEP_SUBDIR,
        help=(
            "Q_filter_plot root (moneyness_step_0d01); writes Combined_tau_{ttm}/S1_* (default: function.ETH_Q_FILTER_PLOT_*)."
        ),
    )
    p.add_argument(
        "--iv-surface-dir",
        type=Path,
        default=ETH_IV_SURFACE_FULL_DIR / ETH_IV_SURFACE_MON_STEP_SUBDIR,
        help="IV surface CSVs for optional IV overlay on diagnostic plots (default: function.ETH_IV_SURFACE_*).",
    )
    p.add_argument(
        "--obs-csv",
        type=Path,
        default=ETH_PROCESSED_MONEYNESS_CSV,
        help="Observed IV long table (date, tau, moneyness, IV) for scatter on plots (default: eth_processed_moneyness path).",
    )
    p.add_argument(
        "--nonneg-scope",
        choices=("repaired_core", "full", "core"),
        default=DEFAULT_S1_NONNEG_SCOPE,
        help=(
            "repaired_core: repair endpoints/tiny negatives, renorm, pass on strict |m|<core band; "
            f"full/core: legacy (no repair). Core band default {DEFAULT_S1_CORE_MONEYNESS_ABS_MAX:g}"
        ),
    )
    p.add_argument(
        "--core-moneyness-abs-max",
        type=float,
        default=DEFAULT_S1_CORE_MONEYNESS_ABS_MAX,
        help=(
            "repaired_core: pass on min(q) over strict |m|<this; core: inclusive |m|<=this. "
            "Try 0.95 vs 0.99 after S1_argmin_m plot."
        ),
    )
    p.add_argument(
        "--min-q-floor",
        type=float,
        default=DEFAULT_S1_MIN_Q_FLOOR,
        help="Pass if rule min(q) >= this (default -1e-6 for repaired_core).",
    )
    p.add_argument(
        "--small-neg-band",
        type=float,
        default=DEFAULT_S1_SMALL_NEG_BAND,
        help="repaired_core: set q=0 where -band < q < 0 (default 0.01), then renorm.",
    )
    args = p.parse_args()
    md = args.matrix_dir.resolve()
    pr = args.plot_root.resolve()
    ivd = args.iv_surface_dir.resolve()
    obs = args.obs_csv.resolve()
    for ttm in args.ttm:
        run_step2_nonneg(
            ttm,
            matrix_dir=md,
            plot_root=pr,
            iv_surface_dir=ivd,
            obs_csv=obs,
            nonneg_scope=args.nonneg_scope,
            core_moneyness_abs_max=args.core_moneyness_abs_max,
            min_q_floor=args.min_q_floor,
            small_neg_band=args.small_neg_band,
        )


if __name__ == "__main__":
    main()
