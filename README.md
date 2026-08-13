# Paper 1: Material Price Drivers in Uganda Housing

Independent folder for your PhD paper execution package.

## Core empirical question

How national fiscal policy and macroeconomic shocks directly drive material price changes in residential and non-residential construction in Uganda.

## Methods implemented

- Vector Autoregression (VAR): dynamic propagation, Granger causality, IRFs, FEVD.
- ARDL: short-run distributed lag effects and long-run multipliers.

## Run

Use the workspace Python environment:

- /Users/charlesgava/Documents/Projects /Housing Paper 1 + CIO/cio_pipeline-2/.venv/bin/python

Execute:

- run_paper1_analysis.py (earlier baseline package)
- run_housing_var_ardl.py (housing-focused VAR/ARDL package requested)

## Main narrative outputs

- RESULTS_DISCUSSION_METHODS.md
- DETAILED_COMPREHENSIVE_REPORT.md
- PAPER1_EXECUTION_REPORT.md

## Housing VAR/ARDL outputs

- output_housing/model_meta.json
- output_housing/var_granger_results.csv
- output_housing/var_irf_summary.csv
- output_housing/var_fevd_12m.csv
- output_housing/ardl_coefficients.csv
- output_housing/ardl_long_run.csv
- output_housing/ardl_significant_terms.csv

## Housing figures

- figures_housing/fig1_timeseries_zscores.png
- figures_housing/fig2_correlation_heatmap.png
- figures_housing/fig3_irf_exchange_rate.png
- figures_housing/fig4_irf_fuel.png
- figures_housing/fig5_irf_imports.png
- figures_housing/fig6_fevd_12m.png
- figures_housing/fig7_ardl_longrun.png
