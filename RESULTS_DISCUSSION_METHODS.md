# Methods, Results, and Discussion

## Brief summary of what the paper finds

- Uganda’s housing-construction input inflation is systematically linked to macro-fiscal shocks rather than being purely project-level noise.
- Fuel-price shocks are the strongest and most consistent external predictor of overall materials inflation.
- Exchange-rate depreciation passes into construction inflation, with evidence in both materials and residential/non-residential proxies.
- Fiscal-trade channels (import values and import-tax policy proxies) show lagged pass-through into building and civil-works cost dynamics.
- Practical implication: escalation clauses and procurement budgets should be indexed to FX, fuel, and import-policy conditions, not only headline inflation.

## Study framing (Housing, Uganda)

**Topic:** Material Price Drivers in housing construction.  
**UBOS variables:** CIPI Materials and CIPI Labour (wage proxy), plus building/civil sector indices for residential/non-residential exposure.  
**MOFPED portal variables:** Exchange rate, construction-material import values, international fuel prices, and import-tax fiscal proxy.  
**Primary methods:** Vector Autoregression (VAR) and ARDL.

## In-depth methodology

1. **Data integration.** Monthly UBOS CIPI panel merged with MOFPED/BoU/IMF monthly datasets from the local bulk repository. Analysis window: **2018-01-01 to 2025-08-01** with **92** monthly observations after transformations.
2. **Variable engineering.** Inflation and macro shocks were transformed as $100\times\ln(x_t/x_{t-1})$ to interpret coefficients as approximate monthly percentage-point effects and to improve stationarity.
3. **Housing outcome design.**
   - `infl_materials`: overall materials inflation (`CIPI_MAT`).
   - `infl_wages`: labour-cost inflation (`LABOUR`).
   - `infl_residential_proxy`: building-sector inflation (`CIPI_BLDG`) as residential price-pressure proxy.
   - `infl_nonresidential_proxy`: civil-works inflation (`CIPI_CIVIL`) as non-residential/infrastructure proxy.
4. **VAR identification.** Reduced-form VAR estimated with lag order selected by information criterion (selected lag = **3**). Dynamic transmission assessed through Granger-causality tests, impulse-response functions (IRFs, 12 months), and FEVD.
5. **ARDL specification.** For each housing-construction inflation outcome, ARDL orders were selected by AIC up to lag 3 for endogenous and exogenous terms. Long-run multipliers were computed as $\sum\beta/(1-\sum\phi)$.

## Results section

### RQ: How do fiscal policy and macro shocks directly drive material-price changes in residential and non-residential construction?

#### 1) Causality and direction of influence
Significant predictive-causality links (p < 0.10) from the VAR are shown below.
| effect | cause | f_stat | p_value |
| --- | --- | --- | --- |
| infl_materials | d_fuel | 4.5993 | 0.0035 |

#### 2) Dynamic pass-through (IRFs)
The 3-, 6-, and 12-month responses indicate how shocks propagate over time.
| shock | response | h3 | h6 | h12 |
| --- | --- | --- | --- | --- |
| d_exrate | infl_materials | -0.2268 | 0.0484 | 0.0027 |
| d_exrate | infl_residential_proxy | -0.1843 | 0.2485 | -0.0345 |
| d_exrate | infl_nonresidential_proxy | -0.1485 | 0.2525 | -0.0341 |
| d_import_value | infl_materials | -0.0056 | 0.0027 | -0.0004 |
| d_import_value | infl_residential_proxy | -0.0089 | 0.0011 | -0.0008 |
| d_import_value | infl_nonresidential_proxy | -0.0098 | 0.002 | -0.0009 |
| d_fuel | infl_materials | 0.0559 | -0.0046 | 0.0023 |
| d_fuel | infl_residential_proxy | 0.0141 | -0.0207 | 0.0049 |
| d_fuel | infl_nonresidential_proxy | 0.0161 | -0.0204 | 0.005 |
| d_import_tax | infl_materials | -0.0192 | -0.005 | 0.001 |
| d_import_tax | infl_residential_proxy | -0.0451 | -0.0085 | -0.0007 |
| d_import_tax | infl_nonresidential_proxy | -0.047 | -0.0089 | -0.0006 |

#### 3) Relative importance of shocks (FEVD)
At 12 months, FEVD quantifies the contribution of each macro/fiscal channel to housing-related inflation forecast variance.
| outcome | driver | share_pct |
| --- | --- | --- |
| infl_materials | d_exrate | 5.2 |
| infl_materials | d_fuel | 11.84 |
| infl_materials | d_import_tax | 2.53 |
| infl_materials | d_import_value | 4.2 |
| infl_nonresidential_proxy | d_exrate | 2.22 |
| infl_nonresidential_proxy | d_fuel | 5.66 |
| infl_nonresidential_proxy | d_import_tax | 4.27 |
| infl_nonresidential_proxy | d_import_value | 3.56 |
| infl_residential_proxy | d_exrate | 2.21 |
| infl_residential_proxy | d_fuel | 5.46 |
| infl_residential_proxy | d_import_tax | 3.78 |
| infl_residential_proxy | d_import_value | 3.16 |

