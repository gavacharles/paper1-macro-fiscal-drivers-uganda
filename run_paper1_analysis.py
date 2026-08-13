#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt


def df_to_markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "(empty)"
    cols = list(df.columns)
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows = []
    for _, r in df.iterrows():
        vals = [str(r[c]) for c in cols]
        rows.append("| " + " | ".join(vals) + " |")
    return "\n".join([header, sep] + rows)


def load_series(path: Path, col_map: dict[str, str]) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "Date" in df.columns:
        df = df.rename(columns={"Date": "date"})
    df["date"] = pd.to_datetime(df["date"]).dt.to_period("M").dt.to_timestamp()
    keep = ["date"] + [c for c in col_map.keys() if c in df.columns]
    out = df[keep].copy().rename(columns=col_map)
    return out.groupby("date", as_index=False).mean()


def log_diff_pct(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    return 100 * np.log(s / s.shift(1))


def build_dataset(root: Path) -> pd.DataFrame:
    panel = pd.read_csv(root / "data/processed/panel_v1.0.csv")
    panel["date"] = pd.to_datetime(panel["date"]).dt.to_period("M").dt.to_timestamp()

    macro = panel[["date", "exchange_rate", "lending_rate", "central_bank_rate", "CEM", "IRONSTEEL", "TIMBER", "CIPI_BLDG", "CIPI_CIVIL"]].copy()

    # Roofing proxy: use explicit ROOF where available, otherwise blend ALU + TILES.
    roof_cols = [c for c in ["ROOF", "TILES", "ALU"] if c in panel.columns]
    if not roof_cols:
        raise RuntimeError("No roofing-related CIPI series found (ROOF/TILES/ALU).")
    macro["ROOF_PROXY"] = panel[roof_cols].mean(axis=1)

    brent = load_series(
        root / "data/raw/mofped_bulk/datasets/IMF_PCPS.csv",
        {"POILBRE_USD": "brent_usd"},
    )
    imports = load_series(
        root / "data/raw/mofped_bulk/datasets/BOU_IM_CIF.csv",
        {"IM_NOIL_P_IX": "import_price_ix", "IM_I_PS_NOIL": "intermediate_imports_noil"},
    )
    construction_imports = load_series(
        root / "data/raw/mofped_bulk/datasets/BOU_IM_C.csv",
        {"IM_BMP": "base_metals_imports", "IM_MMAN": "manufactures_imports"},
    )
    tariffs = load_series(
        root / "data/raw/mofped_bulk/datasets/MOF_REV_DOM_14.csv",
        {
            "REV_TAX_GS_EXD_IM_14": "import_excise_tax",
            "REV_TAX_GS_VAT_IM_14": "import_vat_tax",
        },
    )

    df = macro.merge(brent, on="date", how="left")
    df = df.merge(imports, on="date", how="left")
    df = df.merge(construction_imports, on="date", how="left")
    df = df.merge(tariffs, on="date", how="left")
    df = df.sort_values("date").set_index("date")

    # Forward fill small publication timing gaps only.
    df = df.ffill(limit=2)

    # Dependent variables: monthly inflation rates
    dep_src = ["CEM", "IRONSTEEL", "TIMBER", "ROOF_PROXY", "CIPI_BLDG", "CIPI_CIVIL"]
    for c in dep_src:
        df[f"infl_{c.lower()}"] = log_diff_pct(df[c])

    # Macro-fiscal drivers: mostly in monthly % changes; interest rates in levels.
    df["d_exrate"] = log_diff_pct(df["exchange_rate"])
    df["d_brent"] = log_diff_pct(df["brent_usd"])
    df["d_import_price"] = log_diff_pct(df["import_price_ix"])
    df["d_intermediate_imports"] = log_diff_pct(df["intermediate_imports_noil"])
    df["d_base_metals_imports"] = log_diff_pct(df["base_metals_imports"])
    df["d_import_excise"] = log_diff_pct(df["import_excise_tax"])
    df["d_import_vat"] = log_diff_pct(df["import_vat_tax"])

    df["lending_rate_level"] = pd.to_numeric(df["lending_rate"], errors="coerce")
    df["cbr_level"] = pd.to_numeric(df["central_bank_rate"], errors="coerce")

    return df


def run_regression_and_backtest(df: pd.DataFrame, y_col: str) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    x_cols = [
        "d_exrate",
        "d_brent",
        "d_import_price",
        "d_base_metals_imports",
        "d_import_excise",
        "lending_rate_level",
    ]

    work = df[[y_col] + x_cols].copy()
    work[f"{y_col}_l1"] = work[y_col].shift(1)
    for c in x_cols:
        work[f"{c}_l1"] = work[c].shift(1)

    model_cols = [f"{y_col}_l1"] + [f"{c}_l1" for c in x_cols]
    work = work[[y_col] + model_cols].dropna().copy()

    X = sm.add_constant(work[model_cols])
    y = work[y_col]

    full_fit = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
    coef = pd.DataFrame(
        {
            "term": full_fit.params.index,
            "coef": full_fit.params.values,
            "std_err": full_fit.bse.values,
            "t": full_fit.tvalues.values,
            "p": full_fit.pvalues.values,
        }
    )
    coef["dependent"] = y_col

    # Expanding-window one-step-ahead backtest
    min_train = min(60, int(len(work) * 0.7))
    preds = []
    for t in range(min_train, len(work)):
        tr = work.iloc[:t]
        te = work.iloc[t : t + 1]
        Xtr = sm.add_constant(tr[model_cols])
        ytr = tr[y_col]
        fit = sm.OLS(ytr, Xtr).fit()
        Xte = sm.add_constant(te[model_cols], has_constant="add")
        yhat = float(fit.predict(Xte).iloc[0])
        ytrue = float(te[y_col].iloc[0])

        # Baseline AR(1): y_t on const + y_{t-1}
        b_cols = [f"{y_col}_l1"]
        bfit = sm.OLS(ytr, sm.add_constant(tr[b_cols])).fit()
        yhat_base = float(bfit.predict(sm.add_constant(te[b_cols], has_constant="add")).iloc[0])

        preds.append({"date": te.index[0], "actual": ytrue, "model": yhat, "baseline_ar1": yhat_base})

    pred_df = pd.DataFrame(preds)
    rmse_model = float(np.sqrt(np.mean((pred_df["actual"] - pred_df["model"]) ** 2)))
    rmse_baseline = float(np.sqrt(np.mean((pred_df["actual"] - pred_df["baseline_ar1"]) ** 2)))
    mae_model = float(np.mean(np.abs(pred_df["actual"] - pred_df["model"])))
    mae_baseline = float(np.mean(np.abs(pred_df["actual"] - pred_df["baseline_ar1"])))
    dir_acc = float(np.mean(np.sign(pred_df["actual"]) == np.sign(pred_df["model"])))

    metrics = {
        "dependent": y_col,
        "n_obs": int(len(work)),
        "r2": float(full_fit.rsquared),
        "adj_r2": float(full_fit.rsquared_adj),
        "rmse_model": rmse_model,
        "rmse_baseline_ar1": rmse_baseline,
        "mae_model": mae_model,
        "mae_baseline_ar1": mae_baseline,
        "rmse_gain_pct": float(100 * (rmse_baseline - rmse_model) / rmse_baseline),
        "mae_gain_pct": float(100 * (mae_baseline - mae_model) / mae_baseline),
        "directional_accuracy": dir_acc,
    }

    return coef, metrics, pred_df


def plot_forecasts(all_preds: pd.DataFrame, out_png: Path) -> None:
    dep_list = all_preds["dependent"].unique()
    n = len(dep_list)
    fig, axes = plt.subplots(n, 1, figsize=(11, 2.8 * n), sharex=True)
    if n == 1:
        axes = [axes]

    for ax, dep in zip(axes, dep_list):
        d = all_preds[all_preds["dependent"] == dep]
        ax.plot(d["date"], d["actual"], label="Actual", linewidth=1.4)
        ax.plot(d["date"], d["model"], label="Model", linewidth=1.2)
        ax.set_title(dep)
        ax.axhline(0, color="grey", linewidth=0.7)
        ax.grid(alpha=0.25)

    axes[0].legend(loc="upper right")
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=180)
    plt.close(fig)


