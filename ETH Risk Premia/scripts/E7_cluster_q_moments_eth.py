#!/usr/bin/env python3
"""
E7：按 **S7** 聚类标签，汇总 **OA / HV / LV** 的 **Q_matrix** 矩（S6_1）；积分与
``function.compute_density_moments`` 一致。

**本仓库 moneyness 定义（线性、非对数收益）**

- **S3**（``scripts/S3_prepare_moneyness_eth.py``）：链上逐笔聚合后定义 ::
      moneyness = K/S - 1
  即 **现货价** ``S``、行权价 ``K`` 下的 **相对偏离**：平价附近 ``m≈0``，等价 ``K/S = 1 + m``。
- **IV 曲面 / Q_matrix** 在 ``moneyness_step_0d01`` 下用的格点即上述 **m**；``Q_matrix`` 行索引名 ``Return``
  为历史命名，**轴变量仍是 ``m``（K/S-1）**，**不是** ``log(K/S)``，也不是``\\log(S_T/S_t)`` 持有期收益。
- **Rookley / ``eth_Q_*.csv``** 内部会用到 ``ret = log(K/S) = log(1+m)`` 作中间自变量；**对 Q 矩做全局解释时
  应以 ``Q_matrix`` 的 ``m`` 为准**。

**默认积分区间（全局）**

- 默认读 **``Q_matrix_{ttm}day.csv``**，行为 ``function._GRID_FULL`` 上的 **m∈[-1,1]**（步长约 0.01），
  **梯形积分覆盖整条支撑**，与 **S6_1_step4** 矩筛选同一全网格。
- 若加 ``--d15``，则改读 ``Q_matrix_{ttm}day_d15.csv``（**仅 |m|≤0.15**），与 **S7** 聚类用的窄带一致，
  **不包含两翼**；仅用于和聚类截面横向对比。

**公式（``q(m)`` 在所用 ``m`` 格上已按 S6_1 对全 [-1,1] 归一；``\\tau``=``ttm_days``）**

- :math:`\\mu_1=\\int q(m)\\,m\\,dm`（积分为所选矩阵行的整条网格）；
- ``mean_ann`` / ``variance_ann`` = :math:`\\mu_1(365/\\tau)`，:math:`\\mu_2(365/\\tau)`；
- ``skewness``、``excess_kurtosis`` 定义同 ``function.compute_density_moments``。

**HV / LV / OA**：**OA** = ``common_dates_cluster`` 全部日期，``cluster=-1``。

**输出**：``.../Q_moments/q_moments_by_cluster.csv``（列 ``q_matrix_grid`` 为 ``full`` 或 ``d15``）。

用法::

    python3 scripts/E7_cluster_q_moments_eth.py
    python3 scripts/E7_cluster_q_moments_eth.py --d15
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from function import (  # noqa: E402
    ETH_Q_MATRIX_MON_STEP_SUBDIR,
    ETH_Q_MATRIX_OUT_DIR,
    PRIMARY_TTMS,
    clustering_multivariate_run_dir,
    compute_density_moments,
)

ETH_CLUSTERING_Q_MOMENTS_DIR = clustering_multivariate_run_dir() / "Q_moments"
DEFAULT_OUT_CSV = ETH_CLUSTERING_Q_MOMENTS_DIR / "q_moments_by_cluster.csv"


def load_q_matrix(ttm: int, *, q_root: Path, use_d15: bool) -> pd.DataFrame:
    """行 = ``m``（K/S-1），列 = 日期；与 ``S7_multivariate_clustering_eth.load_q_matrix`` 一致。"""
    suffix = "_d15" if use_d15 else ""
    name = f"Q_matrix_{ttm}day{suffix}.csv"
    path = q_root / name
    if not path.is_file():
        raise FileNotFoundError(f"missing Q_matrix (run S6_1): {path}")
    df = pd.read_csv(path, index_col=0)
    if "Return" in df.columns:
        df = df.set_index("Return")
    df.columns = [str(c) for c in df.columns]
    return df


def _regime_label(cluster_id: int) -> str:
    if cluster_id == 0:
        return "HV"
    if cluster_id == 1:
        return "LV"
    return f"cluster_{cluster_id}"


def mean_moments_over_dates_qmatrix(
    dates: Sequence[str],
    *,
    ttm: int,
    q_df: pd.DataFrame,
) -> Tuple[Optional[np.ndarray], int, int, int]:
    """Each day: ``compute_density_moments`` on moneyness index and column (S6_1 / BTC)."""
    grid = q_df.index.to_numpy(dtype=float)
    moment_rows: List[np.ndarray] = []
    n_skip_nf = 0
    n_skip_err = 0
    for d in dates:
        if d not in q_df.columns:
            n_skip_nf += 1
            continue
        try:
            q = np.maximum(q_df[d].to_numpy(dtype=float), 0.0)
            moment_rows.append(compute_density_moments(grid, q, ttm))
        except Exception:
            n_skip_err += 1
            continue
    if not moment_rows:
        return None, 0, n_skip_nf, n_skip_err
    stack = np.vstack(moment_rows)
    return stack.mean(axis=0), len(moment_rows), n_skip_nf, n_skip_err


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "E7：按 S7 聚类汇总 Q 矩（function.compute_density_moments，类内对有效日取平均）"
        )
    )
    p.add_argument(
        "--cluster-csv",
        type=Path,
        default=None,
        help="common_dates_cluster.csv（默认 clustering_multivariate_run_dir()）",
    )
    p.add_argument(
        "--matrix-root",
        type=Path,
        default=ETH_Q_MATRIX_OUT_DIR / ETH_Q_MATRIX_MON_STEP_SUBDIR,
        help="S6_1 Q_matrix 目录（含 Q_matrix_{ttm}day.csv）",
    )
    p.add_argument(
        "--d15",
        action="store_true",
        help="使用 Q_matrix_{ttm}day_d15.csv（|m|<=0.15，与 S7 聚类同宽）；默认全网格 m∈[-1,1]",
    )
    p.add_argument(
        "--ttms",
        type=int,
        nargs="+",
        default=list(PRIMARY_TTMS),
        help="到期天数，须与 S7 使用的 tau 一致，默认 9 27 45",
    )
    p.add_argument(
        "--out-csv",
        type=Path,
        default=DEFAULT_OUT_CSV,
        help=f"输出 CSV（默认 {DEFAULT_OUT_CSV}）",
    )
    args = p.parse_args()

    cluster_path = args.cluster_csv or (clustering_multivariate_run_dir() / "common_dates_cluster.csv")
    if not cluster_path.is_file():
        raise SystemExit(f"缺少聚类结果: {cluster_path}")

    lab = pd.read_csv(cluster_path)
    if "Date" not in lab.columns or "Cluster" not in lab.columns:
        raise SystemExit(f"需要列 Date, Cluster: {cluster_path}")
    lab["Date"] = lab["Date"].astype(str)
    lab["Cluster"] = lab["Cluster"].astype(int)
    dates_oa = sorted(lab["Date"].unique())

    use_d15 = args.d15
    q_grid_tag = "d15" if use_d15 else "full"
    rows: List[dict] = []
    for ttm in args.ttms:
        try:
            q_df = load_q_matrix(ttm, q_root=args.matrix_root, use_d15=use_d15)
        except FileNotFoundError as e:
            print(f"警告: {e}，跳过 ttm={ttm}", file=sys.stderr)
            continue
        regimes: List[Tuple[int, str, Sequence[str]]] = [
            (-1, "OA", dates_oa),
            (
                0,
                _regime_label(0),
                sorted(lab.loc[lab["Cluster"] == 0, "Date"].unique()),
            ),
            (
                1,
                _regime_label(1),
                sorted(lab.loc[lab["Cluster"] == 1, "Date"].unique()),
            ),
        ]
        for cluster_id, regime_label, date_list in regimes:
            mu, n_used, n_skip_nf, n_skip_err = mean_moments_over_dates_qmatrix(
                date_list, ttm=ttm, q_df=q_df
            )
            if mu is None:
                print(
                    f"警告: ttm={ttm} {regime_label} 无有效 Q 文件 "
                    f"(缺文件 {n_skip_nf}, 读入失败 {n_skip_err})",
                    file=sys.stderr,
                )
                continue
            rows.append(
                {
                    "cluster": cluster_id,
                    "regime_label": regime_label,
                    "q_matrix_grid": q_grid_tag,
                    "ttm_days": ttm,
                    "n_dates_used": n_used,
                    "n_dates_missing_file": n_skip_nf,
                    "n_dates_load_failed": n_skip_err,
                    "mean_Q_ann_mean": mu[0],
                    "variance_Q_ann_mean": mu[1],
                    "skewness_Q_mean": mu[2],
                    "excess_kurtosis_Q_mean": mu[3],
                }
            )
            print(
                f"ttm={ttm} {regime_label}: n={n_used} "
                f"(skip_missing={n_skip_nf} skip_err={n_skip_err})",
                file=sys.stderr,
            )

    if not rows:
        raise SystemExit("未生成任何汇总行；请检查 --matrix-root 与 Q_matrix 文件。")

    out = pd.DataFrame(rows)
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out_csv, index=False)
    print(f"写出: {args.out_csv}")
    print(
        "Columns: q_matrix_grid=full (m in [-1,1]) or d15; daily moments then regime mean. "
        "Moneyness axis m=K/S-1 (see module docstring).",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