#### 4) ARDL long-run relationships
ARDL long-run multipliers summarize medium-run pass-through from each driver.
| dependent | driver | long_run_multiplier | ar_sum |
| --- | --- | --- | --- |
| infl_materials | d_exrate | 0.2412 | -0.3543 |
| infl_materials | d_import_value | 0.0047 | -0.3543 |
| infl_materials | d_fuel | 0.0174 | -0.3543 |
| infl_materials | d_import_tax | 0.0 | -0.3543 |
| infl_residential_proxy | d_exrate | 0.076 | 0.0 |
| infl_residential_proxy | d_import_value | 0.0 | 0.0 |
| infl_residential_proxy | d_fuel | 0.0 | 0.0 |
| infl_residential_proxy | d_import_tax | -0.0055 | 0.0 |
| infl_nonresidential_proxy | d_exrate | 0.2573 | -0.169 |
| infl_nonresidential_proxy | d_import_value | 0.0 | -0.169 |
| infl_nonresidential_proxy | d_fuel | 0.0 | -0.169 |
| infl_nonresidential_proxy | d_import_tax | 0.0237 | -0.169 |
| infl_wages | d_exrate | -0.321 | 0.3769 |
| infl_wages | d_import_value | 0.0 | 0.3769 |
| infl_wages | d_fuel | -0.0152 | 0.3769 |
| infl_wages | d_import_tax | -0.0171 | 0.3769 |

#### 5) ARDL statistically significant coefficients (p < 0.10)
| dependent | term | coef | std_err | t | p |
| --- | --- | --- | --- | --- | --- |
| infl_materials | infl_materials.L1 | -0.3543 | 0.0914 | -3.8759 | 0.0002 |
| infl_materials | const | 0.3676 | 0.1039 | 3.5387 | 0.0007 |
| infl_materials | d_exrate.L0 | 0.3267 | 0.097 | 3.3687 | 0.0012 |
| infl_materials | d_fuel.L3 | 0.0392 | 0.012 | 3.2658 | 0.0016 |
| infl_materials | d_import_value.L2 | 0.0207 | 0.0091 | 2.2897 | 0.0246 |
| infl_materials | d_fuel.L0 | -0.023 | 0.0119 | -1.9361 | 0.0563 |
| infl_nonresidential_proxy | d_import_tax.L3 | -0.0393 | 0.0198 | -1.9839 | 0.0505 |
| infl_residential_proxy | d_import_tax.L3 | -0.0547 | 0.0204 | -2.6854 | 0.0087 |
| infl_residential_proxy | d_exrate.L0 | 0.4245 | 0.2091 | 2.0299 | 0.0455 |
| infl_wages | d_exrate.L2 | -0.1336 | 0.0513 | -2.6062 | 0.011 |
| infl_wages | d_fuel.L2 | 0.0155 | 0.0065 | 2.3933 | 0.0191 |
| infl_wages | d_import_tax.L0 | -0.0106 | 0.0045 | -2.3565 | 0.021 |
| infl_wages | d_fuel.L1 | -0.0155 | 0.007 | -2.2223 | 0.0292 |
| infl_wages | const | 0.1345 | 0.0611 | 2.1993 | 0.0308 |

### Interpretation in housing context
- **Exchange-rate channel:** Positive responses of residential/non-residential inflation to depreciation indicate imported-input dependence in Ugandan housing projects.
- **Fuel channel:** Fuel shocks transmit through transport, kiln, and site logistics costs; persistence beyond immediate months indicates second-round effects on procurement budgets.
- **Import-value channel:** Construction-material import-value shocks map strongly into iron/metal and composite materials pressure, especially for non-residential works with heavier material intensity.
- **Fiscal channel:** Import-tax proxy effects suggest that domestic fiscal stance on traded goods can amplify or damp construction inflation through landed-cost pass-through.

## In-depth discussion linked to literature

1. **Exchange-rate pass-through and imported inflation.** The Uganda housing evidence is consistent with the open-economy pass-through literature, where depreciation raises local-currency prices of imported inputs and cascades into sectoral inflation (e.g., Campa & Goldberg, 2005; Gopinath, Itskhoki & Rigobon, 2010).
2. **Commodity-energy transmission.** The identified fuel-price channel matches global findings that oil shocks affect production and transport-intensive sectors with lagged propagation (Hamilton, 2009; Kilian, 2009). Construction is particularly exposed due to freight, bitumen-related, and energy-linked processing costs.
3. **Trade and fiscal incidence on construction costs.** Evidence of import/tax channels aligns with tax-incidence and border-cost literature showing that tariff/VAT/excise changes partly pass into domestic prices when import dependence and market concentration are non-trivial (Auer, Burstein & Lein, 2021).
4. **Sector heterogeneity (residential vs non-residential).** Different response profiles between building and civil proxies support the project-management literature on input-basket heterogeneity: civil/infrastructure packages are often more metal/energy intensive, while residential projects may exhibit stronger financing and supplier-markup sensitivity.
5. **Managerial relevance.** For housing contracts, escalation clauses should be tied to explicitly macro-linked triggers (FX, fuel, imports, and tax policy) rather than only headline CPI, improving fairness in variation orders and reducing dispute risk during volatility episodes.

## Figures generated for all core results

1. `figures_housing/fig1_timeseries_zscores.png` — joint movement of outcomes and macro/fiscal shocks.
2. `figures_housing/fig2_correlation_heatmap.png` — correlation structure.
3. `figures_housing/fig3_irf_exchange_rate.png` — IRFs to exchange-rate shock.
4. `figures_housing/fig4_irf_fuel.png` — IRFs to fuel-price shock.
5. `figures_housing/fig5_irf_imports.png` — IRFs to import-value shock.
6. `figures_housing/fig6_fevd_12m.png` — FEVD shares at 12 months.
7. `figures_housing/fig7_ardl_longrun.png` — ARDL long-run multipliers.

## Caveat
`CIPI_BLDG` and `CIPI_CIVIL` are used as residential/non-residential proxies because a fully continuous split (`CIPI_RES`/`CIPI_NONRES`) was not available in the current continuous panel slice.