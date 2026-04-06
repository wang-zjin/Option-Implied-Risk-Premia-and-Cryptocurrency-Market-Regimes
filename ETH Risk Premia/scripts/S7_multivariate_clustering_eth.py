#!/usr/bin/env python3
"""
S7：多变量聚类（**基于 Q**，非 IV）。

对齐 BTC ``S5_0_multivariate_clustering_9_27_45.ipynb``：读入多条 **ttm** 的 ``Q_matrix_{ttm}day[_d15].csv``（**S6_1**），
对**日期**在 CLR 后的 Q 向量（跨 moneyness 网格 × 多 τ 拼接）上做 **Ward** 层次聚类，写出 ``common_dates_cluster.csv``
（Date, Cluster），**Cluster：0 = HV，1 = LV**（与 BTC ``S8_raw_IV_multivariate_cluster_9_27_45.py`` 一致）。

默认 **ttm = 9, 27, 45**，默认使用 ``_d15`` 窄网格文件（与 BTC 笔记本一致）。

**先决**：须先完成 **S6_1**（对应 ttm 的 ``Q_matrix_*_d15.csv``）。**与 S6_3（ETH-VIX）无数据依赖**。

**默认输出目录**（可用 ``--out-dir`` 覆盖）::

    results/Clustering/moneyness_step_0d01/multivariate_clustering_9_27_45/

**生成文件**

- ``common_dates_cluster.csv``：列 ``Date``, ``Cluster``（0=HV，1=LV）。
- ``clustering_run_meta.json``：运行参数与簇频数。
- 若加 ``--plot``：``dendrogram.png``（树状图）。

**命令说明**（在仓库 ``deribit/`` 根下执行；``python3`` 可改为 ``python``）::

    # 默认：ttm 9/27/45，使用 _d15，二类聚类，并按 Q 隐含方差定向 HV/LV
    python3 scripts/S7_multivariate_clustering_eth.py

    # 查看全部参数
    python3 scripts/S7_multivariate_clustering_eth.py --help

    # 同时保存树状图
    python3 scripts/S7_multivariate_clustering_eth.py --plot

    # 与 BTC 笔记本类似：按树高切分（指定时不再使用 --n-clusters）
    python3 scripts/S7_multivariate_clustering_eth.py --cut-height 40

    # 使用全网格 Q_matrix（无 _d15 后缀）
    python3 scripts/S7_multivariate_clustering_eth.py --no-d15

    # 自定义 Q 矩阵目录（须含各 ttm 的 Q_matrix_*day*.csv）
    python3 scripts/S7_multivariate_clustering_eth.py --q-root results/Q_matrix/moneyness_step_0d01

    # 自定义输出目录
    python3 scripts/S7_multivariate_clustering_eth.py --out-dir results/Clustering/moneyness_step_0d01/multivariate_clustering_9_27_45

    # 仅输出算法簇编号、不做 HV/LV 定向（下游若假定 0=HV 需自行核对）
    python3 scripts/S7_multivariate_clustering_eth.py --no-relabel

    # 指定多 τ（至少 2 个）
    python3 scripts/S7_multivariate_clustering_eth.py --ttms 9 27 45
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Sequence, Tuple

import numpy as np
import pandas as pd
import scipy.cluster.hierarchy as sch
from scipy.cluster.hierarchy import cut_tree, linkage
from scipy.spatial.distance import pdist
from scipy.stats.mstats import gmean

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from function import (  # noqa: E402
    ETH_Q_MATRIX_MON_STEP_SUBDIR,
    ETH_Q_MATRIX_OUT_DIR,
    PRIMARY_TTMS,
    clustering_multivariate_run_dir,
)


def _trapz(y: np.ndarray, x: np.ndarray) -> float:
    if hasattr(np, "trapezoid"):
        return float(np.trapezoid(y, x))
    return float(np.trapz(y, x))


def q_implied_variance(ret_grid: np.ndarray, q_raw: np.ndarray) -> float:
    """风险中性分布下关于 Return 的二阶中心矩（梯形积分），用于 HV/LV 定向。"""
    q_raw = np.maximum(q_raw.astype(float), 0.0)
    s = _trapz(q_raw, ret_grid)
    if s <= 1e-15 or not np.isfinite(s):
        return float("nan")
    q = q_raw / s
    m = _trapz(q * ret_grid, ret_grid)
    v = _trapz(q * (ret_grid - m) ** 2, ret_grid)
    return float(v)


def clr_columns(df: pd.DataFrame) -> pd.DataFrame:
    """对每一列（交易日）做 CLR：log x - log gmean(x)；x 截断为正。"""
    out = {}
    for col in df.columns:
        x = df[col].to_numpy(dtype=float)
        x = np.maximum(x, 1e-15)
        gm = float(gmean(x))
        if gm <= 0 or not np.isfinite(gm):
            gm = 1e-15
        out[col] = np.log(x) - np.log(gm)
    return pd.DataFrame(out, index=df.index)


def load_q_matrix(
    ttm: int,
    *,
    q_root: Path,
    use_d15: bool,
) -> pd.DataFrame:
    """行索引为 Return 网格，列为日期字符串。"""
    suffix = "_d15" if use_d15 else ""
    name = f"Q_matrix_{ttm}day{suffix}.csv"
    path = q_root / name
    if not path.is_file():
        raise FileNotFoundError(f"缺少 Q 矩阵文件（请先跑 S6_1）：{path}")
    df = pd.read_csv(path, index_col=0)
    if "Return" in df.columns:
        df = df.set_index("Return")
    df.columns = [str(c) for c in df.columns]
    return df


def common_date_columns(dfs: Sequence[pd.DataFrame]) -> List[str]:
    cols = [set(df.columns) for df in dfs]
    inter = set.intersection(*cols) if cols else set()
    # ISO 日期字符串字典序 = 时间序
    return sorted(inter)


def hierarchical_labels(
    X: np.ndarray,
    *,
    n_clusters: int | None,
    cut_height: float | None,
) -> np.ndarray:
    """Ward + 按类数或高度切树。"""
    d = pdist(X, metric="euclidean")
    Z = linkage(d, method="ward")
    if cut_height is not None:
        lab = cut_tree(Z, height=cut_height)
    elif n_clusters is not None:
        lab = cut_tree(Z, n_clusters=n_clusters)
    else:
        lab = cut_tree(Z, n_clusters=2)
    if lab.ndim == 2:
        lab = lab[:, 0]
    return np.asarray(lab).astype(int).ravel()


def relabel_hv_zero_lv_one(
    raw: np.ndarray,
    variance_per_date: np.ndarray,
) -> Tuple[np.ndarray, bool]:
    """
    使 **Cluster 0 = HV（更高 Q 隐含方差）**、**1 = LV**。
    若第一簇已方差更大则不变；否则对标签取 1-raw。
    返回 (final_labels, swapped)。
    """
    raw = np.asarray(raw).astype(int).ravel()
    m0 = np.nanmean(variance_per_date[raw == 0])
    m1 = np.nanmean(variance_per_date[raw == 1])
    if not np.isfinite(m0) or not np.isfinite(m1):
        return raw, False
    if m0 >= m1:
        return raw, False
    return 1 - raw, True


def run_clustering(
    ttms: Sequence[int],
    *,
    q_root: Path,
    use_d15: bool,
    n_clusters: int | None,
    cut_height: float | None,
    relabel: bool,
) -> Tuple[pd.DataFrame, np.ndarray, List[pd.DataFrame]]:
    dfs = [load_q_matrix(t, q_root=q_root, use_d15=use_d15) for t in ttms]
    dates = common_date_columns(dfs)
    if len(dates) < 2:
        raise ValueError(
            f"共同交易日不足 2 日（当前 {len(dates)}），无法做二类聚类。"
        )

    dfs_c = [clr_columns(df[dates]) for df in dfs]
    ret0 = dfs[0].index.to_numpy(dtype=float)

    concatenated_vectors: List[np.ndarray] = []
    variances: List[float] = []
    for d in dates:
        parts = [dfc[d].to_numpy(dtype=float) for dfc in dfs_c]
        concatenated_vectors.append(np.concatenate(parts))
        variances.append(q_implied_variance(ret0, dfs[0][d].to_numpy(dtype=float)))

    X = np.asarray(concatenated_vectors)
    var_arr = np.asarray(variances)

    raw = hierarchical_labels(X, n_clusters=n_clusters, cut_height=cut_height)
    uniq = np.unique(raw)
    if len(uniq) != 2:
        raise RuntimeError(
            f"切树得到 {len(uniq)} 类（期望 2 类）。请调整 --cut-height 或检查数据。"
        )

    swapped = False
    if relabel:
        labels, swapped = relabel_hv_zero_lv_one(raw, var_arr)
    else:
        labels = raw

    out = pd.DataFrame({"Date": dates, "Cluster": labels})
    out.attrs["relabel_swapped"] = swapped
    return out, X, dfs


def main() -> None:
    _epilog = """
