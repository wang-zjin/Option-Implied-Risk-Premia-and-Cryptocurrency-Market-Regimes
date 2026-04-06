#!/usr/bin/env python3
"""
E6_2: Plot EVIX by expiry tau (TTM), vs same-tau BVIX (btc_vix_EWA) and DVOL (VIX_DVOL.csv).

Tenor note (DVOL vs EWA VIX)
----------------------------
**DVOL** (Deribit BTC Volatility Index from ``VIX_DVOL.csv``) is the exchange index: ~**30 calendar days**
forward implied vol (variance-swap style, interpolated between expiries around 30d). It is **not** tied to
the same tau as ``eth_vix_EWA_{tau}`` / ``btc_vix_EWA_{tau}`` (e.g. 9, 27, 45 days). The BTC pipeline
(``SVI_independent_tau/calculate_btc_vix.py``) builds **BVIX** at chosen tau from QW files; **DVOL** is
only read from external CSV like ``prepared_code_0711/BVIX_DVOL_plot.m`` does.

**Comparison figure** plots EVIX, BVIX, and DVOL on the **union** of their calendars (each line uses
its own dates; x-axis spans from the earliest to the latest date across the three series). A separate
**EVIX-only** figure is written per tau.

Inputs
------
- ``results/ETH_VIX/eth_vix_EWA_{tau}.csv``: columns ``Date`` (YYYYMMDD string), ``EMA`` (EVIX)
- ``data/BVIX_DVOL/btc_vix_EWA_{tau}.csv``: columns ``Date``, ``EMA`` (BVIX)
- ``data/BVIX_DVOL/VIX_DVOL.csv``: columns ``DateTime``, DVOL column (name contains DVOL)

Outputs
-------
- ``results/ETH_VIX/compare_with_BVIX/EVIX_BVIX_DVOL_tau_{tau}.png`` - union calendar overlay (default ``--out-dir``)
- ``results/ETH_VIX/EVIX_series/EVIX_tau_{tau}.png`` - EVIX time series only (default ``--evix-series-dir``)
- Optional: ``merged_union_tau_{tau}.csv`` under ``--out-dir`` - outer merge on date (EVIX, BVIX, DVOL columns)

Only taus with both ETH and BTC EWA files are plotted (default: intersection of ``*_EWA_*.csv`` names).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Set

import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from function import ETH_VIX_RESULTS_DIR, PROJECT_ROOT  # noqa: E402

BVIX_DVOL_DIR = PROJECT_ROOT / "data" / "BVIX_DVOL"
VIX_DVOL_CSV = BVIX_DVOL_DIR / "VIX_DVOL.csv"
DEFAULT_OUT_DIR = ETH_VIX_RESULTS_DIR / "compare_with_BVIX"
DEFAULT_EVIX_SERIES_DIR = ETH_VIX_RESULTS_DIR / "EVIX_series"

_EWA_NAME_RE = re.compile(r"^(?:eth|btc)_vix_EWA_(\d+)\.csv$", re.IGNORECASE)


def _parse_date_series(ser: pd.Series) -> pd.Series:
    """Normalize to calendar day (naive); supports ISO and YYYYMMDD."""
    x = ser.astype(str).str.strip()
    out = pd.to_datetime(x, errors="coerce")
    mask = out.isna()
    if mask.any():
        out.loc[mask] = pd.to_datetime(x[mask], format="%Y%m%d", errors="coerce")
    return out.dt.normalize()


def _discover_taus(eth_dir: Path, btc_dir: Path) -> List[int]:
    def taus_from_dir(d: Path, prefix: str) -> Set[int]:
        s: Set[int] = set()
        for p in d.glob(f"{prefix}_vix_EWA_*.csv"):
            m = _EWA_NAME_RE.match(p.name)
            if m:
                s.add(int(m.group(1)))
        return s

    eth = taus_from_dir(eth_dir, "eth")
    btc = taus_from_dir(btc_dir, "btc")
    common = sorted(eth & btc)
    return common


def load_dvol(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "DateTime" not in df.columns:
        raise ValueError(f"missing column DateTime: {path}")
    dvol_col = None
    for c in df.columns:
        if "DVOL" in c.upper() or c.strip().lower().endswith("(dvol)"):
            dvol_col = c
            break
    if dvol_col is None:
        raise ValueError(f"no DVOL column (name should contain DVOL): {path}")
    out = pd.DataFrame(
        {
            "date": _parse_date_series(df["DateTime"]),
            "DVOL": pd.to_numeric(df[dvol_col], errors="coerce"),
        }
    )
    return out.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)


def load_ewa_vix(path: Path, value_name: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "Date" not in df.columns or "EMA" not in df.columns:
        raise ValueError(f"expected columns Date, EMA: {path}")
    out = pd.DataFrame(
        {
            "date": _parse_date_series(df["Date"]),
            value_name: pd.to_numeric(df["EMA"], errors="coerce"),
        }
    )
    return out.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)


def merge_union_outer(
    evix: pd.DataFrame, bvix: pd.DataFrame, dvol: pd.DataFrame
) -> pd.DataFrame:
    """Outer merge on date: all calendar days present in any series."""
    m = evix.merge(bvix, on="date", how="outer")
    m = m.merge(dvol, on="date", how="outer")
    return m.sort_values("date").reset_index(drop=True)


def _configure_matplotlib() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["font.family"] = "DejaVu Sans"
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]


def _xlim_union(*dfs: pd.DataFrame) -> tuple:
    mins: List = []
    maxs: List = []
    for df in dfs:
        if df is not None and not df.empty and "date" in df.columns:
            mins.append(df["date"].min())
            maxs.append(df["date"].max())
    if not mins:
        raise ValueError("no dates for x-axis")
    return min(mins), max(maxs)


def plot_union(
    evix: pd.DataFrame,
    bvix: pd.DataFrame,
    dvol: pd.DataFrame,
    tau: int,
    out_path: Path,
    dpi: int,
) -> None:
    """EVIX, BVIX, DVOL on union of date ranges (each series on its own observation dates)."""
    _configure_matplotlib()
    import matplotlib.pyplot as plt

    xmin, xmax = _xlim_union(evix, bvix, dvol)

    fig, ax = plt.subplots(figsize=(11, 5.5))
    if not evix.empty:
        ax.plot(evix["date"], evix["EVIX"], label="EVIX", linewidth=1.2)
    if not bvix.empty:
        ax.plot(bvix["date"], bvix["BVIX"], label="BVIX", linewidth=1.2, alpha=0.9)
    if not dvol.empty:
        ax.plot(dvol["date"], dvol["DVOL"], label="DVOL", linewidth=1.0, alpha=0.85)
    ax.set_xlim(xmin, xmax)
    ax.set_xlabel("Date")
    ax.set_ylabel("Volatility index (%)")
    ax.set_title(
        f"EVIX vs BVIX vs DVOL (union calendar, tau = {tau} days)"
    )
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)


def plot_evix_only(
    evix: pd.DataFrame,
    tau: int,
    out_path: Path,
    dpi: int,
) -> None:
    """Single series: EVIX only."""
    if evix.empty:
        raise ValueError("EVIX is empty")
    _configure_matplotlib()
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(evix["date"], evix["EVIX"], label="EVIX", linewidth=1.2, color="C0")
    ax.set_xlabel("Date")
    ax.set_ylabel("Volatility index (%)")
    ax.set_title(f"EVIX (tau = {tau} days)")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)


def main(argv: Optional[Iterable[str]] = None) -> int:
    p = argparse.ArgumentParser(description="E6_2: EVIX / BVIX / DVOL by tau")
    p.add_argument(
        "--eth-dir",
        type=Path,
        default=ETH_VIX_RESULTS_DIR,
        help="directory containing eth_vix_EWA_*.csv",
    )
    p.add_argument(
        "--btc-dir",
        type=Path,
        default=BVIX_DVOL_DIR,
        help="directory containing btc_vix_EWA_*.csv",
    )
    p.add_argument(
        "--vix-dvol-csv",
        type=Path,
        default=VIX_DVOL_CSV,
        help="CSV with DateTime and DVOL",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="output directory for union comparison PNG and optional merged_union CSV",
    )
    p.add_argument(
        "--evix-series-dir",
        type=Path,
        default=DEFAULT_EVIX_SERIES_DIR,
        help="output directory for EVIX_tau_{tau}.png only",
    )
    p.add_argument(
        "--tau",
        type=int,
        nargs="*",
        default=None,
        help="tau list in days; default: intersection of EWA filenames in eth-dir and btc-dir",
    )
    p.add_argument("--dpi", type=int, default=150)
    p.add_argument(
        "--save-csv",
        action="store_true",
        help="write merged_union_tau_{tau}.csv (outer join on date) per tau",
    )
    args = p.parse_args(list(argv) if argv is not None else None)

    if not args.vix_dvol_csv.is_file():
        print(f"missing file: {args.vix_dvol_csv}", file=sys.stderr)
        return 1

    taus: List[int]
    if args.tau:
        taus = sorted(set(args.tau))
    else:
        taus = _discover_taus(args.eth_dir, args.btc_dir)
        if not taus:
            print(
                "no common tau found from eth_vix_EWA_*.csv and btc_vix_EWA_*.csv in eth-dir and btc-dir.",
                file=sys.stderr,
            )
            return 1

    dvol = load_dvol(args.vix_dvol_csv)
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    evix_series_dir = args.evix_series_dir
    evix_series_dir.mkdir(parents=True, exist_ok=True)

    ok = 0
    for tau in taus:
        eth_p = args.eth_dir / f"eth_vix_EWA_{tau}.csv"
        btc_p = args.btc_dir / f"btc_vix_EWA_{tau}.csv"
        if not eth_p.is_file():
            print(f"skip tau={tau}: missing {eth_p}", file=sys.stderr)
            continue
        if not btc_p.is_file():
            print(f"skip tau={tau}: missing {btc_p}", file=sys.stderr)
            continue

        evix = load_ewa_vix(eth_p, "EVIX")
        bvix = load_ewa_vix(btc_p, "BVIX")
        if evix.empty:
            print(f"skip tau={tau}: empty EVIX series in {eth_p}", file=sys.stderr)
            continue

        merged = merge_union_outer(evix, bvix, dvol)

        png_union = out_dir / f"EVIX_BVIX_DVOL_tau_{tau}.png"
        plot_union(evix, bvix, dvol, tau, png_union, args.dpi)
        png_evix = evix_series_dir / f"EVIX_tau_{tau}.png"
        plot_evix_only(evix, tau, png_evix, args.dpi)
        print(
            f"tau={tau}: union rows={len(merged)}, "
            f"EVIX {evix['date'].min().date()} - {evix['date'].max().date()} -> {png_union}, {png_evix}"
        )

        if args.save_csv:
            csv_path = out_dir / f"merged_union_tau_{tau}.csv"
            merged.to_csv(csv_path, index=False, encoding="utf-8")
            print(f"  -> {csv_path}")

        ok += 1

    if ok == 0:
        print("no figures written.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
