# paper1-macro-fiscal-drivers-uganda

Python analysis scripts and outputs for a study of how fiscal policy and macroeconomic shocks drive construction material prices in Uganda, using vector autoregression (VAR: Granger causality, impulse responses, variance decomposition) and ARDL models.

## Contents

| Path | What it is |
|---|---|
| `run_paper1_analysis.py` | Baseline analysis (regressions and forecasts) → `output/`, `figures/` |
| `run_housing_var_ardl.py` | Housing-focused VAR and ARDL analysis → `output_housing/`, `figures_housing/` |
| `output/` | Analysis dataset, regression coefficients, significant effects, forecast paths and metrics, run summary |
| `output_housing/` | ARDL coefficients and long-run multipliers, VAR Granger tests, impulse-response and FEVD summaries, model metadata |
| `figures/`, `figures_housing/` | Figures for the two analyses |
| `RESULTS_DISCUSSION_METHODS.md`, `DETAILED_COMPREHENSIVE_REPORT.md`, `PAPER1_EXECUTION_REPORT.md` | Write-ups of methods and results |

## Running

The scripts read the data panel built by [cio_pipeline-2](https://github.com/gavacharles/cio_pipeline-2) and use that project's Python environment:

```
python run_paper1_analysis.py
python run_housing_var_ardl.py
```
