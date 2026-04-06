"""
S6_3：ETH VIX 计算（由 SVI_independent_tau/calculate_btc_vix.py 复制改写；不修改 BTC 原文件）。

管线位置：**Q measure**末端（与 **S6_0 / S6_1** 同段）；主链为 **S4→…→S6_1→S6_2（QW）→S6_3→S7→S8_***
（… → Q_matrix → **QW** → **ETH-VIX** → **S7 聚类（Q）** → **S8_* 物理测度 P**）。
本脚本数学上**不依赖** SVI/IV 曲面，输入为 ``prepare_QW_for_VIX/TTM_{dd}/`` 下日度 QW（默认根目录见 **`function.ETH_VIX_QW_DIR`**；QW 由 **`S6_2_build_QW_eth.py`** 生成）。详见 ETH_risk_premia_plan.md §7；VRP 必要条件见 §1.3。

参考 CBOE VIX 方法论，使用近月与次近月期权计算隐含波动率指数。

如何运行
--------
在仓库 ``deribit/`` 根目录下执行；须已用 **S6_2** 生成 ``prepare_QW_for_VIX/TTM_09/``、``TTM_27/`` 等及其中 CSV。

默认：QW 根目录为 ``function.ETH_VIX_QW_DIR``，输出为 ``results/ETH_VIX/``。

::

    python scripts/S6_3_calculate_eth_vix.py
    python scripts/S6_3_calculate_eth_vix.py --tau-list 9 27 45
    python scripts/S6_3_calculate_eth_vix.py --tau 27
    python scripts/S6_3_calculate_eth_vix.py -i data/eth_options_processed/prepare_QW_for_VIX -o results/ETH_VIX
    python scripts/S6_3_calculate_eth_vix.py --tau-list 9 27 45 -q

``--tau-list``：一次算多个目标期限（天）。``--tau`` / ``-t``：只算一个。``-i``：QW **根目录**（其下须有 ``TTM_{dd}/``，由 ``eth_vix_qw_ttm_subdir(tau)`` 命名）。``-o``：输出目录。``-q``：静默（不打印逐文件「跳过」）。另见 ``--ema-span``、``--date-start``（默认 2017-07-01）。

输入数据格式
------------
- 路径：``{ETH_VIX_QW_DIR}/TTM_09/``、``TTM_27/`` 等（与目标 tau 对应，见 ``function.eth_vix_qw_ttm_subdir``）
- 文件名：``YYYYMMDD_QW_T1_{ttm1}_T2_{ttm2}.csv``
- 列: K_T1, C_T1, P_T1 (近月: 行权价, Call价, Put价)
       K_T2, C_T2, P_T2 (次近月: 行权价, Call价, Put价)

输出
----
- ``{output}/eth_vix_EWA_{tau}.csv``：列 Date（YYYYMMDD 字符串）、EMA
"""

from __future__ import annotations

import argparse
import math
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from function import ETH_VIX_QW_DIR, ETH_VIX_RESULTS_DIR, eth_vix_qw_ttm_subdir

# ============== 配置 ==============
# 可通过 --input / --output 覆盖
DEFAULT_INPUT_DIR = ETH_VIX_QW_DIR
DEFAULT_OUTPUT_DIR = ETH_VIX_RESULTS_DIR

DEFAULT_TAU = 45
EMA_SPAN = 3
VIX_MAX = 170
DATE_START = "2017-07-01"
LARGE_NUMBER = 9999999


def extract_info(filename: str):
    """Parse ``YYYYMMDD_QW_T1_{t1}_T2_{t2}.csv`` -> (date, ttm1, ttm2)."""
    m = re.match(r"(\d{8})_QW_T1_(\d+)_T2_(\d+)\.csv", filename)
    if not m:
        return None
    ds, t1_s, t2_s = m.groups()
    return datetime.strptime(ds, "%Y%m%d").date(), int(t1_s), int(t2_s)


