#!/usr/bin/env python3
"""
S2：成交 → (date, expiry, strike) 日度面板（ETH_risk_premia_plan.md §1.1 步骤 ②）。

从 S1 合并长表（或列兼容的 CSV/Parquet）解析 Deribit ETH 期权 ``instrument_name``，
在 **清洗后、按日聚合前** 可选输出 **逐笔** 描述性统计（对齐 BTC Table 1 式：Call/Put 分列的
TTM / Moneyness / IV）；再按交易日聚合为「一行一点」的 IV 与现货参考价，供 ``S3_prepare_moneyness_eth.py`` 使用。

合约名格式（线性交割期权）：``ETH-{DD}{MMM}{YY}-{strike}-C|P``，例如 ``ETH-26DEC25-11000-C``。

默认 **``merged``**：同一 ``(trade_date, expiry, K)`` 上 **Call 与 Put 成交一并纳入**，按 quantity
做 **加权平均 IV / spot**（与 BTC ``S1_data_prepare_moneyness_unique`` 中按 ``date,tau,moneyness``
合并逻辑一致）。可选仅 Call / 仅 Put，或 ``separate``（分 C/P 两行，供特殊用途）。

IV：Deribit 成交里 ``iv`` 多为 **0–100 百分比**；本脚本默认输出 **小数年化波动**
（除以 100），与 S3 **默认**（不加 ``--iv-already-percent``）一致。

上游：``S1_consolidate_eth_options_parquet.py`` → ``eth_options_fullsample.csv``
下游：``S3_prepare_moneyness_eth.py``（列：date, expiry, K, spot, IV, quantity）
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Tuple

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from function import (
    ETH_OPTIONS_CHAIN_DAILY_CSV,
    ETH_OPTIONS_FULLSAMPLE_CSV,
    ETH_OPTIONS_PROCESSED_DIR,
)

try:
    import pyarrow as pa  # type: ignore
    import pyarrow.parquet as pq  # type: ignore

    _HAS_PYARROW = True
except ImportError:
    _HAS_PYARROW = False

_DEFAULT_OUT = ETH_OPTIONS_CHAIN_DAILY_CSV


def _canonical_option_filter(name: str) -> str:
    """CLI ``both`` 视为 ``separate``（向后兼容）。"""
    if name == "both":
        return "separate"
    return name


_MONTH_MAP = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}

# ETH-26DEC25-11000-C
_INSTRUMENT_RE = re.compile(
    r"^ETH-(\d{1,2})([A-Z]{3})(\d{2})-([\d.]+)-(C|P)$",
    re.IGNORECASE,
)


def parse_eth_option_instrument(name: Any) -> Optional[Tuple[pd.Timestamp, float, str]]:
    """
    解析 Deribit ETH 期权 instrument_name。
    返回 (expiry 日末 normalized Timestamp, strike, 'C'|'P')；失败返回 None。
    """
    if not isinstance(name, str) or not name.strip():
        return None
    m = _INSTRUMENT_RE.match(name.strip())
    if not m:
        return None
    day_s, mon_s, yy_s, strike_s, cp = m.groups()
    mon = _MONTH_MAP.get(mon_s.upper())
    if mon is None:
        return None
    try:
        y = 2000 + int(yy_s)
        day = int(day_s)
        strike = float(strike_s)
        dt = datetime(y, mon, day)
    except (ValueError, OSError):
        return None
    expiry = pd.Timestamp(dt).normalize()
    return expiry, strike, cp.upper()


def _trade_weight(row: pd.Series, prefer_contracts: bool) -> float:
    if prefer_contracts and "contracts" in row.index and pd.notna(row["contracts"]):
        w = float(row["contracts"])
        if w > 0 and np.isfinite(w):
            return w
    if "amount" in row.index and pd.notna(row["amount"]):
        w = float(row["amount"])
        if w > 0 and np.isfinite(w):
            return w
    return 1.0


def _clean_trades(
    df: pd.DataFrame,
    *,
    date_col: str,
    instrument_col: str,
    iv_col: str,
    spot_col: str,
    iv_input: str,
    option_filter: str,
    prefer_contracts: bool,
) -> pd.DataFrame:
    """
    与链日聚合相同的清洗规则，输出 **一行一笔成交**（未聚合）。
    列：date, expiry, K, option_type, spot, IV, weight, ttm_days, moneyness。
    option_filter 为 call/put 时在此阶段即过滤单边；merged/separate 保留 C 与 P。
    """
    mode = _canonical_option_filter(option_filter)

    need = [date_col, instrument_col, iv_col, spot_col]
    miss = [c for c in need if c not in df.columns]
    if miss:
        raise ValueError(f"缺少列: {miss}；当前列: {list(df.columns)}")

    out = df[need + [c for c in ("contracts", "amount") if c in df.columns]].copy()
    out["_parsed"] = out[instrument_col].apply(parse_eth_option_instrument)
    out = out[out["_parsed"].notna()].copy()

    if out.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "expiry",
                "K",
                "option_type",
                "spot",
                "IV",
                "weight",
                "ttm_days",
                "moneyness",
            ]
        )

    expiries = []
    strikes = []
    cps = []
    for p in out["_parsed"]:
        assert p is not None
        expiries.append(p[0])
        strikes.append(p[1])
        cps.append(p[2])
    out["expiry"] = expiries
    out["K"] = strikes
    out["option_type"] = cps

    if mode == "call":
        out = out[out["option_type"] == "C"].copy()
    elif mode == "put":
        out = out[out["option_type"] == "P"].copy()

    out[date_col] = pd.to_datetime(out[date_col], utc=True, errors="coerce")
    out[date_col] = out[date_col].dt.tz_convert(None).dt.normalize()
    out = out[out[date_col].notna()].copy()

    out[iv_col] = pd.to_numeric(out[iv_col], errors="coerce")
    out[spot_col] = pd.to_numeric(out[spot_col], errors="coerce")
    out = out[out[iv_col].notna() & out[spot_col].notna()].copy()
    out = out[(out[iv_col] > 0) & (out[spot_col] > 0)].copy()

    out["expiry"] = pd.to_datetime(out["expiry"], utc=True, errors="coerce").dt.tz_convert(
        None
    ).dt.normalize()
    out = out[out["expiry"].notna()].copy()
    out = out[out["expiry"] > out[date_col]].copy()

    if iv_input == "deribit_percent":
        out["IV"] = out[iv_col].astype(float) / 100.0
    else:
        out["IV"] = out[iv_col].astype(float)

    spot_f = out[spot_col].astype(float)
    prefer = prefer_contracts and "contracts" in out.columns
    out["weight"] = out.apply(lambda r: _trade_weight(r, prefer), axis=1)
    out["spot"] = spot_f
    out["ttm_days"] = (out["expiry"] - out[date_col]).dt.days.astype(np.int32)
    out["moneyness"] = out["K"] / spot_f

    keep_cols = [
        date_col,
        "expiry",
        "K",
        "option_type",
        "spot",
        "IV",
        "weight",
        "ttm_days",
        "moneyness",
    ]
    return out[keep_cols].rename(columns={date_col: "date"})


def _aggregate_cleaned_to_chain(cleaned: pd.DataFrame, option_filter: str) -> pd.DataFrame:
    """将 ``_clean_trades`` 输出聚合成 S2 链日面板（与原先 groupby 语义一致）。"""
    mode = _canonical_option_filter(option_filter)

    empty_schema = ["date", "expiry", "K", "spot", "IV", "quantity", "n_trades"]
    if mode == "separate":
        empty_schema = [
            "date",
            "expiry",
            "K",
            "option_type",
            "spot",
            "IV",
            "quantity",
            "n_trades",
        ]
    if cleaned.empty:
        return pd.DataFrame(columns=empty_schema)

    out = cleaned.copy()
    out["_wxiv"] = out["weight"] * out["IV"]
    out["_wxs"] = out["weight"] * out["spot"]

    keys: List[str] = ["date", "expiry", "K"]
    if mode == "separate":
        keys.append("option_type")

    g = (
        out.groupby(keys, sort=False)
        .agg(
            w_sum=("weight", "sum"),
            wxiv=("_wxiv", "sum"),
            wxs=("_wxs", "sum"),
            n_trades=("weight", "count"),
        )
        .reset_index()
    )
    g["spot"] = g["wxs"] / g["w_sum"]
    g["IV"] = g["wxiv"] / g["w_sum"]
    g["quantity"] = g["w_sum"]
    if mode == "separate":
        keep = ["date", "expiry", "K", "option_type", "spot", "IV", "quantity", "n_trades"]
    else:
        keep = ["date", "expiry", "K", "spot", "IV", "quantity", "n_trades"]
    return g[keep]


def _prepare_frame(
    df: pd.DataFrame,
    *,
    date_col: str,
    instrument_col: str,
    iv_col: str,
    spot_col: str,
    iv_input: str,
    option_filter: str,
    prefer_contracts: bool,
) -> pd.DataFrame:
    cleaned = _clean_trades(
        df,
        date_col=date_col,
        instrument_col=instrument_col,
        iv_col=iv_col,
        spot_col=spot_col,
        iv_input=iv_input,
        option_filter=option_filter,
        prefer_contracts=prefer_contracts,
    )
    return _aggregate_cleaned_to_chain(cleaned, option_filter)


def _trade_descriptives_wide(trades: pd.DataFrame) -> pd.DataFrame:
    """
    逐笔表（须含 date, option_type, ttm_days, moneyness, IV）→ 宽表：
    BTC Table 1 风格：Mean/Median/Std/Min/Max，Call 与 Put 分列。
    """
    need = {"date", "option_type", "ttm_days", "moneyness", "IV"}
    miss = need - set(trades.columns)
    if miss:
        raise ValueError(f"_trade_descriptives_wide 缺少列: {sorted(miss)}")

    rows_order = ["count", "mean", "std", "min", "median", "max"]
    data: dict[str, List[Any]] = {"statistic": rows_order}

    for side, prefix in (("C", "Call"), ("P", "Put")):
        sub = trades.loc[trades["option_type"] == side, ["ttm_days", "moneyness", "IV"]]
        if sub.empty:
            for v_en in ("TTM", "Moneyness", "IV"):
                data[f"{prefix}_{v_en}"] = [np.nan] * len(rows_order)
            continue
        desc = sub.describe(percentiles=[0.5]).rename(index={"50%": "median"})
        for v_en, v_col in (("TTM", "ttm_days"), ("Moneyness", "moneyness"), ("IV", "IV")):
            col_vals: List[Any] = []
            for r in rows_order:
                if r not in desc.index:
                    col_vals.append(np.nan)
                else:
                    val = desc.loc[r, v_col]
                    col_vals.append(float(val) if pd.notna(val) else np.nan)
            data[f"{prefix}_{v_en}"] = col_vals

    return pd.DataFrame(data)


def _trade_descriptives_meta(trades: pd.DataFrame) -> dict:
    d = pd.to_datetime(trades["date"], errors="coerce")
    return {
        "n_transactions_total": int(len(trades)),
        "n_transactions_call": int((trades["option_type"] == "C").sum()),
        "n_transactions_put": int((trades["option_type"] == "P").sum()),
        "n_trading_days": int(d.dt.normalize().nunique()),
        "first_trade_date": str(d.min().date()) if d.notna().any() else "",
        "last_trade_date": str(d.max().date()) if d.notna().any() else "",
    }


def _combine_partials(partials: List[pd.DataFrame], option_filter: str) -> pd.DataFrame:
    mode = _canonical_option_filter(option_filter)
    empty_cols = ["date", "expiry", "K", "spot", "IV", "quantity", "n_trades"]
    if mode == "separate":
        empty_cols = [
            "date",
            "expiry",
            "K",
            "option_type",
            "spot",
            "IV",
            "quantity",
            "n_trades",
        ]
    if not partials:
        return pd.DataFrame(columns=empty_cols)
    big = pd.concat(partials, ignore_index=True)
    if big.empty:
        return pd.DataFrame(columns=empty_cols)
    keys: List[str] = ["date", "expiry", "K"]
    if mode == "separate" and "option_type" in big.columns:
        keys.append("option_type")
    # 跨分块再次按 quantity 加权合并 IV / spot
    big["_wxiv"] = big["IV"] * big["quantity"]
    big["_wxs"] = big["spot"] * big["quantity"]
    g = (
        big.groupby(keys, sort=False)
        .agg(
            quantity=("quantity", "sum"),
            n_trades=("n_trades", "sum"),
            wxiv=("_wxiv", "sum"),
            wxs=("_wxs", "sum"),
        )
        .reset_index()
    )
    g["IV"] = g["wxiv"] / g["quantity"]
    g["spot"] = g["wxs"] / g["quantity"]
    g = g.drop(columns=["wxiv", "wxs"])
    return g.sort_values(keys).reset_index(drop=True)


def _save_trade_descriptives(wide: pd.DataFrame, meta: dict, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    wide.to_csv(dest, index=False)
    meta_path = dest.with_name(dest.stem + "_meta.json")
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def _save_empty_trade_descriptives(dest: Path) -> None:
    wide = pd.DataFrame(
        columns=[
            "statistic",
            "Call_TTM",
            "Call_Moneyness",
            "Call_IV",
            "Put_TTM",
            "Put_Moneyness",
            "Put_IV",
        ]
    )
    meta = {
        "n_transactions_total": 0,
        "n_transactions_call": 0,
        "n_transactions_put": 0,
        "n_trading_days": 0,
        "first_trade_date": "",
        "last_trade_date": "",
        "note": "无通过清洗的成交行",
    }
    _save_trade_descriptives(wide, meta, dest)


def _write_stats_from_cleaned(cleaned: pd.DataFrame, dest: Path) -> None:
    if cleaned.empty:
        _save_empty_trade_descriptives(dest)
        return
    snap = cleaned[["date", "option_type", "ttm_days", "moneyness", "IV"]].copy()
    wide = _trade_descriptives_wide(snap)
    meta = _trade_descriptives_meta(snap)
    _save_trade_descriptives(wide, meta, dest)


def trades_to_chain(
    input_path: Path,
    *,
    date_col: str = "trade_date",
    instrument_col: str = "instrument_name",
    iv_col: str = "iv",
    spot_col: str = "index_price",
    iv_input: str = "deribit_percent",
    option_filter: str = "merged",
    prefer_contracts: bool = True,
    chunksize: Optional[int] = 500_000,
    trade_descriptives: Optional[Path] = None,
) -> pd.DataFrame:
    """
    读取 S1 风格长表，返回日度链面板（VWAP 式加权：权重为 contracts 或 amount）。
    ``trade_descriptives``：在清洗后、聚合前对 **逐笔** 汇总 Call/Put 的 TTM、moneyness、IV 描述统计；
    分块读 CSV 时用临时 Parquet 累积（须安装 pyarrow）。
    """
    suf = input_path.suffix.lower()
    partials: List[pd.DataFrame] = []
    pq_writer: Any = None
    tmp_parquet: Optional[Path] = None

    if trade_descriptives is not None:
        trade_descriptives = trade_descriptives.resolve()

    try:
        if suf == ".parquet":
            df = pd.read_parquet(input_path)
            cleaned = _clean_trades(
                df,
                date_col=date_col,
                instrument_col=instrument_col,
                iv_col=iv_col,
                spot_col=spot_col,
                iv_input=iv_input,
                option_filter=option_filter,
                prefer_contracts=prefer_contracts,
            )
            if trade_descriptives is not None:
                _write_stats_from_cleaned(cleaned, trade_descriptives)
            partials = [_aggregate_cleaned_to_chain(cleaned, option_filter)]

        elif suf in (".csv", ".txt"):
            if chunksize:
                if trade_descriptives is not None and not _HAS_PYARROW:
                    raise RuntimeError(
                        "指定了 --trade-descriptives 且分块读取 CSV 时需要 pyarrow（临时写入 Parquet）。"
                        "请安装 pyarrow，或加 --no-chunks 一次性读入。"
                    )
                if trade_descriptives is not None:
                    tmp_parquet = trade_descriptives.parent / (
                        f".{trade_descriptives.stem}_clean_trades_tmp.parquet"
                    )
                reader = pd.read_csv(input_path, chunksize=chunksize)
                for chunk in reader:
                    cleaned = _clean_trades(
                        chunk,
                        date_col=date_col,
                        instrument_col=instrument_col,
                        iv_col=iv_col,
                        spot_col=spot_col,
                        iv_input=iv_input,
                        option_filter=option_filter,
                        prefer_contracts=prefer_contracts,
                    )
                    if trade_descriptives is not None and not cleaned.empty:
                        sub = cleaned[["date", "option_type", "ttm_days", "moneyness", "IV"]]
                        tbl = pa.Table.from_pandas(sub, preserve_index=False)
                        if pq_writer is None:
                            pq_writer = pq.ParquetWriter(str(tmp_parquet), tbl.schema)
                        pq_writer.write_table(tbl)
                    partials.append(_aggregate_cleaned_to_chain(cleaned, option_filter))
                if pq_writer is not None:
                    pq_writer.close()
                    pq_writer = None
                if trade_descriptives is not None:
                    if tmp_parquet is not None and tmp_parquet.exists():
                        all_tr = pd.read_parquet(tmp_parquet)
                        _write_stats_from_cleaned(all_tr, trade_descriptives)
                    else:
                        _save_empty_trade_descriptives(trade_descriptives)
            else:
                df = pd.read_csv(input_path)
                cleaned = _clean_trades(
                    df,
                    date_col=date_col,
                    instrument_col=instrument_col,
                    iv_col=iv_col,
                    spot_col=spot_col,
                    iv_input=iv_input,
                    option_filter=option_filter,
                    prefer_contracts=prefer_contracts,
                )
                if trade_descriptives is not None:
                    _write_stats_from_cleaned(cleaned, trade_descriptives)
                partials = [_aggregate_cleaned_to_chain(cleaned, option_filter)]
        else:
            raise ValueError(f"不支持的输入类型: {input_path}")
    finally:
        if pq_writer is not None:
            pq_writer.close()
        if tmp_parquet is not None and tmp_parquet.exists():
            tmp_parquet.unlink(missing_ok=True)

    return _combine_partials(partials, option_filter)


def main() -> None:
    p = argparse.ArgumentParser(
        description="S2：Deribit ETH 成交 → 日度 (date, expiry, K) 链表面板",
    )
    p.add_argument(
        "--input",
        "-i",
        type=Path,
        default=ETH_OPTIONS_FULLSAMPLE_CSV,
        help="S1 产出 CSV 或 Parquet",
    )
    p.add_argument(
        "--output",
        "-o",
        type=Path,
        default=_DEFAULT_OUT,
        help="输出 CSV 路径",
    )
    p.add_argument("--date-col", default="trade_date", help="交易日列（S1 默认为 trade_date）")
    p.add_argument("--instrument-col", default="instrument_name")
    p.add_argument("--iv-col", default="iv")
    p.add_argument("--spot-col", default="index_price", help="现货参考：成交内 index_price")
    p.add_argument(
        "--iv-input",
        choices=("deribit_percent", "decimal"),
        default="deribit_percent",
        help="deribit_percent：输入 iv 为 0–100，输出 IV 小数；decimal：输入已是小数",
    )
    p.add_argument(
        "--option-filter",
        choices=("merged", "call", "put", "separate", "both"),
        default="merged",
        help="merged=Call+Put 同 K 按 quantity 加权合并（默认，对齐 BTC S1）；call/put=单边；"
        "separate 或 both=按 C/P 分两行（接 S3 会混 moneyness，慎用）",
    )
    p.add_argument(
        "--no-chunks",
        action="store_true",
        help="CSV 一次性读入（小文件）；默认分块 50 万行",
    )
    p.add_argument(
        "--prefer-amount-over-contracts",
        action="store_true",
        help="权重优先用 amount，不用 contracts",
    )
    p.add_argument(
        "--trade-descriptives",
        type=Path,
        nargs="?",
        const=ETH_OPTIONS_PROCESSED_DIR / "s2_trade_descriptives.csv",
        default=None,
        help="清洗后、聚合成链日前写出逐笔描述性统计（BTC Table 1 式宽表 + 同名 _meta.json）。"
        "仅写该标志时用默认路径 data/eth_options_processed/s2_trade_descriptives.csv",
    )
    args = p.parse_args()

    if not args.input.exists():
        print(f"输入不存在: {args.input}", file=sys.stderr)
        raise SystemExit(1)

    out = trades_to_chain(
        args.input,
        date_col=args.date_col,
        instrument_col=args.instrument_col,
        iv_col=args.iv_col,
        spot_col=args.spot_col,
        iv_input=args.iv_input,
        option_filter=args.option_filter,
        prefer_contracts=not args.prefer_amount_over_contracts,
        chunksize=None if args.no_chunks else 500_000,
        trade_descriptives=args.trade_descriptives,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    print(f"已写入 {args.output}（{len(out):,} 行）")
    if args.trade_descriptives is not None:
        meta_fp = args.trade_descriptives.with_name(args.trade_descriptives.stem + "_meta.json")
        print(
            f"逐笔描述性统计: {args.trade_descriptives} ，元数据: {meta_fp}",
            file=sys.stderr,
        )
    if _canonical_option_filter(args.option_filter) == "separate":
        print(
            "提示：separate/both 模式下 C 与 P 为不同行；当前 S3 仅按 (date,tau,moneyness) 分组，"
            "接入前请确认是否需要扩展 S3 分组键。",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