def write_report(out_dir: Path, summary: dict, metrics: pd.DataFrame, top_effects: pd.DataFrame) -> None:
    report_path = out_dir / "PAPER1_EXECUTION_REPORT.md"
    lines = []
    lines.append("# Paper 1 Execution Report\n")
    lines.append("## Topic\n")
    lines.append("Macro-Fiscal Drivers of Construction Input Inflation in Uganda (UBOS + MoFPED portal data).\n")

    lines.append("## What was executed\n")
    for step in summary["steps"]:
        lines.append(f"- {step}")

    lines.append("\n## Final analytical sample\n")
    lines.append(f"- Monthly window used: **{summary['start_date']} to {summary['end_date']}**")
    lines.append(f"- Number of monthly observations after transformations: **{summary['n_months']}**")
    lines.append("- Dependent inflation series: Cement, Iron/Steel, Timber, Roofing proxy (ALU/TILES), Buildings, Civil works.")
    lines.append("- Key macro-fiscal drivers: exchange-rate depreciation, Brent oil price growth, non-oil import price index, import volumes for intermediate/base metals, import tax proxies, lending rate, central bank rate.\n")

    lines.append("## Forecasting performance (expanding-window, one-step ahead; benchmark = AR(1))\n")
    lines.append(df_to_markdown_table(metrics))

    lines.append("\n## Strongest statistically significant lagged effects (HAC robust, p < 0.10)\n")
    if len(top_effects):
        lines.append(df_to_markdown_table(top_effects))
    else:
        lines.append("No effects passed the p < 0.10 threshold in this sample.")

    lines.append("\n## Interpretation for construction management\n")
    lines.append("- The model converts macro shocks into expected monthly material inflation and can support escalation clauses by index bucket (cement/steel/timber/roofing).")
    lines.append("- Exchange-rate and imported-energy/import-cost channels are explicitly embedded, enabling procurement scenario stress-testing under FX and oil volatility.")
    lines.append("- Buildings and civil-works equations provide sector-level budgeting signals when material-level noise is high.")

    lines.append("\n## Reproducibility artifacts generated\n")
    lines.append("- output/analysis_dataset.csv")
    lines.append("- output/regression_coefficients.csv")
    lines.append("- output/forecast_metrics.csv")
    lines.append("- output/forecast_paths.csv")
    lines.append("- output/significant_effects.csv")
    lines.append("- output/summary.json")
    lines.append("- figures/forecast_vs_actual.png")

    lines.append("\n## Notes and limits\n")
    lines.append("- UBOS roofing sheets are proxied with ALU/TILES because the continuous ROOF series is not available through the current parsed panel vintage.")
    lines.append("- Residential/non-residential split is proxied with CIPI_BLDG and CIPI_CIVIL in this extraction.")
    lines.append("- Import-tax variables are fiscal proxies from domestic revenue datasets and should be complemented with explicit tariff schedules in the final thesis chapter.")

    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    this = Path(__file__).resolve()
    root = this.parents[1]
    paper_dir = this.parent
    out_dir = paper_dir / "output"

    df = build_dataset(root)

    # Keep analysis window aligned to the panel period with stable macro coverage.
    analysis = df.loc[(df.index >= "2018-01-01") & (df.index <= "2026-02-01")].copy()

    dep_vars = [
        "infl_cem",
        "infl_ironsteel",
        "infl_timber",
        "infl_roof_proxy",
        "infl_cipi_bldg",
        "infl_cipi_civil",
    ]

    coefs = []
    metrics = []
    preds_all = []

    for y in dep_vars:
        coef, met, pred = run_regression_and_backtest(analysis, y)
        coefs.append(coef)
        metrics.append(met)
        pred["dependent"] = y
        preds_all.append(pred)

    coef_df = pd.concat(coefs, ignore_index=True)
    met_df = pd.DataFrame(metrics).sort_values("rmse_gain_pct", ascending=False)
    pred_df = pd.concat(preds_all, ignore_index=True)

    # Significant effects (exclude constant and AR term).
    sig = coef_df[(coef_df["p"] < 0.10) & (~coef_df["term"].isin(["const"]))].copy()
    sig = sig[~sig["term"].str.contains("_l1$") | sig["term"].str.contains("d_|rate")]
    sig = sig.sort_values(["dependent", "p"]).head(40)

    out_dir.mkdir(parents=True, exist_ok=True)
    analysis.to_csv(out_dir / "analysis_dataset.csv")
    coef_df.to_csv(out_dir / "regression_coefficients.csv", index=False)
    met_df.to_csv(out_dir / "forecast_metrics.csv", index=False)
    pred_df.to_csv(out_dir / "forecast_paths.csv", index=False)
    sig.to_csv(out_dir / "significant_effects.csv", index=False)

    summary = {
        "start_date": str(analysis.index.min().date()),
        "end_date": str(analysis.index.max().date()),
        "n_months": int(analysis.shape[0]),
        "steps": [
            "Merged UBOS CIPI panel with MoFPED bulk macro-fiscal datasets.",
            "Constructed monthly inflation rates for materials and sector indices.",
            "Estimated HAC-robust dynamic regressions with lagged macro-fiscal drivers.",
            "Ran expanding-window one-step-ahead backtests against AR(1) benchmark.",
            "Exported coefficients, metrics, forecast paths, and reproducibility summary.",
        ],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    plot_forecasts(pred_df, paper_dir / "figures/forecast_vs_actual.png")
    write_report(paper_dir, summary, met_df.round(4), sig.round(4))

    print("Paper 1 analysis complete.")
    print("Outputs written to:", out_dir)


if __name__ == "__main__":
    main()