def calculate_vix_for_file(filepath: str, date, ttm1: int, ttm2: int, tau: int):
    df = pd.read_csv(filepath)

    required_cols = ["K_T1", "C_T1", "P_T1", "K_T2", "C_T2", "P_T2"]
    for col in required_cols:
        if col not in df.columns:
            print(f"  缺少列 {col}: {filepath}")
            return None

    data1 = df[["K_T1", "C_T1", "P_T1"]].values.tolist()
    data2 = df[["K_T2", "C_T2", "P_T2"]].values.tolist()

    data1_clean = [t for t in data1 if not all(np.isnan(v) for v in t)]
    data2_clean = [t for t in data2 if not all(np.isnan(v) for v in t)]

    data1_clean = [[v if v != 0 else LARGE_NUMBER for v in t] for t in data1_clean]
    data2_clean = [[v if v != 0 else LARGE_NUMBER for v in t] for t in data2_clean]

    arr1 = np.array(data1_clean)
    arr2 = np.array(data2_clean)
    diff1 = np.abs(arr1[:, 1] - arr1[:, 2])
    diff2 = np.abs(arr2[:, 1] - arr2[:, 2])
    if np.sum(diff1 < 10000) < 1 or np.sum(diff2 < 10000) < 1:
        return None

    quotedata = [data1_clean, data2_clean]
    rates = [0.0, 0.0]
    T = [ttm1 / 365.0, ttm2 / 365.0]

    if ttm1 >= ttm2:
        return None
    # CBOE 方差插值要求目标 tau（天）严格落在两档到期之间；否则外推易出现负方差 → sqrt 报错
    if not (ttm1 < tau < ttm2):
        return None

    F = [None, None]
    for j in (0, 1):
        mindiff = None
        Fstrike = None
        for d in quotedata[j]:
            diff = abs(d[1] - d[2])
            if mindiff is None or diff < mindiff:
                mindiff = diff
                Fstrike = d[0]
                Fcall = d[1]
                Fput = d[2]
        F[j] = Fstrike + math.exp(rates[j] * T[j]) * (Fcall - Fput)

    selectedoptions = [[], []]
    k0 = [None, None]
    for j in (0, 1):
        k0i = 0
        for i, d in enumerate(quotedata[j]):
            if d[0] < F[j]:
                k0[j] = d[0]
                k0i = i

        # 无行权价严格低于远期 F 时无法定义 K0（CBOE 步骤）
        if k0[j] is None:
            return None

        if k0i < len(quotedata[j]) and LARGE_NUMBER in quotedata[j][k0i]:
            k0i = min(k0i + 1, len(quotedata[j]) - 1)

        if k0i >= len(quotedata[j]):
            return None

        d = quotedata[j][k0i]
        selectedoptions[j].append([d[0], "put/call average", (d[1] + d[2]) / 2])

        i = k0i - 1
        prev_put = None
        while i >= 0:
            d = quotedata[j][i]
            if d[2] > 0:
                selectedoptions[j].insert(0, [d[0], "put", d[2]])
            elif prev_put == 0:
                break
            prev_put = d[2]
            i -= 1

        i = k0i + 1
        prev_call = None
        while i < len(quotedata[j]):
            d = quotedata[j][i]
            if d[1] > 0:
                selectedoptions[j].append([d[0], "call", d[1]])
            elif prev_call == 0:
                break
            prev_call = d[1]
            i += 1

    selectedoptions[0] = [t for t in selectedoptions[0] if LARGE_NUMBER not in t]
    selectedoptions[1] = [t for t in selectedoptions[1] if LARGE_NUMBER not in t]

    if len(selectedoptions[0]) < 2 or len(selectedoptions[1]) < 2:
        return None

    for j in (0, 1):
        for i, d in enumerate(selectedoptions[j]):
            if i == 0:
                deltak = selectedoptions[j][1][0] - selectedoptions[j][0][0]
            elif i == len(selectedoptions[j]) - 1:
                deltak = selectedoptions[j][i][0] - selectedoptions[j][i - 1][0]
            else:
                deltak = (
                    selectedoptions[j][i + 1][0] - selectedoptions[j][i - 1][0]
                ) / 2
            contrib = (deltak / (d[0] ** 2)) * math.exp(rates[j] * T[j]) * d[2]
            d.append(contrib)

    sigmasquared = [None, None]
    for j in (0, 1):
        agg = sum(d[3] for d in selectedoptions[j])
        agg = (2 / T[j]) * agg
        sigmasquared[j] = agg - (1 / T[j]) * (F[j] / k0[j] - 1) ** 2

    tau_years = tau / 365.0
    vix_sq = (
        (T[0] * sigmasquared[0]) * (T[1] - tau_years) / (T[1] - T[0])
        + (T[1] * sigmasquared[1]) * (tau_years - T[0]) / (T[1] - T[0])
    ) * 365 / tau
    if not math.isfinite(vix_sq) or vix_sq <= 0:
        return None
    VIX = 100 * math.sqrt(vix_sq)

    return pd.DataFrame({"Date": [date], "VIX": [VIX]})


