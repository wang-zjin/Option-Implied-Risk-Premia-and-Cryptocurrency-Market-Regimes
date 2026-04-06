#!/usr/bin/env python3
"""
E3：S2 日度期权链面板 ``eth_options_chain_daily.csv`` 的描述性统计。

S2 输出：``(date, expiry, K)`` 一行一点（可选 ``option_type``），列含 ``spot``, ``IV``（年化小数）,
``quantity``（权重和）, ``n_trades``。默认读 ``function.ETH_OPTIONS_CHAIN_DAILY_CSV``。

用法::

    python scripts/E3_descriptive_stats_s2_chain.py
    python scripts/E3_descriptive_stats_s2_chain.py --csv path/to/chain.csv

写回 ``descriptive_stats_report.md`` 中 ``<!-- S2_AUTO_BEGIN -->`` … ``<!-- S2_AUTO_END -->``::

    python scripts/E3_descriptive_stats_s2_chain.py --write-report
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from function import ETH_OPTIONS_CHAIN_DAILY_CSV

MARK_BEGIN = "<!-- S2_AUTO_BEGIN -->"
MARK_END = "<!-- S2_AUTO_END -->"
DEFAULT_REPORT_MD = _ROOT / "descriptive_stats_report.md"

# S2 输出中的连续变量
NUM_COLS_BASE = ["K", "spot", "IV", "quantity", "n_trades"]


def _fmt_cell(x) -> str:
    if pd.isna(x):
        return ""
    if isinstance(x, (float, int)) and not isinstance(x, bool):
        if isinstance(x, float) and x.is_integer():
            x = int(x)
        if isinstance(x, int):
            if 1900 <= x <= 2100:
                return str(x)
            return f"{x:,}"
        return f"{x:.6g}"
    return str(x)


def _md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = [
        "| " + " | ".join(str(c) for c in cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(_fmt_cell(v) for v in row) + " |")
    return "\n".join(lines)


def _write_auto_block(report_path: Path, md_body: str, begin: str, end: str) -> None:
    text = report_path.read_text(encoding="utf-8")
    if begin not in text or end not in text:
        print(
            f"Error: {report_path} must contain {begin!r} and {end!r}",
            file=sys.stderr,
        )
        sys.exit(1)
    pre, rest = text.split(begin, 1)
    _old, post = rest.split(end, 1)
    new_text = pre + begin + "\n\n" + md_body.strip() + "\n\n" + end + post
    report_path.write_text(new_text, encoding="utf-8")
    print(f"Updated: {report_path}", file=sys.stderr)


def compute_stats(df: pd.DataFrame, csv_path: Path) -> dict:
    n = len(df)
    mem_gb = df.memory_usage(deep=True).sum() / 1e9

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["expiry"] = pd.to_datetime(df["expiry"], errors="coerce")

    num_cols = [c for c in NUM_COLS_BASE if c in df.columns]
    raw_desc = df[num_cols].describe(percentiles=[0.25, 0.5, 0.75])
    raw_desc = raw_desc.rename(
        index={k: v for k, v in {"25%": "p25", "50%": "p50", "75%": "p75"}.items() if k in raw_desc.index}
    )
    raw_desc.index.name = "Statistic"
    desc_md = raw_desc.reset_index()

    year_vc = df["date"].dt.year.value_counts()

    nulls = df.isnull().sum()
    miss_rows = nulls[nulls > 0]

    out = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "csv_path": str(csv_path.resolve()),
        "n_rows": n,
        "n_cols": len(df.columns),
        "mem_gb": mem_gb,
        "columns": list(df.columns),
        "date_min": str(df["date"].min()),
        "date_max": str(df["date"].max()),
        "expiry_min": str(df["expiry"].min()),
        "expiry_max": str(df["expiry"].max()),
        "unique_date": int(df["date"].nunique()),
        "unique_expiry": int(df["expiry"].nunique()),
        "unique_K": int(df["K"].nunique()) if "K" in df.columns else 0,
        "year_vc": year_vc,
        "desc_md": desc_md,
        "miss_rows": miss_rows,
        "option_type_vc": df["option_type"].value_counts(dropna=False) if "option_type" in df.columns else None,
    }
    return out


def print_stdout(st: dict) -> None:
    print("=== S2 chain daily — descriptive statistics (E3) ===")
    print(f"CSV: {st['csv_path']}")
    print(f"Rows: {st['n_rows']:,}  Columns: {st['n_cols']} {st['columns']}")
    print(f"Memory (deep): {st['mem_gb']:.3f} GB")
    print()
    print(f"date: {st['date_min']} .. {st['date_max']}  (unique: {st['unique_date']:,})")
    print(f"expiry: {st['expiry_min']} .. {st['expiry_max']}  (unique: {st['unique_expiry']:,})")
    print(f"Unique K: {st['unique_K']:,}")
    print()
    if st["option_type_vc"] is not None:
        print("=== option_type ===")
        print(st["option_type_vc"].to_string())
        print()
    print("=== rows by calendar year (date) ===")
    for y, c in sorted(st["year_vc"].items(), key=lambda x: int(x[0])):
        print(f"  {int(y)}: {c:,}")
    print()
    print("=== describe() — numeric ===")
    with pd.option_context("display.max_columns", None, "display.width", 200):
        print(st["desc_md"].set_index("Statistic").round(8).to_string())
    print()
    if len(st["miss_rows"]):
        print("=== non-zero missing counts ===")
        print(st["miss_rows"].to_string())
    else:
        print("No missing values in any column.")


def build_markdown_block(st: dict) -> str:
    csv_p = Path(st["csv_path"])
    try:
        csv_disp = f"`{csv_p.resolve().relative_to(_ROOT.resolve())}`"
    except ValueError:
        csv_disp = f"`{csv_p}`"

    lines: list[str] = []
    lines.append(f"*Generated: {st['generated_utc']} · Source: {csv_disp}*")
    lines.append("")
    lines.append(
        f"- **Rows:** {st['n_rows']:,} · **Columns:** {st['n_cols']} · **Memory (deep):** {st['mem_gb']:.3f} GB"
    )
    lines.append(f"- **Columns:** `{', '.join(st['columns'])}`")
    lines.append(
        f"- **`date`:** {st['date_min']} … {st['date_max']} · **unique trading days:** {st['unique_date']:,}"
    )
    lines.append(
        f"- **`expiry`:** {st['expiry_min']} … {st['expiry_max']} · **unique expiries:** {st['unique_expiry']:,}"
    )
    lines.append(f"- **Unique strikes `K`:** {st['unique_K']:,}")
    lines.append("")
    if st["option_type_vc"] is not None:
        lines.append("### `option_type`")
        lines.append("")
        ot = pd.DataFrame(
            {
                "option_type": st["option_type_vc"].index.astype(str),
                "count": st["option_type_vc"].values.astype(int),
            }
        )
        lines.append(_md_table(ot))
        lines.append("")
    lines.append("### Rows by calendar year (`date`)")
    lines.append("")
    yr = pd.DataFrame(
        {
            "year": [int(y) for y, _ in sorted(st["year_vc"].items(), key=lambda x: int(x[0]))],
            "rows": [int(c) for _, c in sorted(st["year_vc"].items(), key=lambda x: int(x[0]))],
        }
    )
    lines.append(_md_table(yr))
    lines.append("")
    lines.append("### Numeric `describe()` (`IV` = annualized vol as **decimal**, e.g. 0.8 ≈ 80%)")
    lines.append("")
    lines.append(_md_table(st["desc_md"]))
    lines.append("")
    lines.append("### Missing values (column → null count)")
    lines.append("")
    if len(st["miss_rows"]):
        miss_df = st["miss_rows"].reset_index()
        miss_df.columns = ["column", "null_count"]
        lines.append(_md_table(miss_df))
    else:
        lines.append("*None — all columns complete.*")
    lines.append("")
    lines.append(
        "*One row = one aggregated point `(date, expiry, K)` [+ `option_type` if S2 `separate`]; "
        "`quantity` is weight sum, `n_trades` is trade count in the group.*"
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="E3: descriptive stats for S2 chain-daily CSV.")
    parser.add_argument("--csv", type=Path, default=ETH_OPTIONS_CHAIN_DAILY_CSV, help="S2 output CSV")
    parser.add_argument(
        "--write-report",
        action="store_true",
        help=f"Patch {DEFAULT_REPORT_MD.name} between S2_AUTO markers",
    )
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MD)
    args = parser.parse_args()

    csv_path = args.csv.resolve()
    if not csv_path.exists():
        print(f"File not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading: {csv_path}", file=sys.stderr)
    df = pd.read_csv(csv_path, low_memory=False)

    required = {"date", "expiry", "K", "spot", "IV", "quantity", "n_trades"}
    missing = required - set(df.columns)
    if missing:
        print(f"Error: missing columns {sorted(missing)}", file=sys.stderr)
        sys.exit(1)

    st = compute_stats(df, csv_path)
    print_stdout(st)

    if args.write_report:
        block = build_markdown_block(st)
        _write_auto_block(args.report_md.resolve(), block, MARK_BEGIN, MARK_END)


if __name__ == "__main__":
    main()
