#!/usr/bin/env python3
"""
E2：S1 合并后长表 ``eth_options_fullsample.csv`` 的**整表**描述性统计。

一次 ``pandas.read_csv`` 读入全表，再 ``describe()``、``value_counts`` 等；分位数与矩量均为**总体精确**
（在 pandas 浮点语义下）。适合内存能容纳整表的情形（约 2.5GB CSV 常需数倍 RAM）。

**TTM（剩余期限）**：由 ``instrument_name`` 解析到期日（与 ``S2_trades_to_chain_daily.py`` 同一规则），
``TTM = (expiry - trade_date)`` 的**日历天数**；仅统计 ``expiry > trade_date`` 的成交（与 S2 筛选一致）。
输出包含分箱频数表（直方图）、分位数表与阈值累积占比表（CDF），可选 ``--plot-ttm`` 保存 PNG。

默认路径：``data/eth_options_processed/eth_options_fullsample.csv``。

用法::

    python scripts/E2_descriptive_stats_s1_merged.py
    python scripts/E2_descriptive_stats_s1_merged.py --csv path/to/file.csv

将结果写回 ``descriptive_stats_report.md`` 中 ``<!-- E2_AUTO_BEGIN -->`` … ``<!-- E2_AUTO_END -->`` 之间::

    python scripts/E2_descriptive_stats_s1_merged.py --write-report
    python scripts/E2_descriptive_stats_s1_merged.py --write-report --plot-ttm
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

DEFAULT_CSV = _ROOT / "data" / "eth_options_processed" / "eth_options_fullsample.csv"
DEFAULT_REPORT_MD = _ROOT / "descriptive_stats_report.md"

NUM_COLS = ["amount", "contracts", "index_price", "iv", "mark_price", "price"]

MARK_BEGIN = "<!-- E2_AUTO_BEGIN -->"
MARK_END = "<!-- E2_AUTO_END -->"

# TTM 直方图分箱（日历天，左闭右开，最后一档右闭）；与 PRIMARY_TTMS 等对照便于阅读
_DEFAULT_TTM_BIN_EDGES = (0, 7, 14, 21, 30, 45, 60, 90, 120, 180, 365, 10_000)


def _load_parse_eth_option_instrument() -> Callable[[Any], Any]:
    """与 S2 相同的合约解析，避免重复维护正则（通过文件路径加载模块）。"""
    mod_path = _ROOT / "scripts" / "S2_trades_to_chain_daily.py"
    spec = importlib.util.spec_from_file_location("_s2_trades_chain_e2", mod_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载 {mod_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.parse_eth_option_instrument


def _expiry_map_unique(
    names: pd.Series, parse_fn: Callable[[Any], Any]
) -> Dict[str, pd.Timestamp]:
    """仅对唯一 instrument_name 调用解析，再 map 回全表。"""
    out: Dict[str, pd.Timestamp] = {}
    for u in names.dropna().unique():
        if not isinstance(u, str):
            continue
        parsed = parse_fn(u)
        out[u] = parsed[0] if parsed is not None else pd.NaT  # type: ignore[arg-type]
    return out


def _compute_ttm_calendar_days(df: pd.DataFrame) -> Tuple[pd.Series, dict]:
    """
    返回 (ttm_days, meta)。
    ttm_days：仅 ``expiry > trade_date`` 处为整数天，其余为 NaN。
    """
    parse_fn = _load_parse_eth_option_instrument()
    exp_map = _expiry_map_unique(df["instrument_name"], parse_fn)
    expiry = df["instrument_name"].map(exp_map)
    td = pd.to_datetime(df["trade_date"], errors="coerce").dt.normalize()
    expiry = pd.to_datetime(expiry, errors="coerce").dt.normalize()

    parsed_ok = expiry.notna()
    time_ok = td.notna()
    positive_maturity = expiry > td
    use = parsed_ok & time_ok & positive_maturity
    ttm = (expiry - td).dt.days.astype("float")
    ttm = ttm.where(use)

    meta = {
        "n_rows": int(len(df)),
        "n_parse_fail": int((~parsed_ok).sum()),
        "n_missing_trade_date": int((~time_ok).sum()),
        "n_expiry_not_after_trade": int((parsed_ok & time_ok & ~positive_maturity).sum()),
        "n_ttm_defined": int(use.sum()),
    }
    return ttm, meta


def _ttm_histogram_table(ttm: pd.Series, bin_edges: Tuple[int, ...]) -> pd.DataFrame:
    """分箱频数 + 占比 + 累积占比（CDF 阶梯，按箱序）。"""
    s = ttm.dropna().astype(int)
    if s.empty:
        return pd.DataFrame(
            columns=["bin_days", "count", "pct", "cdf_pct"]
        )
    edges = list(bin_edges)
    mx = int(s.max())
    if edges[-1] <= mx:
        edges[-1] = mx + 1
    counts, _ = np.histogram(s, bins=edges)
    total = int(s.shape[0])
    pct = 100.0 * counts / total
    cdf = np.cumsum(pct)
    labels = []
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        if i < len(edges) - 2:
            labels.append(f"[{lo}, {hi})")
        else:
            labels.append(f"[{lo}, {hi}]")
    return pd.DataFrame(
        {"bin_days": labels, "count": counts.astype(int), "pct": np.round(pct, 3), "cdf_pct": np.round(cdf, 3)}
    )


def _ttm_cdf_by_threshold(ttm: pd.Series, thresholds: Tuple[int, ...]) -> pd.DataFrame:
    s = ttm.dropna()
    if s.empty:
        return pd.DataFrame(columns=["TTM_leq_days", "share_pct"])
    total = len(s)
    rows = []
    for t in thresholds:
        rows.append({"TTM_leq_days": t, "share_pct": round(100.0 * (s <= t).sum() / total, 3)})
    return pd.DataFrame(rows)


def _ttm_quantile_table(ttm: pd.Series) -> pd.DataFrame:
    s = ttm.dropna()
    if s.empty:
        return pd.DataFrame(columns=["quantile", "TTM_days"])
    qs = [0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]
    vals = s.quantile(qs)
    return pd.DataFrame({"quantile": [f"{int(q * 100)}%" for q in qs], "TTM_days": np.round(vals.values, 4)})


def _maybe_plot_ttm(ttm: pd.Series, out_path: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("跳过 TTM 图：未安装 matplotlib", file=sys.stderr)
        return
    s = ttm.dropna().astype(float)
    if s.empty:
        print("跳过 TTM 图：无有效 TTM", file=sys.stderr)
        return
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    hi = min(400.0, float(s.quantile(0.995)) + 10)
    ax1.hist(s, bins=80, range=(0, hi), color="steelblue", edgecolor="white", linewidth=0.3)
    ax1.set_xlabel("TTM (calendar days)")
    ax1.set_ylabel("Count")
    ax1.set_title(f"Histogram (0–{hi:.0f} d, ~99.5%ile cap on x)")

    xs = np.sort(s.to_numpy())
    ys = np.arange(1, len(xs) + 1) / len(xs)
    ax2.step(xs, ys, where="post", color="darkred", linewidth=1.2)
    ax2.set_xlim(0, hi)
    ax2.set_ylim(0, 1)
    ax2.set_xlabel("TTM (calendar days)")
    ax2.set_ylabel("F(x) = P(TTM ≤ x)")
    ax2.set_title("Empirical CDF")
    ax2.grid(True, alpha=0.3)

    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Wrote TTM figure: {out_path}", file=sys.stderr)


def _fmt_cell(x) -> str:
    if pd.isna(x):
        return ""
    if isinstance(x, (float, int)) and not isinstance(x, bool):
        if isinstance(x, float) and x.is_integer():
            x = int(x)
        if isinstance(x, int):
            # calendar years should not use thousands separators (e.g. 2019 not 2,019)
            if 1900 <= x <= 2100:
                return str(x)
            return f"{x:,}"
        return f"{x:.6g}"
    return str(x)


def _md_table(df: pd.DataFrame) -> str:
    """Simple GitHub-flavored markdown table (no tabulate)."""
    cols = list(df.columns)
    lines = [
        "| " + " | ".join(str(c) for c in cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(_fmt_cell(v) for v in row) + " |")
    return "\n".join(lines)


def compute_stats(df: pd.DataFrame, csv_path: Path) -> dict:
    n = len(df)
    dt = pd.to_datetime(df["datetime"], errors="coerce")
    td = df["trade_date"]
    mem_gb = df.memory_usage(deep=True).sum() / 1e9

    num = df[NUM_COLS]
    raw_desc = num.describe(percentiles=[0.25, 0.5, 0.75])
    # quartiles live on the **index** (rows) of describe(); normalize labels for markdown
    qmap = {"25%": "p25", "50%": "p50", "75%": "p75"}
    raw_desc = raw_desc.rename(index={k: v for k, v in qmap.items() if k in raw_desc.index})
    raw_desc.index.name = "Statistic"
    desc_for_print = raw_desc.T  # variables × stats (stdout)
    desc_for_md = raw_desc.reset_index()

    direction_vc = df["direction"].value_counts(dropna=False)
    year_vc = df["year"].value_counts()

    ttm, ttm_meta = _compute_ttm_calendar_days(df)
    ttm_ok = ttm.dropna()
    if len(ttm_ok):
        ttm_desc_s = ttm_ok.describe(percentiles=[0.25, 0.5, 0.75])
        ttm_desc_s = ttm_desc_s.rename(
            index={k: v for k, v in {"25%": "p25", "50%": "p50", "75%": "p75"}.items() if k in ttm_desc_s.index}
        )
        ttm_desc_s.index.name = "Statistic"
        ttm_desc_print = ttm_desc_s.to_frame(name="TTM_days").T
        ttm_desc_md = ttm_desc_s.reset_index()
        ttm_desc_md.columns = ["Statistic", "TTM_days"]
    else:
        ttm_desc_print = pd.DataFrame()
        ttm_desc_md = pd.DataFrame(columns=["Statistic", "TTM_days"])

    ttm_hist_md = _ttm_histogram_table(ttm, _DEFAULT_TTM_BIN_EDGES)
    ttm_cdf_thresholds_md = _ttm_cdf_by_threshold(ttm, (7, 14, 21, 30, 45, 60, 90, 120, 180, 365))
    ttm_quant_md = _ttm_quantile_table(ttm)

    return {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "csv_path": str(csv_path),
        "n_rows": n,
        "n_cols": len(df.columns),
        "mem_gb": mem_gb,
        "unique_trade_date": int(td.nunique()),
        "unique_instrument": int(df["instrument_name"].nunique()),
        "unique_source_file": int(df["source_file"].nunique()),
        "dt_min": str(dt.min()),
        "dt_max": str(dt.max()),
        "td_min": str(td.min()),
        "td_max": str(td.max()),
        "direction_vc": direction_vc,
        "year_vc": year_vc,
        "desc": desc_for_print,
        "desc_md": desc_for_md,
        "miss_contracts": int(df["contracts"].isna().sum()),
        "miss_mark_price": int(df["mark_price"].isna().sum()),
        "n": n,
        "ttm_meta": ttm_meta,
        "ttm_desc_print": ttm_desc_print,
        "ttm_desc_md": ttm_desc_md,
        "ttm_hist_md": ttm_hist_md,
        "ttm_cdf_thresholds_md": ttm_cdf_thresholds_md,
        "ttm_quant_md": ttm_quant_md,
        "ttm": ttm,
    }


def print_stdout(st: dict) -> None:
    print("=== S1 merged descriptive statistics (full table in memory) ===")
    print(f"CSV: {st['csv_path']}")
    print(f"Rows: {st['n_rows']:,}  Columns: {st['n_cols']}")
    print(f"Memory usage (DataFrame): {st['mem_gb']:.2f} GB (deep=True)")
    print()
    print(f"Unique trade_date: {st['unique_trade_date']:,}")
    print(f"Unique instrument_name: {st['unique_instrument']:,}")
    print(f"Unique source_file: {st['unique_source_file']}")
    print(f"datetime: {st['dt_min']} .. {st['dt_max']}")
    print(f"trade_date: {st['td_min']} .. {st['td_max']}")
    print()
    print("=== direction ===")
    for k, v in st["direction_vc"].items():
        print(f"  {k}: {v:,} ({100 * v / st['n']:.2f}%)")
    print()
    print("=== rows by year ===")
    for y, c in sorted(st["year_vc"].items(), key=lambda x: int(x[0])):
        print(f"  {int(y)}: {c:,}")
    print()
    print("=== pandas.describe() — numeric columns ===")
    with pd.option_context("display.max_columns", None, "display.width", 200):
        print(st["desc"].round(6).to_string())
    print()
    print(f"Missing contracts: {st['miss_contracts']:,} rows")
    print(f"Missing mark_price: {st['miss_mark_price']:,} rows")
    print()
    tm = st["ttm_meta"]
    print("=== TTM (calendar days; expiry − trade_date, expiry > trade_date only) ===")
    print(f"  Rows with defined TTM: {tm['n_ttm_defined']:,} / {tm['n_rows']:,}")
    print(f"  instrument parse fail: {tm['n_parse_fail']:,}")
    print(f"  missing trade_date: {tm['n_missing_trade_date']:,}")
    print(f"  expiry ≤ trade_date (excluded): {tm['n_expiry_not_after_trade']:,}")
    if len(st["ttm_desc_print"]) > 0:
        print()
        with pd.option_context("display.max_columns", None, "display.width", 120):
            print(st["ttm_desc_print"].round(4).to_string())
        print()
        print("=== TTM histogram (bin, count, %, cum % = CDF within bins) ===")
        with pd.option_context("display.max_columns", None, "display.width", 120):
            print(st["ttm_hist_md"].to_string(index=False))
        print()
        print("=== TTM empirical CDF at thresholds P(TTM ≤ d) ===")
        with pd.option_context("display.max_columns", None, "display.width", 80):
            print(st["ttm_cdf_thresholds_md"].to_string(index=False))
        print()
        print("=== TTM quantiles ===")
        with pd.option_context("display.max_columns", None, "display.width", 80):
            print(st["ttm_quant_md"].to_string(index=False))


def build_markdown_block(st: dict) -> str:
    lines: list[str] = []
    csv_p = Path(st["csv_path"])
    try:
        csv_disp = f"`{csv_p.resolve().relative_to(_ROOT.resolve())}`"
    except ValueError:
        csv_disp = f"`{csv_p}`"
    lines.append(f"*Generated: {st['generated_utc']} · Source CSV: {csv_disp}*")
    lines.append("")
    lines.append(f"- **Rows:** {st['n_rows']:,} · **Columns:** {st['n_cols']} · **DataFrame memory (deep):** {st['mem_gb']:.2f} GB")
    lines.append(
        f"- **Unique `trade_date`:** {st['unique_trade_date']:,} · **`instrument_name`:** {st['unique_instrument']:,} · **`source_file` shards:** {st['unique_source_file']}"
    )
    lines.append(f"- **`datetime`:** {st['dt_min']} … {st['dt_max']}")
    lines.append(f"- **`trade_date`:** {st['td_min']} … {st['td_max']}")
    lines.append("")
    lines.append("### Rows by `year`")
    lines.append("")
    yr = pd.DataFrame(
        {"year": [int(y) for y, _ in sorted(st["year_vc"].items(), key=lambda x: int(x[0]))], "rows": [int(c) for _, c in sorted(st["year_vc"].items(), key=lambda x: int(x[0]))]}
    )
    lines.append(_md_table(yr))
    lines.append("")
    lines.append("### Direction")
    lines.append("")
    dir_rows = []
    for k, v in st["direction_vc"].items():
        dir_rows.append({"direction": k, "count": int(v), "share_pct": round(100 * v / st["n"], 2)})
    lines.append(_md_table(pd.DataFrame(dir_rows)))
    lines.append("")
    lines.append("### Numeric `describe()` (non-null `count`; pandas default quantiles)")
    lines.append("")
    lines.append(_md_table(st["desc_md"]))
    lines.append("")
    lines.append("### Missing values")
    lines.append("")
    miss = pd.DataFrame(
        {
            "Field": ["`contracts`", "`mark_price`"],
            "missing_rows": [st["miss_contracts"], st["miss_mark_price"]],
        }
    )
    lines.append(_md_table(miss))
    lines.append("")
    tm = st["ttm_meta"]
    lines.append("### TTM (time to maturity, calendar days)")
    lines.append("")
    lines.append(
        "**Definition:** parse `instrument_name` as in `scripts/S2_trades_to_chain_daily.py`; "
        "`TTM = (expiry − trade_date)` in **whole calendar days**; keep rows with **`expiry > trade_date`** only (same as S2)."
    )
    lines.append("")
    lines.append(
        f"- **Defined TTM:** {tm['n_ttm_defined']:,} / {tm['n_rows']:,} rows · "
        f"parse fail: {tm['n_parse_fail']:,} · missing `trade_date`: {tm['n_missing_trade_date']:,} · "
        f"`expiry ≤ trade_date` excluded: {tm['n_expiry_not_after_trade']:,}"
    )
    lines.append("")
    if len(st["ttm_desc_md"]) > 0:
        lines.append("#### `TTM` — `describe()`")
        lines.append("")
        lines.append(_md_table(st["ttm_desc_md"]))
        lines.append("")
    lines.append("#### Histogram (binned counts) and cumulative % within defined TTM")
    lines.append("")
    lines.append(
        "*Bins are half-open `[lo, hi)` except the last interval, which is closed on the right; "
        "`cdf_pct` is cumulative share over all defined TTM rows.*"
    )
    lines.append("")
    lines.append(_md_table(st["ttm_hist_md"]))
    lines.append("")
    lines.append("#### CDF at fixed horizons — share with `TTM ≤ d` days")
    lines.append("")
    lines.append(_md_table(st["ttm_cdf_thresholds_md"]))
    lines.append("")
    lines.append("#### Quantiles of `TTM` (days)")
    lines.append("")
    lines.append(_md_table(st["ttm_quant_md"]))
    lines.append("")
    lines.append(
        "*In the numeric table, each column's `count` is non-null observations only; see **Missing values** for null row counts (e.g. early shards without `contracts`).*"
    )
    return "\n".join(lines)


def write_report_md(md_body: str, report_path: Path) -> None:
    text = report_path.read_text(encoding="utf-8")
    if MARK_BEGIN not in text or MARK_END not in text:
        print(
            f"Error: {report_path} must contain {MARK_BEGIN!r} and {MARK_END!r}",
            file=sys.stderr,
        )
        sys.exit(1)
    pre, rest = text.split(MARK_BEGIN, 1)
    _old, post = rest.split(MARK_END, 1)
    new_text = pre + MARK_BEGIN + "\n\n" + md_body.strip() + "\n\n" + MARK_END + post
    report_path.write_text(new_text, encoding="utf-8")
    print(f"Updated: {report_path}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Full in-memory descriptive stats for S1 merged CSV (E2)."
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Path to merged CSV")
    parser.add_argument(
        "--write-report",
        action="store_true",
        help=f"Write markdown block into {DEFAULT_REPORT_MD.name} (between E2_AUTO markers)",
    )
    parser.add_argument(
        "--report-md",
        type=Path,
        default=DEFAULT_REPORT_MD,
        help="Target markdown file for --write-report",
    )
    parser.add_argument(
        "--plot-ttm",
        action="store_true",
        help="Save histogram + empirical CDF of TTM (needs matplotlib)",
    )
    parser.add_argument(
        "--ttm-plot-path",
        type=Path,
        default=_ROOT / "figures" / "e2_ttm_distribution.png",
        help="Output PNG when --plot-ttm is set",
    )
    args = parser.parse_args()

    csv_path = args.csv.resolve()
    if not csv_path.exists():
        print(f"File not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading entire CSV into memory: {csv_path}", file=sys.stderr)
    df = pd.read_csv(csv_path, low_memory=False)

    st = compute_stats(df, csv_path)
    print_stdout(st)

    if args.plot_ttm:
        _maybe_plot_ttm(st["ttm"], args.ttm_plot_path)

    if args.write_report:
        block = build_markdown_block(st)
        write_report_md(block, args.report_md.resolve())


if __name__ == "__main__":
    main()