def run_vix_calculation(
    input_dir: str,
    output_dir: str,
    tau: int = DEFAULT_TAU,
    ema_span: int = EMA_SPAN,
    vix_max: float = VIX_MAX,
    date_start: str = DATE_START,
    verbose: bool = True,
):
    tau_qw_dir = Path(input_dir) / eth_vix_qw_ttm_subdir(tau)
    if not tau_qw_dir.is_dir():
        raise FileNotFoundError(
            f"QW 子目录不存在: {tau_qw_dir}（请先生成 S6_2 对应 TTM 目录）"
        )

    os.makedirs(output_dir, exist_ok=True)

    all_data = []
    files = sorted(f for f in os.listdir(tau_qw_dir) if f.endswith(".csv"))

    for filename in files:
        try:
            file_info = extract_info(filename)
            if file_info is None:
                continue
            date, ttm1, ttm2 = file_info
            if not (ttm1 < tau < ttm2):
                continue
            filepath = str(tau_qw_dir / filename)
            result = calculate_vix_for_file(filepath, date, ttm1, ttm2, tau)
            if result is not None:
                all_data.append(result)
            elif verbose:
                print(f"  跳过 (无有效数据): {filename}")
        except Exception as e:
            if verbose:
                print(f"  错误 {filename}: {e}")

    if not all_data:
        print("未找到有效数据，无法生成 VIX。")
        return None

    vix_df = pd.concat(all_data, ignore_index=True)
    vix_df["Date"] = pd.to_datetime(vix_df["Date"])
    vix_df = vix_df.sort_values("Date").reset_index(drop=True)

    vix_df = vix_df[vix_df["VIX"] <= vix_max]
    vix_df = vix_df[vix_df["Date"] >= date_start]

    ema = vix_df["VIX"].ewm(span=ema_span, adjust=False).mean()
    vix_df["EMA"] = ema

    out_df = vix_df[["Date", "EMA"]].copy()
    out_df["Date"] = pd.to_datetime(out_df["Date"]).dt.strftime("%Y%m%d")

    output_file = os.path.join(output_dir, f"eth_vix_EWA_{tau}.csv")
    out_df.to_csv(output_file, index=False, encoding="utf-8")

    if verbose:
        print(f"已保存: {output_file} ({len(out_df)} 行)")

    return out_df


def main():
    parser = argparse.ArgumentParser(description="计算 ETH VIX（CBOE 方法 + EMA，S6_3）")
    parser.add_argument(
        "--input",
        "-i",
        default=str(DEFAULT_INPUT_DIR),
        help="QW 根目录 (prepare_QW_for_VIX；其下含 TTM_09/ 等子目录)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=str(DEFAULT_OUTPUT_DIR),
        help="输出目录",
    )
    parser.add_argument(
        "--tau",
        "-t",
        type=int,
        default=DEFAULT_TAU,
        help=f"VIX 目标期限 (天), 默认 {DEFAULT_TAU}",
    )
    parser.add_argument("--ema-span", type=int, default=EMA_SPAN)
    parser.add_argument("--date-start", default=DATE_START)
    parser.add_argument(
        "--tau-list",
        nargs="+",
        type=int,
        metavar="TAU",
        help="一次计算多个 tau，如: --tau-list 9 27 45",
    )
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args()

    tau_list = args.tau_list if args.tau_list else [args.tau]
    for tau in tau_list:
        run_vix_calculation(
            input_dir=args.input,
            output_dir=args.output,
            tau=tau,
            ema_span=args.ema_span,
            date_start=args.date_start,
            verbose=not args.quiet,
        )


if __name__ == "__main__":
    main()
