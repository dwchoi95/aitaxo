# Results summary (script-generated; FAMILY is primary, leaf exploratory)

Submissions: 2800 (human 1397, AI 1403)
Between-arm differences are conservative lower bounds (non-differential judge error).

## RQ1 FAMILY (primary)
overall: {'test': 'chi2', 'statistic': 412.97573175820753, 'p_value': 1.0743597932293326e-81, 'dof': 11, 'cramers_v': 0.3711474246980246}
families significant after BH-FDR: 10
  GE1: human 0.107 vs AI 0.401  (h=0.71, q=1.39e-73)
  GE3: human 0.093 vs AI 0.038  (h=0.23, q=1.47e-08)
  GE4: human 0.160 vs AI 0.091  (h=0.21, q=1.04e-07)
  GE6: human 0.040 vs AI 0.009  (h=0.21, q=2.07e-07)
  GE5: human 0.075 vs AI 0.031  (h=0.20, q=4.89e-07)
  AE2: human 0.078 vs AI 0.037  (h=0.18, q=6.15e-06)
  AE4: human 0.009 vs AI 0.000  (h=0.19, q=0.000398)
  AE6: human 0.031 vs AI 0.011  (h=0.14, q=0.000501)
  AE3: human 0.075 vs AI 0.043  (h=0.14, q=0.000545)
  AE1: human 0.305 vs AI 0.360  (h=0.12, q=0.00242)

## RQ1 leaf (exploratory)
overall: {'test': 'chi2', 'statistic': 624.1315744105815, 'p_value': 2.9542997729904607e-112, 'dof': 30, 'cramers_v': 0.45543560835401325}
leaves significant after BH-FDR: 21
  GE1.2: human 0.034 vs AI 0.170  (h=0.48, q=4.08e-33)
  GE1.1: human 0.072 vs AI 0.228  (h=0.45, q=7.77e-31)
  AE3.2: human 0.054 vs AI 0.007  (h=0.30, q=3.47e-13)
  GE2.2: human 0.041 vs AI 0.003  (h=0.30, q=8.47e-13)
  GE3.2: human 0.054 vs AI 0.014  (h=0.23, q=7.48e-09)
  GE2.1: human 0.026 vs AI 0.072  (h=0.22, q=4.59e-08)
  GE6.1: human 0.037 vs AI 0.007  (h=0.22, q=7.9e-08)
  AE1.2: human 0.019 vs AI 0.001  (h=0.23, q=2.83e-07)
  GE5.1: human 0.075 vs AI 0.031  (h=0.20, q=3.06e-07)
  AE3.1: human 0.009 vs AI 0.034  (h=0.19, q=6.07e-06)
  GE4.2: human 0.117 vs AI 0.068  (h=0.17, q=1.34e-05)
  AE1.1: human 0.286 vs AI 0.359  (h=0.16, q=6.24e-05)

## RQ2 problem-clustered models: family 10, leaf 17 (see rq2_*_adjusted.csv)
## Saturation: {'final_distinct': 23, 'still_rising': False}
## Distributions: dist_leaf_by_arm.csv, dist_family_by_arm.csv
## RQ3 persistence: {'turn0': 152, 'residual': 144} (see rq3_persistence_*.csv)
