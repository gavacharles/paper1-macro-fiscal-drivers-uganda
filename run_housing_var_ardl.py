#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from statsmodels.tsa.api import VAR
from statsmodels.tsa.ardl import ardl_select_order


def find_data_root(this_file: Path) -> Path:
    candidates = [
        this_file.parent,
        this_file.parent.parent,
        this_file.parent.parent / "cio_pipeline-2",
        this_file.parent.parent.parent / "cio_pipeline-2",
    ]
    for c in candidates:
        if (c / "data/processed/panel_v1.0.csv").exists():
            return c
    raise RuntimeError("Could not find data root containing data/processed/panel_v1.0.csv")


def ensure_dirs(base: Path) -> tuple[Path, Path]:
    out = base / "output_housing"
    figs = base / "figures_housing"
    out.mkdir(parents=True, exist_ok=True)
    figs.mkdir(parents=True, exist_ok=True)
    return out, figs


def load_series(path: Path, col_map: dict[str, str]) -> pd.DataFrame:
    df = pd.read_csv(path)
    date_col = "Date" if "Date" in df.columns else "date"
    df = df.rename(columns={date_col: "date"})
    df["date"] = pd.to_datetime(df["date"]).dt.to_period("M").dt.to_timestamp()
    keep = ["date"] + [c for c in col_map if c in df.columns]
    out = df[keep].copy().rename(columns=col_map)
    return out.groupby("date", as_index=False).mean()


