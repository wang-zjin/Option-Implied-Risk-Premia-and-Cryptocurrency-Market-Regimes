# Risk Premia in the Bitcoin Market

Research codes and selected output files for the paper *Option-Implied-Risk-Premia-and-Cryptocurrency-Market-Regimes*, by Caio Almeida, Maria Grith, Ratmir Miftachov and Zijin Wang.

## Abstract

We analyze the first and second moment risk premia in the Bitcoin market based on options and realized returns. The results show that Bitcoin is much more volatile and has higher premia than the S&P 500 stock index. By decomposing the return premium into different regions of the return state space, we find that while most of the S&P 500 equity premium comes from mildly negative returns, the corresponding negative Bitcoin returns (between three and one standard deviations)  account for only one-third of the total Bitcoin premium (BP). The decomposition of the Bitcoin variance risk premium (BVRP) reveals a dominant positive contribution from upside return states, in contrast to the S\&P 500, where the VRP is primarily driven by downside returns. Further, applying a novel clustering algorithm to a collection of estimated Bitcoin option-implied risk-neutral densities, we find that risk premia vary over time as a function of two distinct market volatility regimes. The low-volatility regime is associated with lower $\bp$ and $\bvrp$, and the share of the total premia attributable to positive returns is higher in magnitude. These results suggest that in stable markets, Bitcoin investors place relatively higher importance on upside return and variance risk.

- SSRN working paper, posted August 1, 2025: [Risk Premia in the Bitcoin Market](https://ssrn.com/abstract=5374295)
- arXiv preprint, submitted October 19, 2024 and revised August 1, 2025: [Risk Premia in the Bitcoin Market](https://arxiv.org/abs/2410.15195)

## Repository Overview

This repository is organized around two main workstreams:

- `BTC Risk Premia/`: Bitcoin-focused empirical analysis, decomposition exercises, tables, figures, and supplementary materials.
- `ETH Risk Premia/`: ETH extension pipeline, including scripts and a large set of generated result files for multiple maturities.

The implementation uses a mix of:

- Python scripts
- MATLAB scripts
- Jupyter notebooks

## Directory Guide

```text
.
├── BTC Risk Premia/
│   ├── main/
│   ├── CL2020/
│   ├── CL2024/
│   └── SS2025/
├── ETH Risk Premia/
│   ├── scripts/
│   └── results/
├── LICENSE
└── README.md
```


## Suggested Citation

```bibtex
@article{almeida2025risk,
  title   = {Risk Premia in the Bitcoin Market},
  author  = {Almeida, Caio and Grith, Maria and Miftachov, Ratmir and Wang, Zijin},
  journal = {arXiv preprint arXiv:2410.15195},
  year    = {2025},
  doi     = {10.48550/arXiv.2410.15195},
  url     = {https://arxiv.org/abs/2410.15195}
}
```

SSRN version:

```bibtex
@misc{almeida2025riskssrn,
  title = {Risk Premia in the Bitcoin Market},
  author = {Grith, Maria and Almeida, Caio and Miftachov, Ratmir and Wang, Zijin},
  year = {2025},
  note = {SSRN Working Paper 5374295},
  doi = {10.2139/ssrn.5374295},
  url = {https://ssrn.com/abstract=5374295}
}
```

## License

This repository is released under the MIT License. See [LICENSE](LICENSE) for details.
