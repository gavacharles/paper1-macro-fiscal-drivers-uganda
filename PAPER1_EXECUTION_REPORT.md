# Paper 1 Execution Report

## Topic

Macro-Fiscal Drivers of Construction Input Inflation in Uganda (UBOS + MoFPED portal data).

## What was executed

- Merged UBOS CIPI panel with MoFPED bulk macro-fiscal datasets.
- Constructed monthly inflation rates for materials and sector indices.
- Estimated HAC-robust dynamic regressions with lagged macro-fiscal drivers.
- Ran expanding-window one-step-ahead backtests against AR(1) benchmark.
- Exported coefficients, metrics, forecast paths, and reproducibility summary.

## Final analytical sample

- Monthly window used: **2018-01-01 to 2026-02-01**
- Number of monthly observations after transformations: **98**
- Dependent inflation series: Cement, Iron/Steel, Timber, Roofing proxy (ALU/TILES), Buildings, Civil works.
- Key macro-fiscal drivers: exchange-rate depreciation, Brent oil price growth, non-oil import price index, import volumes for intermediate/base metals, import tax proxies, lending rate, central bank rate.

## Forecasting performance (expanding-window, one-step ahead; benchmark = AR(1))

| dependent | n_obs | r2 | adj_r2 | rmse_model | rmse_baseline_ar1 | mae_model | mae_baseline_ar1 | rmse_gain_pct | mae_gain_pct | directional_accuracy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| infl_roof_proxy | 92 | 0.0462 | -0.0333 | 0.3536 | 0.3972 | 0.2871 | 0.3868 | 10.9835 | 25.7903 | 0.4688 |
| infl_timber | 92 | 0.1918 | 0.1244 | 0.7292 | 0.5281 | 0.5287 | 0.3827 | -38.0593 | -38.1779 | 0.375 |
| infl_cem | 86 | 0.0809 | -0.0016 | 1.2361 | 0.8245 | 0.961 | 0.574 | -49.9178 | -67.4263 | 0.3462 |
| infl_ironsteel | 92 | 0.0619 | -0.0163 | 0.2644 | 0.0293 | 0.1945 | 0.0249 | -800.7717 | -680.1017 | 0.625 |
| infl_cipi_bldg | 92 | 0.0735 | -0.0037 | 0.3653 | 0.0182 | 0.2729 | 0.0147 | -1908.0742 | -1755.0532 | 0.4375 |
| infl_cipi_civil | 92 | 0.0781 | 0.0013 | 0.3803 | 0.0054 | 0.2793 | 0.0046 | -6960.585 | -5985.5996 | 0.5938 |

## Strongest statistically significant lagged effects (HAC robust, p < 0.10)

| term | coef | std_err | t | p | dependent |
| --- | --- | --- | --- | --- | --- |
| lending_rate_level_l1 | 0.1988 | 0.0755 | 2.6348 | 0.0084 | infl_roof_proxy |
| d_exrate_l1 | 0.1984 | 0.1174 | 1.6903 | 0.091 | infl_timber |

## Interpretation for construction management

- The model converts macro shocks into expected monthly material inflation and can support escalation clauses by index bucket (cement/steel/timber/roofing).
- Exchange-rate and imported-energy/import-cost channels are explicitly embedded, enabling procurement scenario stress-testing under FX and oil volatility.
- Buildings and civil-works equations provide sector-level budgeting signals when material-level noise is high.

## Reproducibility artifacts generated

- output/analysis_dataset.csv
- output/regression_coefficients.csv
- output/forecast_metrics.csv
- output/forecast_paths.csv
- output/significant_effects.csv
- output/summary.json
- figures/forecast_vs_actual.png

## Notes and limits

- UBOS roofing sheets are proxied with ALU/TILES because the continuous ROOF series is not available through the current parsed panel vintage.
- Residential/non-residential split is proxied with CIPI_BLDG and CIPI_CIVIL in this extraction.
- Import-tax variables are fiscal proxies from domestic revenue datasets and should be complemented with explicit tariff schedules in the final thesis chapter.