命令示例（在 deribit/ 根目录）:
  python3 scripts/S7_multivariate_clustering_eth.py
  python3 scripts/S7_multivariate_clustering_eth.py --plot
  python3 scripts/S7_multivariate_clustering_eth.py --cut-height 40
  python3 scripts/S7_multivariate_clustering_eth.py --no-d15
  python3 scripts/S7_multivariate_clustering_eth.py --q-root results/Q_matrix/moneyness_step_0d01
  python3 scripts/S7_multivariate_clustering_eth.py --no-relabel
  python3 scripts/S7_multivariate_clustering_eth.py --ttms 9 27 45

默认写出: results/Clustering/moneyness_step_0d01/multivariate_clustering_9_27_45/
  common_dates_cluster.csv, clustering_run_meta.json；--plot 时另有 dendrogram.png
"""
    p = argparse.ArgumentParser(
        description=(
            "S7：多 τ Q_matrix → Ward 层次聚类 → common_dates_cluster.csv（Cluster: 0=HV, 1=LV）"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_epilog,
    )
    p.add_argument(
        "--ttms",
        type=int,
        nargs="+",
        default=list(PRIMARY_TTMS),
        help="到期日（天），默认 9 27 45",
    )
    p.add_argument(
        "--q-root",
        type=Path,
        default=ETH_Q_MATRIX_OUT_DIR / ETH_Q_MATRIX_MON_STEP_SUBDIR,
        help="Q_matrix 所在目录（含 moneyness_step_0d01）",
    )
    p.add_argument(
        "--no-d15",
        action="store_true",
        help="使用全网格 Q_matrix_{ttm}day.csv（默认用 _d15 与 BTC 笔记本一致）",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="输出目录（默认 function.clustering_multivariate_run_dir()）",
    )
    p.add_argument(
        "--n-clusters",
        type=int,
        default=2,
        help="层次聚类切为 k 类（默认 2；与 --cut-height 互斥）",
    )
    p.add_argument(
        "--cut-height",
        type=float,
        default=None,
        help="按树高切分（对齐 BTC 笔记本时可试 40）；指定时忽略 --n-clusters",
    )
    p.add_argument(
        "--no-relabel",
        action="store_true",
        help="不做 HV/LV 定向（0/1 仅为算法簇编号，可能与下游 HV=0 约定不一致）",
    )
    p.add_argument(
        "--plot",
        action="store_true",
        help="保存树状图 dendrogram.png（需 matplotlib）",
    )
    args = p.parse_args()

    ttms = list(args.ttms)
    if len(ttms) < 2:
        raise SystemExit("至少需要 2 个 ttm 才能做多变量（跨 τ）聚类。")

    use_d15 = not args.no_d15
    out_dir = args.out_dir or clustering_multivariate_run_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    cut_h = args.cut_height
    n_clust = None if cut_h is not None else args.n_clusters

    df_out, X, _dfs = run_clustering(
        ttms,
        q_root=args.q_root,
        use_d15=use_d15,
        n_clusters=n_clust,
        cut_height=cut_h,
        relabel=not args.no_relabel,
    )

    csv_path = out_dir / "common_dates_cluster.csv"
    df_out.to_csv(csv_path, index=False)

    meta = {
        "ttms": ttms,
        "q_root": str(args.q_root.resolve()),
        "use_d15": use_d15,
        "n_clusters": n_clust,
        "cut_height": cut_h,
        "relabel_hv_lv": not args.no_relabel,
        "relabel_swapped_vs_raw": bool(df_out.attrs.get("relabel_swapped", False)),
        "n_dates": int(len(df_out)),
        "cluster_counts": df_out["Cluster"].value_counts().to_dict(),
    }
    (out_dir / "clustering_run_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"写出: {csv_path}")
    print(f"样本日数: {len(df_out)}；簇计数:\n{df_out['Cluster'].value_counts()}")

    if args.plot:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        d = pdist(X, metric="euclidean")
        Z = linkage(d, method="ward")
        fig, ax = plt.subplots(figsize=(14, 5))
        sch.dendrogram(Z, ax=ax, no_labels=True)
        ax.set_title("Ward linkage (ETH multivariate Q clustering)")
        fig.tight_layout()
        fig.savefig(out_dir / "dendrogram.png", dpi=150)
        plt.close(fig)
        print(f"写出: {out_dir / 'dendrogram.png'}")


if __name__ == "__main__":
    main()
