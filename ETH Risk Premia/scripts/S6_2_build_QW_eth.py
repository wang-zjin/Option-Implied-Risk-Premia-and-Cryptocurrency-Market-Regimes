#!/usr/bin/env python3
"""
S6_2：从 S2 日度链（**separate** 或 **merged**）生成 ``data/eth_options_processed/prepare_QW_for_VIX/`` 下的 QW 日文件（默认，见 ``function.ETH_VIX_QW_DIR``），
供 ``S6_3_calculate_eth_vix.py`` 估计 ETH-VIX。

链上需同时有 Call / Put 的 IV（按行权价聚合）；本脚本用 Black–Scholes（**r 默认 0**，
与 ``S6_3_calculate_eth_vix.py`` 一致）将 IV 转为 **名义美元** 期权价，再按 BTC QW 列格式写出。

上游：``S2_trades_to_chain_daily.py``；**separate** 链最优（C/P 分侧 IV）；**merged** 链也可用（无 ``option_type`` 时，脚本按档将**同一 IV** 赋给 Call 与 Put 再 BS 定价）。
下游：``S6_3_calculate_eth_vix.py``

对每个 ``--tau-list`` 中的目标期限，在 ``[min-ttm, max-ttm]`` 内选取**相邻**两档到期
``T1 < tau < T2`` 作为插值端点。输出至 ``{output_dir}/TTM_{dd}/``（如 ``TTM_09``），CSV 名为
``YYYYMMDD_QW_T1_{t1}_T2_{t2}.csv``（与旧命名一致）。
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from function import (
    ETH_OPTIONS_CHAIN_DAILY_CSV,
    ETH_VIX_QW_DIR,
    PRIMARY_TTMS,
    eth_vix_qw_ttm_subdir,
)


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_call_put(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
) -> Tuple[float, float]:
    """Black–Scholes 欧式 Call / Put（现货 S，年化波动 sigma，年化 r）。"""
    if not (S > 0 and K > 0 and T > 0 and sigma > 0):
        return float("nan"), float("nan")
    v = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / v
    d2 = d1 - v
    disc = math.exp(-r * T)
    c = S * _norm_cdf(d1) - K * disc * _norm_cdf(d2)
    p = K * disc * _norm_cdf(-d2) - S * _norm_cdf(-d1)
    return c, p


def _normalize_option_type(s: object) -> Optional[str]:
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return None
    t = str(s).strip().upper()
    if t in ("C", "CALL"):
        return "C"
    if t in ("P", "PUT"):
        return "P"
    return None


def _strike_key(k: float) -> float:
    return round(float(k), 8)


def load_chain_separate(path: Path) -> pd.DataFrame:
    """
    读取 S2 链。列至少含 date, expiry, K, spot, IV。

    - **separate**：含 ``option_type``（C/P），按侧聚合 IV。
    - **merged**（无 ``option_type``）：先按 (date, expiry, K) 聚合，再将**同一 IV** 复制到
      Call 与 Put 两侧，供 BS 定价（与 merged 链「每档单一代表 IV」一致）。
    """
    suf = path.suffix.lower()
    if suf == ".parquet":
        df = pd.read_parquet(path)
    elif suf in (".csv", ".txt"):
        df = pd.read_csv(path)
    else:
        raise ValueError(f"不支持的输入: {path}")

    need_base = ["date", "expiry", "K", "spot", "IV"]
    miss = [c for c in need_base if c not in df.columns]
    if miss:
        raise ValueError(
            f"缺少列 {miss}。需要 S2 产出的日度链（至少含 date, expiry, K, spot, IV）。"
        )

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce").dt.tz_convert(None).dt.normalize()
    df["expiry"] = pd.to_datetime(df["expiry"], utc=True, errors="coerce").dt.tz_convert(None).dt.normalize()
    df["K"] = pd.to_numeric(df["K"], errors="coerce")
    df["spot"] = pd.to_numeric(df["spot"], errors="coerce")
    df["IV"] = pd.to_numeric(df["IV"], errors="coerce")
    df = df[df["date"].notna() & df["expiry"].notna()].copy()
    df = df[df["expiry"] > df["date"]].copy()
    df = df.dropna(subset=["K", "spot", "IV"])
    df = df[(df["spot"] > 0) & (df["IV"] > 0)].copy()

    if "option_type" not in df.columns:
        df = (
            df.groupby(["date", "expiry", "K"], sort=False)
            .agg(IV=("IV", "mean"), spot=("spot", "mean"))
            .reset_index()
        )
        df = pd.concat(
            [df.assign(option_type="C"), df.assign(option_type="P")],
            ignore_index=True,
        )
    else:
        df["_ot"] = df["option_type"].apply(_normalize_option_type)
        df = df[df["_ot"].notna()].copy()
        df = df.rename(columns={"_ot": "option_type"})

    g = (
        df.groupby(["date", "expiry", "K", "option_type"], sort=False)
        .agg(IV=("IV", "mean"), spot=("spot", "mean"))
        .reset_index()
    )
    return g


def expiry_call_put_table(
    rows: pd.DataFrame,
    date: pd.Timestamp,
    expiry: pd.Timestamp,
    r: float,
) -> Dict[float, Tuple[float, float, float]]:
    """
    返回 K_key -> (C_price, P_price, spot)（仅包含可 BS 定价的 K）。
    若仅 Call 或仅 Put 有 IV，则用该 IV 同时生成 C、P（单一波动率下的 BS 价）。
    若两侧均有 IV，则 Call 用 C 侧 IV、Put 用 P 侧 IV 分别定价。
    """
    sub = rows[(rows["date"] == date) & (rows["expiry"] == expiry)].copy()
    if sub.empty:
        return {}

    spot0 = float(sub["spot"].mean())
    calls = sub[sub["option_type"] == "C"]
    puts = sub[sub["option_type"] == "P"]
    by_k: Dict[float, Dict[str, float]] = {}
    for _, r0 in calls.iterrows():
        k = _strike_key(r0["K"])
        by_k.setdefault(k, {})["C"] = float(r0["IV"])
    for _, r0 in puts.iterrows():
        k = _strike_key(r0["K"])
        by_k.setdefault(k, {})["P"] = float(r0["IV"])

    ttm_days = (expiry - date).days
    if ttm_days <= 0:
        return {}
    T = ttm_days / 365.0

    out: Dict[float, Tuple[float, float, float]] = {}
    for k_key, sides in by_k.items():
        iv_c = sides.get("C")
        iv_p = sides.get("P")
        if iv_c is None and iv_p is None:
            continue
        K = float(k_key)
        if iv_c is not None and iv_p is not None:
            c, _ = bs_call_put(spot0, K, T, r, float(iv_c))
            _, p = bs_call_put(spot0, K, T, r, float(iv_p))
        else:
            sig = float(iv_c if iv_c is not None else iv_p)
            c, p = bs_call_put(spot0, K, T, r, sig)
        if not (math.isfinite(c) and math.isfinite(p) and c >= 0 and p >= 0):
            continue
        out[k_key] = (c, p, spot0)
    return out


def pick_straddling_expiries(
    expiries: Iterable[pd.Timestamp],
    date: pd.Timestamp,
    target_tau: int,
    min_ttm: int,
    max_ttm: int,
) -> Optional[Tuple[pd.Timestamp, pd.Timestamp, int, int]]:
    """
    在 [min_ttm, max_ttm] 内的到期中按剩余天数排序，取**相邻**两档 (T1,T2)，
    使 ``T1 < target_tau < T2``（与 S6_3 CBOE 方差插值一致）。若无这样的一对则返回 None。
    """
    cand: List[Tuple[pd.Timestamp, int]] = []
    for e in sorted(set(expiries)):
        ddays = (e - date).days
        if min_ttm <= ddays <= max_ttm:
            cand.append((e, ddays))
    if len(cand) < 2:
        return None
    cand.sort(key=lambda x: x[1])
    ttms = [c[1] for c in cand]
    for i in range(len(ttms) - 1):
        if ttms[i] < target_tau < ttms[i + 1]:
            e1, t1 = cand[i][0], ttms[i]
            e2, t2 = cand[i + 1][0], ttms[i + 1]
            return e1, e2, t1, t2
    return None


def build_qw_dataframe(
    chain: pd.DataFrame,
    *,
    r: float,
    min_ttm: int,
    max_ttm: int,
    target_taus: List[int],
) -> List[Tuple[pd.DataFrame, str, int]]:
    """
    对每个交易日、每个目标 tau，若存在夹住该 tau 的两档到期则生成一个 QW 表。

    返回 ``(DataFrame, basename, target_tau)``；basename 为 ``YYYYMMDD_QW_T1_{t1}_T2_{t2}.csv``。
    """
    dates = sorted(chain["date"].unique())
    outputs: List[Tuple[pd.DataFrame, str, int]] = []

    for d in dates:
        day = chain[chain["date"] == d]
        expiries = day["expiry"].unique()
        for target_tau in target_taus:
            picked = pick_straddling_expiries(
                expiries, d, target_tau, min_ttm, max_ttm
            )
            if picked is None:
                continue
            e1, e2, t1, t2 = picked
            tab1 = expiry_call_put_table(chain, d, e1, r)
            tab2 = expiry_call_put_table(chain, d, e2, r)
            common = sorted(set(tab1.keys()) & set(tab2.keys()))
            if len(common) < 2:
                continue

            rows_out = []
            for k in common:
                c1, p1, _ = tab1[k]
                c2, p2, _ = tab2[k]
                rows_out.append(
                    {
                        "K_T1": k,
                        "C_T1": c1,
                        "P_T1": p1,
                        "K_T2": k,
                        "C_T2": c2,
                        "P_T2": p2,
                    }
                )
            qw = pd.DataFrame(rows_out).sort_values("K_T1").reset_index(drop=True)
            name = f"{pd.Timestamp(d).strftime('%Y%m%d')}_QW_T1_{t1}_T2_{t2}.csv"
            outputs.append((qw, name, target_tau))
    return outputs


def main() -> None:
    p = argparse.ArgumentParser(
        description="从 S2 日度链生成 ETH-VIX 所需的 QW 日 CSV（供 S6_3_calculate_eth_vix.py）",
    )
    p.add_argument(
        "--input",
        "-i",
        type=Path,
        default=ETH_OPTIONS_CHAIN_DAILY_CSV,
        help="S2 链 CSV/Parquet（默认 eth_options_chain_daily.csv；separate 含 option_type，merged 无该列亦可）",
    )
    p.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=ETH_VIX_QW_DIR,
        help="QW 根目录（默认 prepare_QW_for_VIX；其下按 TTM_09/TTM_27/… 分子目录）",
    )
    p.add_argument("--r", type=float, default=0.0, help="年化无风险利率（与 S6_3 一致默认 0）")
    p.add_argument(
        "--min-ttm",
        type=int,
        default=8,
        help="选近月/次近月时：剩余到期天数下界（天），与 CBOE 常用「≥8 天」一致",
    )
    p.add_argument(
        "--max-ttm",
        type=int,
        default=180,
        help="剩余到期天数上界（天），过滤过远到期",
    )
    p.add_argument("--date-start", default=None, help="仅处理此日及之后（YYYY-MM-DD）")
    p.add_argument("--date-end", default=None, help="仅处理此日及之前（YYYY-MM-DD）")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="只统计将写出多少文件，不写盘",
    )
    p.add_argument(
        "--tau-list",
        nargs="+",
        type=int,
        default=list(PRIMARY_TTMS),
        metavar="TAU",
        help=f"目标期限（天）；对每个 tau 选取夹住该 tau 的两档到期生成 QW。默认 {list(PRIMARY_TTMS)}",
    )
    args = p.parse_args()
    target_taus = sorted(set(args.tau_list))

    if not args.input.exists():
        print(f"输入不存在: {args.input}", file=sys.stderr)
        raise SystemExit(1)

    chain = load_chain_separate(args.input)
    if chain.empty:
        print("链表为空，退出。", file=sys.stderr)
        raise SystemExit(1)

    if args.date_start:
        ds = pd.to_datetime(args.date_start).normalize()
        chain = chain[chain["date"] >= ds]
    if args.date_end:
        de = pd.to_datetime(args.date_end).normalize()
        chain = chain[chain["date"] <= de]

    built = build_qw_dataframe(
        chain,
        r=args.r,
        min_ttm=args.min_ttm,
        max_ttm=args.max_ttm,
        target_taus=target_taus,
    )
    if not built:
        print("未生成任何 QW 日文件（检查 min/max-ttm、链是否含两档到期与足够交集行权价）。")
        raise SystemExit(1)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        print(
            f"[dry-run] 将写出 {len(built)} 个文件至 {args.output_dir}/TTM_*/ (e.g. TTM_09, TTM_27)"
        )
        return

    for qw, name, target_tau in built:
        sub = eth_vix_qw_ttm_subdir(target_tau)
        out_path = args.output_dir / sub / name
        out_path.parent.mkdir(parents=True, exist_ok=True)
        qw.to_csv(out_path, index=False, encoding="utf-8")
    print(f"已写入 {len(built)} 个 QW 文件 → {args.output_dir}/TTM_*/")


if __name__ == "__main__":
    main()
