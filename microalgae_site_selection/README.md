# Microalgae Site Selection – Corbion AlgaPrime DHA

Multi-criteria model that scores candidate countries for a new heterotrophic-fermentation
microalgae DHA plant and renders slide-ready visuals in the AgroInsper / Aqua Capital deck style.

## Run

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python microalgae_site_selection.py                    # site-selection model -> ./outputs
python brazil_thailand_economics.py                    # cost & return, Brazil vs Thailand
python -m pytest -q                                    # validation and scoring checks
```

Options: `--data <csv>`, `--output-dir <dir>`, `--no-charts`, `--plotly-static`,
`--distance-mode export_only|include_domestic`, `--ratings <csv>`, `--mc-sims <n>`, `--compare <v1 csv>`
(also tries a Plotly/Kaleido PNG; this needs Chrome and internet, so the Matplotlib PNGs remain the
deliverables).

## Files

| File | Content |
|---|---|
| `raw_country_data.csv` | **Input.** One row per country × metric with value, unit, year, source, URL, access date, type and confidence |
| `microalgae_site_selection.py` | The model (validation → normalisation → sub-criteria → criteria → score → sensitivity → charts) |
| `methodology_and_sources.md` | Method, rubrics, results, limitations, sources (section 0 = v2 changes) |
| `data_change_log.csv` | Every v1 → v2 data correction with reason and source; v1 data in `archive/` |
| `brazil_thailand_economics.py` + `economics_assumptions.csv` | Capex/opex/tax/WACC model and minimum selling price, Brazil vs Thailand |
| `due_diligence_brazil_thailand.md` | Desk findings and field-diligence checklist |
| `rubric_ratings.csv` (optional) | Extra raters for rubric metrics; template in `outputs/rubric_ratings_template.csv` |
| `outputs/country_scores.csv` | Ranking, criterion scores, contributions, viability flag, Data Confidence |
| `outputs/metric_scores.csv` | Every raw value next to its 0–10 score and weight (audit trail) |
| `outputs/subcriterion_scores.csv` | Sub-criterion scores and missing-data coverage |
| `outputs/sensitivity_analysis.csv` | Scores/ranks under the three weighting scenarios |
| `outputs/data_quality_report.csv` | Missing values and other data warnings |
| `outputs/country_data_template.csv` | Rows to fill in to add a new country |
| `outputs/monte_carlo_results.csv`, `monte_carlo_top3.png`, `version_comparison.csv` | Data-uncertainty simulation, v1 vs v2 |
| `outputs/thesis_breakeven.csv`, `thesis_weight_sweep.png` | Weight at which Thailand overtakes Brazil |
| `outputs/distance_mode_comparison.csv`, `rubric_rater_agreement.csv` | Circularity check; inter-rater agreement |
| `outputs/economics_*.csv`, `economics_cost_breakdown.png`, `economics_tornado.png` | Cost & return results, scenarios, tornado, Monte Carlo |
| `outputs/microalgae_bubble_map_clean*.png` | Clean transparent map for pasting on the slide |
| `outputs/microalgae_bubble_map.html` | Interactive map (self-contained, works offline) |
| `outputs/microalgae_bubble_map.png` / `_transparent.png` | Main 3840×2160 visual, with the slide gradient or a transparent background |
| `outputs/country_ranking.png`, `score_contribution.png`, `ranking_sensitivity.png`, `ranking_table.png` | Complementary charts |

## Adding a country

Copy the rows of `outputs/country_data_template.csv` into `raw_country_data.csv`, fill in the
values, sources and confidence levels, and leave unknown values empty with `value_type=missing`.
Rubric metrics accept only 0, 2.5, 5, 7.5 or 10. Goalposts are fixed, so existing countries keep
their scores.