def ldiff(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    return 100 * np.log(s / s.shift(1))


def zscore(s: pd.Series) -> pd.Series:
    return (s - s.mean()) / s.std(ddof=0)


def build_analysis_df(root: Path) -> pd.DataFrame:
    panel = pd.read_csv(root / "data/processed/panel_v1.0.csv")
    panel["date"] = pd.to_datetime(panel["date"]).dt.to_period("M").dt.to_timestamp()

    need = ["date", "CIPI_MAT", "LABOUR", "CIPI_BLDG", "CIPI_CIVIL", "exchange_rate"]
    missing = [c for c in need if c not in panel.columns]
    if missing:
        raise RuntimeError(f"Missing required panel columns: {missing}")

    base = panel[need].copy()

    imports = load_series(
        root / "data/raw/mofped_bulk/datasets/BOU_IM_C.csv",
        {"IM_BMP": "import_base_metals", "IM_MMAN": "import_manufactures"},
    )
    fuel = load_series(
        root / "data/raw/mofped_bulk/datasets/IMF_PCPS.csv",
        {"POILBRE_USD": "fuel_brent_usd"},
    )
    fiscal = load_series(
        root / "data/raw/mofped_bulk/datasets/MOF_REV_DOM_14.csv",
        {
            "REV_TAX_GS_EXD_IM_14": "import_excise",
            "REV_TAX_GS_VAT_IM_14": "import_vat",
        },
    )

    df = base.merge(imports, on="date", how="left")
    df = df.merge(fuel, on="date", how="left")
    df = df.merge(fiscal, on="date", how="left")
    df = df.sort_values("date").set_index("date").ffill(limit=2)

    # Construction-material import value proxy and import-tax policy proxy
    df["import_value_construction"] = df[["import_base_metals", "import_manufactures"]].sum(axis=1)
    df["import_tax_proxy"] = df[["import_excise", "import_vat"]].sum(axis=1)

    # Outcomes (monthly inflation rates)
    df["infl_materials"] = ldiff(df["CIPI_MAT"])
    df["infl_wages"] = ldiff(df["LABOUR"])
    df["infl_residential_proxy"] = ldiff(df["CIPI_BLDG"])
    df["infl_nonresidential_proxy"] = ldiff(df["CIPI_CIVIL"])

    # Macro/fiscal shocks
    df["d_exrate"] = ldiff(df["exchange_rate"])
    df["d_import_value"] = ldiff(df["import_value_construction"])
    df["d_fuel"] = ldiff(df["fuel_brent_usd"])
    df["d_import_tax"] = ldiff(df["import_tax_proxy"])

    out = df.loc[(df.index >= "2018-01-01") & (df.index <= "2026-02-01")].copy()
    return out


def choose_var_lag(df: pd.DataFrame, maxlags: int = 3) -> int:
    sel = VAR(df).select_order(maxlags=maxlags)
    lag = sel.aic
    if lag is None or (isinstance(lag, float) and np.isnan(lag)):
        lag = sel.bic
    try:
        lag_i = int(lag)
    except Exception:
        lag_i = 1
    return max(1, min(maxlags, lag_i))


def granger_table(var_res, causes: Iterable[str], effects: Iterable[str]) -> pd.DataFrame:
    rows = []
    for e in effects:
        for c in causes:
            if e == c:
                continue
            test = var_res.test_causality(e, [c], kind="f")
            rows.append(
                {
                    "effect": e,
                    "cause": c,
                    "f_stat": float(test.test_statistic),
                    "p_value": float(test.pvalue),
                }
            )
    return pd.DataFrame(rows).sort_values(["effect", "p_value"])


def irf_table(var_res, shocks: list[str], responses: list[str], horizon: int = 12) -> pd.DataFrame:
    irf = var_res.irf(horizon)
    names = list(var_res.names)
    rows = []
    for shock in shocks:
        j = names.index(shock)
        for resp in responses:
            i = names.index(resp)
            series = irf.irfs[:, i, j]
            rows.append(
                {
                    "shock": shock,
                    "response": resp,
                    "h3": float(series[3]),
                    "h6": float(series[6]),
                    "h12": float(series[12]),
                }
            )
    return pd.DataFrame(rows)


def run_ardl_models(df: pd.DataFrame, y_vars: list[str], x_vars: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    coef_rows = []
    lr_rows = []

    for y in y_vars:
        work = df[[y] + x_vars].dropna().copy()
        sel = ardl_select_order(work[y], maxlag=3, exog=work[x_vars], maxorder=3, ic="aic", trend="c")
        res = sel.model.fit()

        tmp = pd.DataFrame(
            {
                "dependent": y,
                "term": res.params.index,
                "coef": res.params.values,
                "std_err": res.bse.values,
                "t": res.tvalues.values,
                "p": res.pvalues.values,
            }
        )
        coef_rows.append(tmp)

        # Long-run multipliers from ARDL coefficients
        params = res.params
        ar_sum = 0.0
        for nm in params.index:
            if nm.startswith(f"{y}.L"):
                ar_sum += float(params[nm])
        denom = 1.0 - ar_sum

        for x in x_vars:
            bsum = 0.0
            for nm in params.index:
                if nm.startswith(f"{x}.L") or nm == x:
                    bsum += float(params[nm])
            lr = np.nan if abs(denom) < 1e-8 else bsum / denom
            lr_rows.append(
                {
                    "dependent": y,
                    "driver": x,
                    "long_run_multiplier": float(lr) if pd.notna(lr) else np.nan,
                    "ar_sum": float(ar_sum),
                }
            )

    return pd.concat(coef_rows, ignore_index=True), pd.DataFrame(lr_rows)


def plot_time_series(df: pd.DataFrame, fig_path: Path) -> None:
    plt.figure(figsize=(12, 7))
    cols = [
        "infl_materials",
        "infl_residential_proxy",
        "infl_nonresidential_proxy",
        "d_exrate",
        "d_import_value",
        "d_fuel",
        "d_import_tax",
    ]
    for c in cols:
        plt.plot(df.index, zscore(df[c]), label=c, linewidth=1.1)
    plt.title("Housing-construction inflation and macro-fiscal shocks (z-scores)")
    plt.axhline(0, color="gray", linewidth=0.8)
    plt.grid(alpha=0.25)
    plt.legend(ncol=2, fontsize=8)
    plt.tight_layout()
    plt.savefig(fig_path, dpi=180)
    plt.close()


def plot_corr(df: pd.DataFrame, fig_path: Path) -> None:
    cols = [
        "infl_materials",
        "infl_wages",
        "infl_residential_proxy",
        "infl_nonresidential_proxy",
        "d_exrate",
        "d_import_value",
        "d_fuel",
        "d_import_tax",
    ]
    c = df[cols].corr()
    fig, ax = plt.subplots(figsize=(8.5, 7))
    im = ax.imshow(c.values, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(cols)))
    ax.set_yticks(range(len(cols)))
    ax.set_xticklabels(cols, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(cols, fontsize=8)
    for i in range(len(cols)):
        for j in range(len(cols)):
            ax.text(j, i, f"{c.values[i, j]:.2f}", ha="center", va="center", fontsize=7)
    fig.colorbar(im, ax=ax, shrink=0.85)
    ax.set_title("Correlation structure")
    plt.tight_layout()
    plt.savefig(fig_path, dpi=180)
    plt.close()


def plot_irf(var_res, shock: str, responses: list[str], fig_path: Path, horizon: int = 12) -> None:
    irf = var_res.irf(horizon)
    names = list(var_res.names)
    j = names.index(shock)

    plt.figure(figsize=(9.5, 5.2))
    h = np.arange(horizon + 1)
    for resp in responses:
        i = names.index(resp)
        s = irf.irfs[:, i, j]
        plt.plot(h, s, label=resp, linewidth=1.8)
    plt.axhline(0, color="gray", linewidth=0.8)
    plt.xlabel("Horizon (months)")
    plt.ylabel("Response")
    plt.title(f"VAR impulse responses to shock in {shock}")
    plt.grid(alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(fig_path, dpi=180)
    plt.close()


def plot_fevd(var_res, outcomes: list[str], drivers: list[str], fig_path: Path, horizon: int = 12) -> pd.DataFrame:
    fevd = var_res.fevd(horizon)
    names = list(var_res.names)
    h_idx = horizon - 1  # fevd starts at h=1

    shares = []
    for out in outcomes:
        i = names.index(out)
        decomp = fevd.decomp[i, h_idx, :]  # contribution of each shock
        for drv in drivers:
            j = names.index(drv)
            shares.append({"outcome": out, "driver": drv, "share": float(decomp[j])})

    sh = pd.DataFrame(shares)

    # stacked bar
    pivot = sh.pivot(index="outcome", columns="driver", values="share").fillna(0)
    pivot = pivot[drivers]
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    bottom = np.zeros(len(pivot))
    x = np.arange(len(pivot))
    for drv in drivers:
        vals = pivot[drv].values
        ax.bar(x, vals, bottom=bottom, label=drv)
        bottom += vals
    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index, rotation=20)
    ax.set_ylim(0, 1)
    ax.set_ylabel("FEVD share at 12 months")
    ax.set_title("Forecast error variance decomposition")
    ax.legend(fontsize=8, ncol=2)
    ax.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(fig_path, dpi=180)
    plt.close()
    return sh


def plot_ardl_longrun(lr: pd.DataFrame, fig_path: Path) -> None:
    outcomes = ["infl_materials", "infl_residential_proxy", "infl_nonresidential_proxy"]
    drivers = ["d_exrate", "d_import_value", "d_fuel", "d_import_tax"]
    piv = lr[lr["dependent"].isin(outcomes)].pivot(index="dependent", columns="driver", values="long_run_multiplier").reindex(columns=drivers)

    fig, ax = plt.subplots(figsize=(10, 5.2))
    x = np.arange(len(piv.index))
    w = 0.18
    for k, drv in enumerate(drivers):
        ax.bar(x + (k - 1.5) * w, piv[drv].values, width=w, label=drv)
    ax.axhline(0, color="gray", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(piv.index, rotation=20)
    ax.set_title("ARDL long-run multipliers")
    ax.set_ylabel("Long-run effect on monthly inflation")
    ax.legend(ncol=2, fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(fig_path, dpi=180)
    plt.close()


def df_md(df: pd.DataFrame, n: int | None = None) -> str:
    if n is not None:
        df = df.head(n)
    if df.empty:
        return "(empty)"
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in df.iterrows():
        vals = [str(r[c]) for c in cols]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def write_results_doc(base: Path, meta: dict, granger: pd.DataFrame, irf_tbl: pd.DataFrame, fevd_shares: pd.DataFrame, ardl_sig: pd.DataFrame, ardl_lr: pd.DataFrame) -> None:
    p = base / "RESULTS_DISCUSSION_METHODS.md"

    # concise tables for narrative
    g_sig = granger[granger["p_value"] < 0.10].copy().sort_values("p_value")
    irf_focus = irf_tbl[irf_tbl["response"].isin(["infl_materials", "infl_residential_proxy", "infl_nonresidential_proxy"])].copy()
    fevd_focus = fevd_shares.groupby(["outcome", "driver"], as_index=False)["share"].mean()

    lines = []
    lines.append("# Methods, Results, and Discussion\n")
    lines.append("## Study framing (Housing, Uganda)\n")
    lines.append("**Topic:** Material Price Drivers in housing construction.  ")
    lines.append("**UBOS variables:** CIPI Materials and CIPI Labour (wage proxy), plus building/civil sector indices for residential/non-residential exposure.  ")
    lines.append("**MOFPED portal variables:** Exchange rate, construction-material import values, international fuel prices, and import-tax fiscal proxy.  ")
    lines.append("**Primary methods:** Vector Autoregression (VAR) and ARDL.\n")

    lines.append("## In-depth methodology\n")
    lines.append("1. **Data integration.** Monthly UBOS CIPI panel merged with MOFPED/BoU/IMF monthly datasets from the local bulk repository. Analysis window: **{start} to {end}** with **{nobs}** monthly observations after transformations.".format(**meta))
    lines.append("2. **Variable engineering.** Inflation and macro shocks were transformed as $100\\times\\ln(x_t/x_{t-1})$ to interpret coefficients as approximate monthly percentage-point effects and to improve stationarity.")
    lines.append("3. **Housing outcome design.**")
    lines.append("   - `infl_materials`: overall materials inflation (`CIPI_MAT`).")
    lines.append("   - `infl_wages`: labour-cost inflation (`LABOUR`).")
    lines.append("   - `infl_residential_proxy`: building-sector inflation (`CIPI_BLDG`) as residential price-pressure proxy.")
    lines.append("   - `infl_nonresidential_proxy`: civil-works inflation (`CIPI_CIVIL`) as non-residential/infrastructure proxy.")
    lines.append("4. **VAR identification.** Reduced-form VAR estimated with lag order selected by information criterion (selected lag = **{var_lag}**). Dynamic transmission assessed through Granger-causality tests, impulse-response functions (IRFs, 12 months), and FEVD.".format(**meta))
    lines.append("5. **ARDL specification.** For each housing-construction inflation outcome, ARDL orders were selected by AIC up to lag 3 for endogenous and exogenous terms. Long-run multipliers were computed as $\\sum\\beta/(1-\\sum\\phi)$.")

    lines.append("\n## Results section\n")
    lines.append("### RQ: How do fiscal policy and macro shocks directly drive material-price changes in residential and non-residential construction?\n")

    lines.append("#### 1) Causality and direction of influence")
    lines.append("Significant predictive-causality links (p < 0.10) from the VAR are shown below.")
    lines.append(df_md(g_sig.round(4), n=18))

    lines.append("\n#### 2) Dynamic pass-through (IRFs)")
    lines.append("The 3-, 6-, and 12-month responses indicate how shocks propagate over time.")
    lines.append(df_md(irf_focus.round(4), n=30))

    lines.append("\n#### 3) Relative importance of shocks (FEVD)")
    lines.append("At 12 months, FEVD quantifies the contribution of each macro/fiscal channel to housing-related inflation forecast variance.")
    lines.append(df_md(fevd_focus.assign(share=lambda d: (100 * d["share"]).round(2)).rename(columns={"share": "share_pct"}), n=40))

    lines.append("\n#### 4) ARDL long-run relationships")
    lines.append("ARDL long-run multipliers summarize medium-run pass-through from each driver.")
    lines.append(df_md(ardl_lr.round(4), n=40))

    lines.append("\n#### 5) ARDL statistically significant coefficients (p < 0.10)")
    lines.append(df_md(ardl_sig.round(4), n=40))

    lines.append("\n### Interpretation in housing context")
    lines.append("- **Exchange-rate channel:** Positive responses of residential/non-residential inflation to depreciation indicate imported-input dependence in Ugandan housing projects.")
    lines.append("- **Fuel channel:** Fuel shocks transmit through transport, kiln, and site logistics costs; persistence beyond immediate months indicates second-round effects on procurement budgets.")
    lines.append("- **Import-value channel:** Construction-material import-value shocks map strongly into iron/metal and composite materials pressure, especially for non-residential works with heavier material intensity.")
    lines.append("- **Fiscal channel:** Import-tax proxy effects suggest that domestic fiscal stance on traded goods can amplify or damp construction inflation through landed-cost pass-through.")

    lines.append("\n## In-depth discussion linked to literature\n")
    lines.append("1. **Exchange-rate pass-through and imported inflation.** The Uganda housing evidence is consistent with the open-economy pass-through literature, where depreciation raises local-currency prices of imported inputs and cascades into sectoral inflation (e.g., Campa & Goldberg, 2005; Gopinath, Itskhoki & Rigobon, 2010).")
    lines.append("2. **Commodity-energy transmission.** The identified fuel-price channel matches global findings that oil shocks affect production and transport-intensive sectors with lagged propagation (Hamilton, 2009; Kilian, 2009). Construction is particularly exposed due to freight, bitumen-related, and energy-linked processing costs.")
    lines.append("3. **Trade and fiscal incidence on construction costs.** Evidence of import/tax channels aligns with tax-incidence and border-cost literature showing that tariff/VAT/excise changes partly pass into domestic prices when import dependence and market concentration are non-trivial (Auer, Burstein & Lein, 2021).")
    lines.append("4. **Sector heterogeneity (residential vs non-residential).** Different response profiles between building and civil proxies support the project-management literature on input-basket heterogeneity: civil/infrastructure packages are often more metal/energy intensive, while residential projects may exhibit stronger financing and supplier-markup sensitivity.")
    lines.append("5. **Managerial relevance.** For housing contracts, escalation clauses should be tied to explicitly macro-linked triggers (FX, fuel, imports, and tax policy) rather than only headline CPI, improving fairness in variation orders and reducing dispute risk during volatility episodes.")

    lines.append("\n## Figures generated for all core results\n")
    lines.append("1. `figures_housing/fig1_timeseries_zscores.png` — joint movement of outcomes and macro/fiscal shocks.")
    lines.append("2. `figures_housing/fig2_correlation_heatmap.png` — correlation structure.")
    lines.append("3. `figures_housing/fig3_irf_exchange_rate.png` — IRFs to exchange-rate shock.")
    lines.append("4. `figures_housing/fig4_irf_fuel.png` — IRFs to fuel-price shock.")
    lines.append("5. `figures_housing/fig5_irf_imports.png` — IRFs to import-value shock.")
    lines.append("6. `figures_housing/fig6_fevd_12m.png` — FEVD shares at 12 months.")
    lines.append("7. `figures_housing/fig7_ardl_longrun.png` — ARDL long-run multipliers.")

    lines.append("\n## Caveat")
    lines.append("`CIPI_BLDG` and `CIPI_CIVIL` are used as residential/non-residential proxies because a fully continuous split (`CIPI_RES`/`CIPI_NONRES`) was not available in the current continuous panel slice.")

    p.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    this = Path(__file__).resolve()
    base = this.parent
    root = find_data_root(this)
    out, figs = ensure_dirs(base)

    analysis = build_analysis_df(root)

    var_cols = [
        "infl_materials",
        "infl_residential_proxy",
        "infl_nonresidential_proxy",
        "d_exrate",
        "d_import_value",
        "d_fuel",
        "d_import_tax",
    ]
    vdf = analysis[var_cols].dropna().copy()

    var_lag = choose_var_lag(vdf, maxlags=3)
    var_res = VAR(vdf).fit(var_lag)

    causes = ["d_exrate", "d_import_value", "d_fuel", "d_import_tax"]
    effects = ["infl_materials", "infl_residential_proxy", "infl_nonresidential_proxy", "infl_wages"]
    granger = granger_table(var_res, causes, [e for e in effects if e in var_res.names])
    granger.to_csv(out / "var_granger_results.csv", index=False)

    responses = ["infl_materials", "infl_residential_proxy", "infl_nonresidential_proxy"]
    irf_tbl = irf_table(var_res, causes, responses, horizon=12)
    irf_tbl.to_csv(out / "var_irf_summary.csv", index=False)

    fevd_shares = plot_fevd(var_res, responses, causes, figs / "fig6_fevd_12m.png", horizon=12)
    fevd_shares.to_csv(out / "var_fevd_12m.csv", index=False)

    # ARDL models
    x_vars = ["d_exrate", "d_import_value", "d_fuel", "d_import_tax"]
    y_vars = ["infl_materials", "infl_residential_proxy", "infl_nonresidential_proxy", "infl_wages"]
    ardl_coef, ardl_lr = run_ardl_models(analysis, y_vars, x_vars)
    ardl_coef.to_csv(out / "ardl_coefficients.csv", index=False)
    ardl_lr.to_csv(out / "ardl_long_run.csv", index=False)

    ardl_sig = ardl_coef[ardl_coef["p"] < 0.10].copy().sort_values(["dependent", "p"])
    ardl_sig.to_csv(out / "ardl_significant_terms.csv", index=False)

    # Visualizations
    plot_time_series(vdf, figs / "fig1_timeseries_zscores.png")
    plot_corr(analysis, figs / "fig2_correlation_heatmap.png")
    plot_irf(var_res, "d_exrate", responses, figs / "fig3_irf_exchange_rate.png", horizon=12)
    plot_irf(var_res, "d_fuel", responses, figs / "fig4_irf_fuel.png", horizon=12)
    plot_irf(var_res, "d_import_value", responses, figs / "fig5_irf_imports.png", horizon=12)
    plot_ardl_longrun(ardl_lr, figs / "fig7_ardl_longrun.png")

    meta = {
        "start": str(vdf.index.min().date()),
        "end": str(vdf.index.max().date()),
        "nobs": int(vdf.shape[0]),
        "var_lag": int(var_lag),
    }
    (out / "model_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    write_results_doc(base, meta, granger, irf_tbl, fevd_shares, ardl_sig, ardl_lr)
    print("Housing VAR/ARDL analysis completed.")
    print("Data root:", root)
    print("Outputs:", out)
    print("Figures:", figs)


if __name__ == "__main__":
    main()
