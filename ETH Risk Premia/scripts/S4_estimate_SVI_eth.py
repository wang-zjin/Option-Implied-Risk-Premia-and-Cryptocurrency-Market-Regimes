#!/usr/bin/env python3
"""
S4：按日 × 到期（τ）拟合 SVI 系数（Tau-independent；与 BTC
``S2_v1_0_estimate_SVI_coefficients_eachday_Tau-independent_unique_moneyness.py`` 等价）。

输入：S3 产出的日度 IV 矩阵目录 ``IV/IV_raw/unique/moneyness/IV_matrix_*.csv``（列：moneyness, τ1, τ2, …；IV 为百分比）。

**拟合范围**：对矩阵中出现的每个 τ，只要 ``tau_min ≤ τ ≤ tau_max``（默认 ``function.SVI_TAU_MIN_DAYS``–
``SVI_TAU_MAX_DAYS``，即 1–120 天）且该 smile 上点数足够，即单独拟合一条 SVI，供后续 **Q 密度 / IV 曲面
插值**（见 ``ETH_risk_premia_plan.md`` §1.1.1：**S5_0** / **S5_1** 在 ``results/IV/`` 生成全量曲面，**S6_0** Q 密度读取该曲面）。**不在拟合阶段**只保留主分析 ttm。

**唯一主输出（全量，与 BTC ``SVI/v1/`` 同构文件名）** → ``results/SVI/``（``function.ETH_SVI_FULL_OUT_DIR``）：
  ``svi_Tau-Ind_Mon-Uni_iv_and_r2_results.csv`` — Date, R2, tau, 及 [-1,1] 上 201 个网格点的 SVI 隐含 IV；
  ``svi_Tau-Ind_Mon-Uni_paras.csv`` — filename, tau, a, b, rho, m, sigma。
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.optimize import minimize

# 允许从仓库根目录运行: python scripts/S4_estimate_SVI_eth.py
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from function import (  # noqa: E402
    ETH_OPTIONS_IV_OUT_DIR,
    ETH_S3_IV_MATRIX_MON_DIR,
    ETH_SVI_FULL_OUT_DIR,
    SVI_TAU_MAX_DAYS,
    SVI_TAU_MIN_DAYS,
)

# ---------------------------------------------------------------------------
# SVI（τ-independent）与 BTC 脚本一致
# ---------------------------------------------------------------------------


def svi_model_ind(theta: np.ndarray, k: float) -> float:
    a, b, rho, m, sigma = theta[:5]
    return a + b * (rho * (k - m) + np.sqrt((k - m) ** 2 + sigma**2))


def objective_function_grid(
    theta: np.ndarray, k_new: np.ndarray, iv_obs_grid: np.ndarray
) -> float:
    iv_model_grid = np.empty_like(iv_obs_grid)
    penalty = 0.0
    epsilon = 1e-10
    for j in range(len(k_new)):
        iv_model_val = svi_model_ind(theta, k_new[j])
        if iv_model_val < -epsilon:
            penalty += 100000.0
            iv_model_grid[j] = 0.0
        else:
            iv_model_grid[j] = np.sqrt(max(iv_model_val, 0.0))
    mse = np.mean((iv_model_grid - iv_obs_grid) ** 2)
    result = np.sqrt(mse) + penalty
    if np.isnan(result):
        return 1e10
    return float(result)


def constraint1(theta: np.ndarray) -> float:
    return float(theta[1])


def constraint2(theta: np.ndarray) -> float:
    return float(1 - abs(theta[2]))


def constraint3(theta: np.ndarray) -> float:
    return float(theta[0] + theta[1] * theta[4] * np.sqrt(1 - theta[2] ** 2))


def constraint4(theta: np.ndarray) -> float:
    return float(theta[4])


def _rng_for_file(seed: Optional[int], filepath: Path) -> np.random.Generator:
    """并行时每个文件独立 RNG；给定 seed 时可复现（不依赖 PYTHONHASHSEED）。"""
    if seed is None:
        return np.random.default_rng()
    h = int(hashlib.md5(filepath.name.encode("utf-8")).hexdigest(), 16) % (1 << 31)
    return np.random.default_rng((seed + h) % (1 << 31))


def process_csv_file(
    filepath: Path,
    seed: Optional[int] = None,
    tau_min: int = SVI_TAU_MIN_DAYS,
    tau_max: int = SVI_TAU_MAX_DAYS,
) -> Tuple[List[dict], List[List[Any]]]:
    """单日日度 IV 矩阵：与 BTC ``process_csv_file`` 相同逻辑；τ 限制在 ``[tau_min, tau_max]``。"""
    rng = _rng_for_file(seed, filepath)
    results_list: List[dict] = []
    thetas_list: List[List[Any]] = []

    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return results_list, thetas_list

    # BTC 用 ``<= 2``；ETH 允许仅 (moneyness, 单列 tau) 共 2 列
    if len(df.columns) < 2:
        print(f"Skipping {filepath} due to having {len(df.columns)} columns.")
        return results_list, thetas_list

    df = df.transpose()

    try:
        filtered_indices = [int(i) for i in df.index if str(i).isnumeric()]
    except Exception as e:
        print(f"Error processing indices in {filepath}: {e}")
        return results_list, thetas_list

    row_names_array = np.array(filtered_indices)
    iv_real = df.iloc[1:, :] / 100.0
    iv = iv_real.to_numpy()

    constraints = [
        {"type": "ineq", "fun": constraint1},
        {"type": "ineq", "fun": constraint2},
        {"type": "ineq", "fun": constraint3},
        {"type": "ineq", "fun": constraint4},
    ]

    ttm = row_names_array
    k = df.iloc[0, :].to_numpy()

    for i_tau, tau_of_interest in enumerate(ttm):
        tau_int = int(tau_of_interest)
        if tau_int < tau_min or tau_int > tau_max:
            continue
        iv_index = ~np.isnan(iv[i_tau, :])
        iv_new = iv[i_tau, iv_index]
        k_new = k[iv_index]
        if iv_new.size < 3:
            continue

        theta_guess = 0.05 * rng.random(5)
        max_iterations = 4
        bounds = [(-4, 4), (-50, 18), (-2, 2), (-2, 2), (-0.5, 1)]
        lower_bounds = np.array([b[0] for b in bounds])
        upper_bounds = np.array([b[1] for b in bounds])

        iteration_count = 0
        best_loss = np.inf
        best_thetas: Optional[np.ndarray] = None
        r2_final = float("nan")

        while iteration_count < max_iterations:
            iteration_count += 1
            optimized_thetas: List[np.ndarray] = []
            losses: List[float] = []
            for _ in range(10):
                theta_guess[(theta_guess < lower_bounds) | (theta_guess > upper_bounds)] = 0
                res = minimize(
                    objective_function_grid,
                    theta_guess,
                    args=(k_new, iv_new.ravel()),
                    constraints=constraints,
                    method="SLSQP",
                    bounds=bounds,
                )
                optimized_thetas.append(res.x)
                losses.append(float(res.fun))
                theta_guess = res.x + 0.02 * rng.random(5)

            best_idx = int(np.argmin(losses))
            if losses[best_idx] < best_loss:
                best_loss = losses[best_idx]
                best_thetas = optimized_thetas[best_idx]

            if best_thetas is None:
                break
            y_obs = iv_new.ravel()
            y_pred = np.array([np.sqrt(svi_model_ind(best_thetas, x)) for x in k_new])
            ss_res = np.sum((y_obs - y_pred) ** 2)
            ss_tot = np.sum((y_obs - y_obs.mean()) ** 2)
            r2_final = float(1 - (ss_res / ss_tot)) if ss_tot > 0 else float("nan")
            if r2_final >= 0.97:
                break

        if best_thetas is None:
            continue

        k_full = np.linspace(-1, 1, 201)
        iv_svi_of_interest = np.sqrt(
            np.array([svi_model_ind(best_thetas, k_val) for k_val in k_full])
        )
        iv_svi_dict = {f"{k_val:.4f}": iv_val for k_val, iv_val in zip(k_full, iv_svi_of_interest)}

        result_entry: Dict[str, Any] = {
            "Date": filepath.name,
            "R2": r2_final,
            "tau": tau_int,
        }
        result_entry.update(iv_svi_dict)
        results_list.append(result_entry)
        thetas_list.append([filepath.name, tau_int] + list(best_thetas))

    return results_list, thetas_list


def _collect_iv_files(iv_folder: Path) -> List[Path]:
    return sorted(
        p
        for p in iv_folder.iterdir()
        if p.is_file() and p.suffix.lower() == ".csv" and p.name.startswith("IV")
    )


def _write_full_svi_tables(results_df: pd.DataFrame, thetas_df: pd.DataFrame, out_dir: Path) -> None:
    """全量 (date, τ) 表 → ``results/SVI/``，与 BTC ``SVI/v1/`` 同构。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(out_dir / "svi_Tau-Ind_Mon-Uni_iv_and_r2_results.csv", index=False)
    thetas_df.to_csv(out_dir / "svi_Tau-Ind_Mon-Uni_paras.csv", index=False)
    print(f"全量 SVI（{len(results_df)} 行）-> {out_dir}")


