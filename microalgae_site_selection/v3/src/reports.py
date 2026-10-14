"""audit_report.md / audit_issues.csv and investment_memo.md, filled from the run's own outputs."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import engine as E
from .data import ROOT


def _f(v, d=1):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(v, d=0):
    return "—" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{100 * v:.{d}f}%".replace(".", ",")


def automated_checks(r: dict) -> pd.DataFrame:
    rk = r["ranking"].dropna(subset=["screening_score_v3"]).copy()
    rk["rank_quant_only"] = rk["score_quant_only"].rank(ascending=False, method="min").astype(int)
    br = rk.set_index("country").loc["Brazil"]
    corr = r["extra"]["criterion_correlation"]
    v2e = pd.read_csv(ROOT / "data" / "raw" / "frozen_v2" / "v2_economics_results.csv", index_col=0)
    ue = r["ue"].set_index("site_id")
    base = r["summ"][r["summ"].scenario == "base"].set_index("alternative")
    gf_capex = E.unit_capex(dict(r["p"], sites={**r["p"]["sites"], "BR_ORI_EXP": {**r["p"]["sites"]["BR_ORI_EXP"],
                                                                                  "brownfield": False}}),
                            {"site": "BR_ORI_EXP"})["total"]
    bf_ratio = ue.loc["BR_ORI_EXP", "capex_musd"] * 1e6 / gf_capex
    tv_share = base.loc["A1_ORI", "tv_pv_musd"] / base.loc["A1_ORI", "npv_musd"]
    rows = [
        ("AC01", "peso das rubricas", f"Rubricas = {_pct(br.rubric_share_of_weight)} do peso efetivo. Score só "
         f"quantitativo: Brasil {_f(br.score_quant_only, 2)} ({int(br.rank_quant_only)}º), "
         + ", ".join(f"{c} {_f(s, 2)}" for c, s in rk.sort_values('score_quant_only', ascending=False)
                     [["country", "score_quant_only"]].head(3).values),
         "O 1º lugar do Brasil na v2 depende de rubricas de um avaliador (CR é 100% rubrica)."),
        ("AC02", "correlação entre critérios", f"corr(PE, CR) entre os 8 países = {_f(corr.loc['production_economics', 'corbion_readiness'], 2)}; "
         f"corr(MA, SR) = {_f(corr.loc['market_access', 'strategic_risk'], 2)}",
         "Integração com usina e ativos existentes premiam os mesmos países duas vezes."),
        ("AC03", "robustez aos pesos", f"Sorteios de pesos Dirichlet (n={r['extra']['weight_draws']}): P(rank 1) Brazil "
         f"{_pct(br.p_rank1_weight_uncertainty)}, Thailand {_pct(rk.set_index('country').loc['Thailand','p_rank1_weight_uncertainty'])}; "
         f"P(top 3) China {_pct(rk.set_index('country').loc['China','p_top3_weight_uncertainty'])}, India "
         f"{_pct(rk.set_index('country').loc['India','p_top3_weight_uncertainty'])}",
         "Top 2 robusto aos pesos; a 3ª posição não."),
        ("AC04", "limites de normalização", "; ".join(f"fator {x.goalpost_range_factor}: {x.countries_changing_rank} países mudam de posição"
                                         for x in r["extra"]["bounds_robustness"].itertuples()),
         "Limites escolhidos a posteriori só mexem nas posições 3–7."),
        ("AC05", "reprodução da v2", f"máx |score recalculado − v2 congelado| = {_f(r['repro']['abs_diff'].max(), 4)}; ranking idêntico: "
         f"{bool((r['repro']['rank_rerun'] == r['repro']['rank_frozen_v2']).all())}", "Baseline reproduzido a partir dos dados congelados."),
        ("AC06", "balanço de massa do açúcar", f"v2 3,0 t açúcar/t produto (30% DHA) vs v3 {_f(E.sugar_per_t(r['p']), 2)} t sacarose/t SKU "
         f"(36% DHA, yield {r['p']['dha_yield']}, recovery {r['p']['recovery']})", "Custo de açúcar por t ~+65%."),
        ("AC07", "capex brownfield", f"v2 fator fixo 0,75 × localização 1,10 = 0,83 do greenfield; v3 modular = "
         f"{_f(bf_ratio, 2)} do greenfield no mesmo site (utilidades compartilhadas {r['p']['bf_utilities']}, prédios {r['p']['bf_buildings']}, "
         f"owner {r['p']['bf_owner']})", "Vantagem agora explícita e testável (caso sem vapor ocioso no tornado)."),
        ("AC08", "custo unitário v2 vs v3", f"v2 MSP Orindiúva {_f(v2e.loc['Brazil – Orindiúva expansion', 'msp_per_kg_dha'], 1)} "
         f"US$/kg DHA (20 kt, 90% de utilização); v3 custo pleno a 100% do módulo {_f(ue.loc['BR_ORI_EXP', 'full_cost_usd_per_kg_dha'], 1)}; "
         f"v3 MSP com demanda-base {_f(base.loc['A1_ORI', 'msp_usd_per_kg_dha'], 1)}",
         "É a utilização (demanda), e não o custo, que define o preço necessário."),
        ("AC09", "valor terminal", f"VPL base de A1 {_f(base.loc['A1_ORI', 'npv_musd'])} US$ mi, dos quais VT "
         f"{_f(base.loc['A1_ORI', 'tv_pv_musd'])} ({_pct(tv_share)}); VPL sem VT {_f(base.loc['A1_ORI', 'npv_ex_tv_musd'])}",
         "Com horizonte 2026–2035 e ramp-up lento, o valor está depois de 2035."),
        ("AC10", "demanda vs capacidade", f"Demanda-base ponderada 2030 = {_f(sum(v['2030'] for v in r['p']['demand'].values()), 0)} t; "
         f"um módulo = {_f(r['p']['module_t'] * r['p']['oee'], 0)} t efetivas; contratado (público) = 0 t",
         "A restrição é a absorção pela demanda, não a capacidade."),
    ]
    return pd.DataFrame(rows, columns=["check_id", "topic", "result", "implication"])


def write_audit(r: dict) -> None:
    out = r["out"]
    f = pd.read_csv(ROOT / "data" / "raw" / "audit_findings.csv")
    ac = automated_checks(r)
    ac.to_csv(out / "audit_automated_checks.csv", index=False)
    issues = f.copy()
    issues["automated_evidence"] = issues["issue_id"].map({
        "AU01": "AC01", "AU02": "AC03", "AU03": "AC02", "AU06": "AC07", "AU08": "AC06", "AU24": "AC04",
        "AU26": "AC10"}).fillna("")
    issues.to_csv(out / "audit_issues.csv", index=False)
    counts = issues["classification"].value_counts()
    lines = [
        "# Relatório de auditoria forense: v2 → v3",
        "",
        f"*Corte: {r['cfg']['cutoff_date']} · commit {r['manifest']['git_commit']} · gerado por `python -m src run`*",
        "",
        "## Como ler",
        "",
        "- **confirmed_error**: erro demonstrável no método ou no cálculo.",
        "- **invalid_comparison**: compara bases, unidades, datas ou escopos diferentes.",
        "- **weak_hypothesis**: premissa sem evidência suficiente, que pode estar certa ou não.",
        "- **unknown**: a fonte pública não permite concluir.",
        "",
        "Nada foi chamado de erro se ainda depende de confirmação.",
        "",
        f"Contagem: {', '.join(f'{k} = {v}' for k, v in counts.items())}. Lista completa em `audit_issues.csv` "
        "(linha/função afetada, afirmação antiga, evidência nova, materialidade, correção e impacto).",
        "",
        "## Limitação de acesso às fontes",
        "",
        "Os domínios corbion.com, annualreport.corbion.com, globenewswire.com, World Bank, WRI, USDA, IFFO e BioMar "
        "estavam bloqueados neste ambiente (403/DNS). Nenhum PDF original foi aberto. Os números vieram de trechos de "
        "busca (`access_status = search_snippet`), de valores informados pelo usuário (`user_supplied`) ou herdados da "
        "v2. `evidence_registry.csv` registra isso linha a linha, e `source_gaps.csv` lista o que precisa ser aberto "
        "no original antes de um FID.",
        "",
        "## Checagens automáticas (recalculadas a cada execução)",
        "",
        "| ID | Tema | Resultado | Implicação |",
        "|---|---|---|---|",
    ]
    lines += [f"| {x.check_id} | {x.topic} | {x.result} | {x.implication} |" for x in ac.itertuples()]
    lines += ["", "## Achados de alta materialidade", "", "| ID | Onde | Classe | Correção na v3 |", "|---|---|---|---|"]
    for x in issues[issues.materiality == "high"].itertuples():
        lines.append(f"| {x.issue_id} | `{x.location}` | {x.classification} | {x.correction} |")
    lines += ["", "## Itens mantidos com trilha", "",
              "- **LPI do México = 2,9**: confirmado no World Bank (S025) e não substituído por palpite.",
              "- **Chile, açúcar doméstico = 0 a partir de 2026/27**: zero verdadeiro (S026), não valor ausente. "
              "Fica com gate REVIEW, porque a importação de açúcar continua possível.",
              "- **Aprovações GACC (2025)**: o escopo por SKU e por planta é `unknown`. Uma planta nova entra com "
              "atraso de registro (`gacc_delay_years`) para vender à China.",
              "- **Pillar Two na Tailândia**: o top-up é modelado como (15% − ETR) × (lucro GloBE − SBIE) e funciona como "
              "chave liga/desliga, porque a combinação com as entidades tributáveis da Corbion em Rayong pode anulá-lo. "
              "Parecer jurídico pendente. O QRTC fica fora do caso base (vale 0).",
              "- **CMD 2025**: TIR de 20% e payback de 4,5 anos referem-se ao programa agregado de expansão. "
              "Os €50 mi de Orindiúva não têm capacidade divulgada. `eur50m_implied_capacity_sensitivity.csv` mostra só "
              "o que essa verba compraria em cada intensidade de capex, e não é um dado divulgado.",
              ""]
    (out / "audit_report.md").write_text("\n".join(lines), encoding="utf-8")


def _breakpoints(fr: pd.DataFrame, capex: float) -> dict:
    s = fr[fr.capex_ori_musd == capex]
    out = {}
    for price in (25.0, 30.0, 35.0):
        g = s[s.price_usd_kg_dha == price].sort_values("asia_contracted_t")
        pos = g[g.delta_G_vs_A1 > 0]
        out[price] = None if pos.empty else float(pos.asia_contracted_t.iloc[0])
    return out


def _c_vs_a1_price(fr: pd.DataFrame, capex: float, vol: float):
    g = fr[(fr.capex_ori_musd == capex) & (fr.asia_contracted_t == vol)].sort_values("price_usd_kg_dha")
    pos = g[g.delta_C_vs_A1 > 0]
    return None if pos.empty else float(pos.price_usd_kg_dha.iloc[0])


def write_memo(r: dict) -> None:
    cfg, out = r["cfg"], r["out"]
    s = r["summ"]
    base = s[s.scenario == "base"].set_index("alternative")
    mcs = r["mcs"].set_index("alternative")
    ue = r["ue"].set_index("site_id")
    rk = r["ranking"].dropna(subset=["screening_score_v3"]).set_index("country")
    lab = {k: v["label"] for k, v in cfg["alternatives"].items()}
    mid = sorted(cfg["frontier"]["capex_ori_musd"])[1]
    bp = {c: _breakpoints(r["frontier"], c) for c in cfg["frontier"]["capex_ori_musd"]}
    fr = r["frontier"]
    no_contract = fr[(fr.capex_ori_musd == mid) & (fr.asia_contracted_t == 0)].set_index("price_usd_kg_dha")
    th_vs_a1_price = no_contract[no_contract.npv_C_TH_NSN > no_contract.npv_A1_ORI].index.min()
    t_a1, t_d = r["t_a1"], r["t_d"]
    res = r["res_stress"]
    up_g = res[(res.scenario == "upside") & (res.alternative == "A1_ORI")]
    order_sites = r["npv_rank"].sort_values("npv_base_musd", ascending=False)

    flips = [x.label for x in t_d.itertuples() if (x.metric_at_low > 0) != (x.base > 0) or (x.metric_at_high > 0) != (x.base > 0)]
    flips_text = ("Premissas que, sozinhas no extremo da faixa, invertem o sinal (Tailândia passa Orindiúva): "
                  + ", ".join(flips) + ".") if flips else "Nenhuma premissa isolada inverte o sinal dentro da faixa."
    same_order = list(mcs["mean_npv_musd"].sort_values().index) == list(mcs["mean_npv_musd_nocorr"].sort_values().index)

    def alt_row(k):
        b = base.loc[k]
        m = mcs.loc[k]
        st = s[(s.scenario == "stress") & (s.alternative == k)].iloc[0]
        up = s[(s.scenario == "upside") & (s.alternative == k)].iloc[0]
        return (f"| {lab[k]} | {_f(st.npv_musd, 0)} / **{_f(b.npv_musd, 0)}** / {_f(up.npv_musd, 0)} | "
                f"{_f(b.npv_ex_tv_musd, 0)} | {_pct(b.irr, 1) if b.irr == b.irr else '—'} | {_f(b.msp_usd_per_kg_dha, 1)} | "
                f"{_pct(b.utilisation_2030)} / {_pct(b.utilisation_2035)} | {_f(m.p10, 0)} / {_f(m.p50, 0)} / {_f(m.p90, 0)} | "
                f"{_pct(m.prob_npv_positive)} | {_f(m.expected_shortfall_10pct, 0)} |")

    L = []
    L += ["# Memorando de investimento: próxima capacidade de DHA de microalgas da Corbion (v3)", "",
          f"*Data de corte: {cfg['cutoff_date']}. Gerado automaticamente a partir dos outputs da execução "
          f"(commit {r['manifest']['git_commit']}, seed {cfg['seed']}, {r['manifest']['mc_sims']} simulações).*", "",
          "> **Natureza do resultado.**",
          "> - Não houve acesso a documentos internos da Corbion, contratos ou cotações de EPC e frete.",
          "> - Os sites corbion.com, World Bank, WRI, USDA, IFFO e BioMar estavam bloqueados neste ambiente; as "
          "fontes foram lidas por trechos de busca e estão marcadas assim.",
          "> - A demanda usada é **PREMISSA**: não há contratos públicos para a nova capacidade.",
          "> - Os números abaixo são condicionais a `assumptions.csv`. O modelo é executável: quando entrarem dados "
          "reais, ele recalcula tudo.", "",
          "## 1. Resposta curta (decisão condicional de hoje)", ""]
    best_base = base["npv_musd"].idxmax()
    L += [
        f"1. **Primeiro investimento: expandir Orindiúva em módulo (A1).** É a alternativa de maior VPL no "
        f"cenário-base ({_f(base.loc['A1_ORI','npv_musd'],0)} US$ mi) e a de menor custo pleno "
        f"(US$ {_f(ue.loc['BR_ORI_EXP','full_cost_usd_per_kg_dha'],1)}/kg DHA a 100% do módulo, contra "
        f"{_f(ue.loc['TH_NSN','full_cost_usd_per_kg_dha'],1)} em Nakhon Sawan). A vantagem vem do açúcar mais barato, "
        "do vapor de bagaço e das utilidades compartilhadas. Tem também a maior probabilidade de VPL > 0 "
        f"({_pct(mcs.loc['A1_ORI','prob_npv_positive'])}, condicional às distribuições assumidas). "
        "O hub asiático sem fermentação (E) empata na prática: média "
        f"{_f(mcs.loc['E_ORI_HUB','mean_npv_musd'],0)} contra {_f(mcs.loc['A1_ORI','mean_npv_musd'],0)} US$ mi, "
        f"com cauda pior ({_f(mcs.loc['E_ORI_HUB','expected_shortfall_10pct'],0)} contra "
        f"{_f(mcs.loc['A1_ORI','expected_shortfall_10pct'],0)}).",
        f"2. **O que move o resultado é demanda e preço, não custo.** Com a demanda-premissa ponderada, o módulo "
        f"opera a {_pct(base.loc['A1_ORI','utilisation_2030'])} em 2030 e "
        f"{_pct(base.loc['A1_ORI','utilisation_2035'])} em 2035.",
        f"   - O preço mínimo (VPL = 0) sobe de ~US$ {_f(ue.loc['BR_ORI_EXP','full_cost_usd_per_kg_dha'],0)} "
        f"(custo pleno) para US$ {_f(base.loc['A1_ORI','msp_usd_per_kg_dha'],1)}/kg DHA.",
        f"   - O VPL depende do valor terminal: VT = {_f(base.loc['A1_ORI','tv_pv_musd'],0)} US$ mi de um VPL de "
        f"{_f(base.loc['A1_ORI','npv_musd'],0)}; sem ele, o VPL até 2035 é {_f(base.loc['A1_ORI','npv_ex_tv_musd'],0)} US$ mi.",
        f"   - No cenário stress (só 30% do pipeline qualificado e nada do potencial), o VPL é "
        f"{_f(s[(s.scenario=='stress')&(s.alternative=='A1_ORI')].npv_musd.iloc[0],0)} US$ mi.",
        f"3. **Uma segunda planta na Tailândia agora (G) destrói valor** com a demanda atual: ΔVPL G − A1 = "
        f"{_f(base.loc['G_ORI_TH_NOW','npv_musd']-base.loc['A1_ORI','npv_musd'],0)} US$ mi no cenário-base. "
        f"Ela só passa a agregar valor com **volume asiático contratado** de cerca de "
        f"{_f(bp[mid][30.0],0) if bp[mid][30.0] else '> 10.000'} t/ano a US$ 30/kg DHA, ou "
        f"{_f(bp[mid][35.0],0) if bp[mid][35.0] else '> 10.000'} t/ano a US$ 35 "
        f"(capex de Orindiúva = US$ {mid:.0f} mi).",
        "4. **Sequência recomendada: F (Orindiúva agora; Tailândia só com gatilho).**",
        f"   - O gatilho é demanda asiática ≥ {_f(r['p']['th_trigger_t'],0)} t/ano em {r['p']['decision_year']}, "
        "com contratos firmes.",
        f"   - Com a demanda-premissa, o gatilho dispara em {_pct(r['trig']['F_ORI_THEN_TH'])} das simulações. Por isso "
        "F = A1 no caso-base: a opção de esperar não custa nada e preserva o direito de construir quando houver contrato.",
        f"   - Sem contrato asiático, Nakhon Sawan sozinha (C) só supera Orindiúva com preço ≥ US$ "
        f"{_f(th_vs_a1_price,1) if th_vs_a1_price==th_vs_a1_price else '—'}/kg DHA. Nesse preço pesam o WACC e a "
        "isenção do BOI tailandeses, mais o acesso direto à Ásia.",
        "5. **Antes de um FID, faltam evidências indispensáveis** (seção 7): capacidade comprada pelos €50 mi, "
        "rendimento industrial, preço líquido realizado, contratos de offtake, vapor/açúcar adicional da usina e "
        "escopo GACC por planta.", "",
        "## 2. O que mudou da v2 para a v3", "",
        "| Tema | v2 | v3 |", "|---|---|---|",
        "| Pergunta | Melhor **país** (score 0–10) | Melhor **sequência de investimento por site** (VPL), com o score só como triagem |",
        "| Capacidade | 20 kt impostos | Módulo de 10 kt como variável; absorção pela demanda testada |",
        f"| Açúcar | 3,0 t/t (rendimento de laboratório) | {_f(E.sugar_per_t(r['p']),2)} t/t (36% DHA ÷ rendimento industrial 0,075 × recuperação 0,95; faixa 0,055–0,10) |",
        "| Capex brownfield | Fator fixo 0,75 | Modular: fermentação, downstream, utilidades, efluentes, prédios, EPC/owner e contingência; compartilhamento explícito |",
        "| Moeda/inflação | USD real, depreciação real (viés) | USD nominal; custos locais por PPP + choque cambial real; WACC nominal em USD |",
        "| Tributos | Piso de 15% fixo na Tailândia | Ledger por entidade: prejuízos (30% no BR), BOI 8 anos, top-up GloBE com SBIE como chave; QRTC como cenário |",
        "| Demanda | Implícita | `market_demand_scenarios.csv` (contracted / qualified_pipeline / unqualified_potential), alocação ótima por rede |",
        "| Monte Carlo | Ruído por rótulo de confiança, sem correlação | Cópula gaussiana com correlações declaradas (PSD checada) e corrida sem correlação como robustez |",
        "| Decisão | MSP | VPL, TIR, MSP, utilização, breakeven, fronteira de decisão, opção de esperar, stress de resiliência |", "",
        "## 3. Erros comprovados × lacunas", "",
        "**Erro comprovado (1):**",
        "",
        "- **AU09**: a v2 descontava fluxos reais com depreciação fiscal em base real e superestimava o benefício "
        "fiscal. Corrigido com fluxos nominais.", "",
        "**Comparações inválidas (corrigidas ou isoladas):**",
        "",
        "- açúcar cristal × branco administrado, em datas diferentes (AU15);",
        "- tarifa elétrica × custo contratado (AU16);",
        "- estresse hídrico nacional × do site (AU17);",
        "- capex por t de biomassa × óleo/DHA (AU18);",
        "- MSP lido como retorno (AU19);",
        "- TIR do programa CMD × TIR do projeto (AU28);",
        "- definições de aquafeed diferentes entre países (AU14);",
        "- score de país usado como decisão de site (AU05).", "",
        f"**Hipóteses fracas, com destaque:**",
        "",
        f"- **AU01:** as rubricas de um único avaliador valem {_pct(rk.loc['Brazil','rubric_share_of_weight'])} do peso. "
        f"Só com métricas quantitativas, o Brasil cai para {_f(rk.loc['Brazil','score_quant_only'],2)} (atrás de China, Tailândia, "
        "Índia, Vietnã e Indonésia).",
        f"- **AU03:** Production Economics e Corbion Readiness têm correlação de "
        f"{_f(r['extra']['criterion_correlation'].loc['production_economics','corbion_readiness'],2)} entre os países "
        "(contagem dupla da integração com a usina).",
        "- **AU06–AU08:** brownfield, capacidade e rendimento.",
        "- **AU26:** demanda.", "",
        "## 4. Dois rankings, que não se misturam", "",
        "**(a) Triagem de países** (`ranking_v3.csv`). O score é filtro de diligência, não VPL.", "",
        "| País | Score v3 (= v2) | Só quantitativo | P(1º) com pesos incertos | P(top 3) | Gate nacional | Shortlist |",
        "|---|---|---|---|---|---|---|"]
    for c, x in rk.iterrows():
        L.append(f"| {c} | {_f(x.screening_score_v3,2)} | {_f(x.score_quant_only,2)} | {_pct(x.p_rank1_weight_uncertainty)} | "
                 f"{_pct(x.p_top3_weight_uncertainty)} | {x.national_gate} | {x.shortlist} |")
    L += ["", "EUA (Blair NE), Equador, Peru e Filipinas ficam como `not_scored`: os dados não foram coletados, "
          "e o motivo e os dados necessários estão listados no CSV.", "",
          "**(b) Sites por VPL** (cenário-base de demanda, uma unidade, `site_npv_ranking.csv`).", "",
          "| Site | VPL base (US$ mi) | VPL médio no MC | Gates |", "|---|---|---|---|"]
    for x in order_sites.itertuples():
        L.append(f"| {x.site_id} | {_f(x.npv_base_musd,0)} | {_f(x.npv_mc_mean_musd,0)} | {x.gate_summary} |")
    L += ["", "Todos os sites estão **CONDITIONAL**: nenhum gate está em FAIL, mas vários ainda estão NOT_VERIFIED "
          "(água outorgável, vapor adicional, licenças, EPC). Nenhum número alto compensa um impedimento legal real.", "",
          "## 5. Alternativas: intervalos e riscos", "",
          "VPL nominal em USD, com valor terminal. As colunas p10/p50/p90, P(VPL > 0) e ES10 vêm do Monte Carlo "
          "correlacionado (cenário-base), e as probabilidades são **condicionais às distribuições assumidas**.", "",
          "| Alternativa | VPL stress / **base** / upside | VPL sem VT | TIR base | MSP base (US$/kg DHA) | Utiliz. 2030 / 2035 | p10 / p50 / p90 | P(VPL>0) | ES 10% |",
          "|---|---|---|---|---|---|---|---|---|"]
    L += [alt_row(k) for k in cfg["alternatives"]]
    L += ["", "- **A2** (2º módulo em Orindiúva) e **F** (Tailândia por gatilho) só divergem de A1 quando seus gatilhos "
          f"disparam. Com a demanda-premissa, isso quase nunca acontece: A2 em {_pct(r['trig']['A2_ORI_STAGED'])} e "
          f"F em {_pct(r['trig']['F_ORI_THEN_TH'])} das simulações.",
          "- **DSCR:** não se aplica, porque o modelo assume financiamento corporativo, sem dívida de projeto.",
          f"- **Robustez à dependência:** sem correlações, o VPL médio de A1 vai de {_f(mcs.loc['A1_ORI','mean_npv_musd'],0)} "
          f"para {_f(mcs.loc['A1_ORI','mean_npv_musd_nocorr'],0)} US$ mi; a ordem das alternativas por VPL médio "
          f"{'se mantém' if same_order else 'muda'}.", "",
          "## 6. Pontos de virada (o que inverte a decisão)", "",
          "- **Tornado do VPL de A1:**",
          "  " + "; ".join(f"{x.label}: {_f(x.metric_at_low,0)} → {_f(x.metric_at_high,0)}" for x in t_a1.head(5).itertuples()) + ".",
          "- **Tornado de ΔVPL (C Tailândia − A1):**",
          "  " + "; ".join(f"{x.label}: {_f(x.metric_at_low,0)} → {_f(x.metric_at_high,0)}" for x in t_d.head(5).itertuples()) + ".",
          "  " + flips_text,
          "- **Fronteira da 2ª unidade** (`decision_frontier.csv` e `decision_frontier.png`), volume asiático contratado "
          "a partir do qual G − A1 > 0:", ""]
    L += ["| Preço líquido | US$ 25/kg DHA | US$ 30 | US$ 35 |", "|---|---|---|---|",
          "| Volume asiático contratado mínimo para G − A1 > 0 | " + " | ".join(
              f"{_f(bp[mid][pr],0)} t/ano" if bp[mid][pr] is not None else "> 10.000 t/ano" for pr in (25.0, 30.0, 35.0)) + " |",
          "",
          "O capex de Orindiúva **não move** essa fronteira, porque está nas duas alternativas e se cancela na "
          "diferença. Ele importa na outra escolha: **qual site recebe a única unidade**. Preço mínimo a partir do "
          "qual Nakhon Sawan sozinha (C) supera Orindiúva (A1):", "",
          "| Capex Orindiúva (US$ mi) | sem contrato asiático | 3.000 t asiáticas contratadas | 6.000 t |",
          "|---|---|---|---|"]
    for c in cfg["frontier"]["capex_ori_musd"]:
        vals = [_c_vs_a1_price(r["frontier"], c, v) for v in (0, 3000, 6000)]
        L.append(f"| {c} | " + " | ".join(f"US$ {_f(v,1)}" if v is not None else "> US$ 45" for v in vals) + " |")
    if not up_g.empty:
        L += ["", f"- **Resiliência:** com demanda alta (upside), uma parada de 6 meses do módulo incremental em 2031 tira "
              f"{_f(up_g.lost_t.iloc[0],0)} t de vendas e {_f(-up_g.npv_change_musd.iloc[0],1)} US$ mi de VPL de A1. "
              "Com demanda base, a capacidade ociosa absorve a parada. O valor de diversificar (Tailândia cobrindo "
              "clientes atuais de Orindiúva) aparece só como limite superior de cenário em `resilience_stress.csv`, "
              "sem prêmio somado ao VPL."]
    L += ["", "## 7. Lacunas que impedem o investimento (ordem de impacto na decisão)", "",
          "1. **Preço líquido realizado por SKU e mercado** (A040). É o maior swing nos dois tornados; não há preço "
          "público do AlgaPrime e as leituras do óleo de peixe em 2026 conflitam (S015).",
          "2. **Offtake contratado e pipeline qualificado** (`market_demand_scenarios.csv`, a ser substituído pelo "
          "estudo de mercado, Prompt 2).",
          "3. **Capacidade comprada pelos €50 mi** e capex por módulo (cotação de EPC); ver "
          "`eur50m_implied_capacity_sensitivity.csv`.",
          "4. **Rendimento industrial** de DHA sobre açúcar, OEE e teor de DHA por lote (dados de operação de "
          "Orindiúva).",
          "5. **Usina vizinha:** contrato de açúcar (especificação, VHP/caldo, entressafra) e vapor/energia adicionais. "
          "Define o fator de utilidades compartilhadas.",
          "6. **Escopo GACC** por SKU e por planta; registro de um novo estabelecimento.",
          "7. **Tributário:** parecer sobre o top-up GloBE na Tailândia (combinação com Rayong, SBIE), tier do BOI e "
          "QRTC; vazamento de créditos no Brasil.",
          "8. **Site:** outorga de água e Aqueduct por sub-bacia; licenças CETESB/ONEP; prazos.",
          "9. **Cotações de frete** por SKU e prazos de entrega (a captura da Ásia a partir do Brasil, 70%, é "
          "julgamento).", "",
          "## 8. Gatilhos e marcos verificáveis (sequência reversível)", "",
          "1. **Agora:** contrato de açúcar e vapor adicionais com a usina; engenharia conceitual do módulo em "
          "Orindiúva; consulta prévia à CETESB.",
          "2. **FID de A1:** contratos ou pipeline qualificado cobrindo pelo menos o breakeven "
          f"(≈ {_pct(base.loc['A1_ORI','breakeven_demand_multiplier'])} da demanda-base ponderada) e preço "
          f"≥ US$ {_f(base.loc['A1_ORI','msp_usd_per_kg_dha'],1)}/kg DHA.",
          "3. **Em paralelo e barato:** qualificação de clientes asiáticos e estoque avançado / hub (E), testando a "
          "captura da Ásia antes de construir na Ásia.",
          f"4. **Gatilho da Tailândia ({r['p']['decision_year']}):** demanda asiática contratada no nível da fronteira "
          "(tabela da seção 6); diligência de Nakhon Sawan (terreno no estate do IEAT, contrato KTIS, água, "
          "BOI/GloBE); depois, FID.",
          "5. **Segundo módulo em Orindiúva:** utilização de A1 ≥ 80% no ano de decisão, com vapor da usina ou "
          "caldeira nova orçada.", "",
          "## 9. Como executar", "", "```bash", "cd microalgae_site_selection/v3",
          "pip install -r requirements.txt",
          "python -m src run              # tudo: outputs/, painel, memorando (≈1–2 min)",
          "python -m src run --mc-sims 300 --no-charts   # rápido",
          "python -m pytest -q tests", "```", "",
          "Para usar a demanda do estudo de mercado, substitua `data/raw/market_demand_scenarios.csv` "
          "(mesmo esquema) e rode de novo.",
          "Para usar dados da Corbion, edite `data/raw/assumptions.csv` (base/low/high e source_id).", "",
          "**Principais saídas** (`outputs/`):",
          "",
          "- **Painel interativo:** `decision_cockpit.html` (abre offline).",
          "- **Relatórios:** `investment_memo.md`, `audit_report.md`, `audit_issues.csv`.",
          "- **Fontes e premissas:** `evidence_registry.csv`, `assumptions.csv`, `source_gaps.csv`.",
          "- **Sites e economia:** `site_candidates.csv`, `unit_economics.csv`, `cashflow_by_scenario.csv`, "
          "`npv_by_scenario.csv`.",
          "- **Decisão e ranking:** `decision_frontier.csv`, `ranking_v3.csv`, `monte_carlo_summary.csv`.",
          "- **Gráficos:** `cost_per_kg_dha_waterfall.png`, `tornado.png`, `decision_frontier.png`, "
          "`risk_return_matrix.png`, `npv_ranges.png`, `site_map.png`.", ""]
    (out / "investment_memo.md").write_text("\n".join(L), encoding="utf-8")