def main() -> None:
    default_iv = ETH_S3_IV_MATRIX_MON_DIR
    p = argparse.ArgumentParser(description="S4：Tau-independent SVI（与 BTC 等价）")
    p.add_argument(
        "--iv-folder",
        type=Path,
        default=default_iv,
        help="S3 日度 IV 矩阵目录（moneyness pivot）",
    )
    p.add_argument(
        "--tau-min",
        type=int,
        default=SVI_TAU_MIN_DAYS,
        help=f"仅拟合 τ≥该值（天），默认 {SVI_TAU_MIN_DAYS}",
    )
    p.add_argument(
        "--tau-max",
        type=int,
        default=SVI_TAU_MAX_DAYS,
        help=f"仅拟合 τ≤该值（天），默认 {SVI_TAU_MAX_DAYS}",
    )
    p.add_argument(
        "--n-jobs",
        type=int,
        default=-2,
        help="joblib 并行作业数（默认 -2，与 BTC 一致）",
    )
    p.add_argument("--seed", type=int, default=None, help="随机种子（可复现性）")
    args = p.parse_args()

    iv_folder = args.iv_folder.resolve()
    if not iv_folder.is_dir():
        print(
            f"错误：IV 目录不存在: {iv_folder}\n"
            "请先运行 S3 生成日度 IV 矩阵（默认会创建本目录并写入 IV_matrix_*.csv），例如：\n"
            f"  python3 scripts/S3_prepare_moneyness_eth.py -i <链表.csv> -o {ETH_OPTIONS_IV_OUT_DIR}\n"
            "若矩阵在其他位置，请使用：  --iv-folder <含 IV_matrix_*.csv 的目录>",
            file=sys.stderr,
        )
        raise SystemExit(2)

    csv_files = _collect_iv_files(iv_folder)
    if not csv_files:
        print(
            f"错误：目录中无 IV_matrix_*.csv: {iv_folder}\n"
            "请确认已运行 S3，且文件名以 IV 开头、扩展名为 .csv。",
            file=sys.stderr,
        )
        raise SystemExit(2)

    if args.tau_min > args.tau_max:
        print("错误：--tau-min 不能大于 --tau-max", file=sys.stderr)
        raise SystemExit(2)

    print(f"IV 目录: {iv_folder}（{len(csv_files)} 个文件）")
    print(f"拟合 τ 范围: [{args.tau_min}, {args.tau_max}]（天）")

    results = Parallel(n_jobs=args.n_jobs)(
        delayed(process_csv_file)(fp, args.seed, args.tau_min, args.tau_max) for fp in csv_files
    )

    all_results: List[dict] = []
    all_thetas: List[List[Any]] = []
    for res_list, theta_list in results:
        all_results.extend(res_list)
        all_thetas.extend(theta_list)

    if not all_results:
        print("未得到任何拟合结果。", file=sys.stderr)
        raise SystemExit(1)

    results_df = pd.DataFrame(all_results).sort_values(by="Date")
    thetas_df = pd.DataFrame(
        all_thetas, columns=["filename", "tau", "a", "b", "rho", "m", "sigma"]
    ).sort_values(by="filename")

    _write_full_svi_tables(results_df, thetas_df, ETH_SVI_FULL_OUT_DIR)


if __name__ == "__main__":
    main()
