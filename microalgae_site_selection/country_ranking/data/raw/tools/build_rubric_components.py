"""Generate data/raw/market_rubric_components.csv (component scores with evidence; lo/hi = interval)."""
import csv, sys
OUT = sys.argv[1]
R = []
def add(n, c, rub, comp, lo, hi, ev, src=""):
    R.append([n, c, rub, comp, lo, hi, ev, src])
U = "não encontrado → faixa"
# ---------------- CANAL (A estágio 0-4, B cobertura 0-3, C profundidade 0-2, D presença Corbion 0-1)
# Premissa Corbion (26/10/2026): em salmão e camarão a venda é só à BioMar. B = capacidade BioMar no país
# (3 ≥300 kt; 2 150-300 kt; 1 30-150 kt; 0 <30 kt ou nenhuma); C = nº de fábricas BioMar (2 = duas ou mais).
# Pet food segue pelo canal IQI (B = cobertura do distribuidor).
canal = {
 ("salmon","Norway"): [(3,3,"BioMar usa AlgaPrime em ração de salmão; reconfirmado abr/2025","R15;R44"),(3,3,"BioMar Noruega ~720 kt (≥300 kt)","R12"),(2,2,"2 fábricas BioMar (Myre, Karmøy)","R12"),(0,1,"Presença Corbion na Noruega "+U,"")],
 ("salmon","Chile"): [(2,3,"BioMar Chile/Ventisqueros: adoção histórica, data incerta (envelhecimento)","R12;R37"),(3,3,"BioMar Chile ~300 kt (Pargua + Ercilla)","R12"),(2,2,"Fábricas BioMar em Pargua e Ercilla","R12"),(1,1,"Equipe Corbion Chile (2020)","R37")],
 ("salmon","United Kingdom"): [(2,3,"BioMar UK (Grangemouth): adoção histórica pré-2022","R37"),(1,2,"Capacidade BioMar Grangemouth "+U,"R12"),(1,1,"1 fábrica BioMar","R12"),(0,1,"Presença Corbion no Reino Unido "+U,"")],
 ("salmon","Faroe Islands"): [(0,0,"Ração local (Havsbrún/Bakkafrost); nenhum cliente AlgaPrime","R37"),(0,0,"—",""),(0,0,"—",""),(0,0,"Sem presença","")],
 ("salmon","Canada"): [(0,0,"Sem fábrica BioMar no Canadá","R12"),(0,0,"—",""),(0,0,"—",""),(0,1,"Presença Corbion no Canadá "+U,"")],
 ("salmon","Iceland"): [(0,0,"Sem fábrica BioMar na Islândia","R12"),(0,0,"—",""),(0,0,"—",""),(0,0,"Sem presença","")],
 ("salmon","Australia"): [(0,1,"BioMar Austrália (Wesley Vale, Tasmânia) – conhecimento prévio, não verificado nesta revisão",""),(0,2,"Capacidade "+U,""),(0,1,U,""),(0,1,"Presença Corbion APAC "+U,"")],
 ("salmon","New Zealand"): [(0,0,"Sem cliente identificado","R37"),(0,0,"—",""),(0,0,"—",""),(0,0,"Sem presença","")],
 ("salmon","Turkey"): [(1,1,"BioMar Turquia (Söke) – cliente global com fábrica","R12"),(0,2,"Capacidade BioMar Turquia "+U,"R12"),(1,1,"1 fábrica BioMar","R12"),(0,0,"Sem presença","")],
 ("salmon","United States"): [(0,0,"Atlantic Sapphire usa Veramaris; sem cliente AlgaPrime em salmão","R31"),(0,0,"—",""),(0,0,"—",""),(1,1,"Corbion US (operações e escritórios)","R04")],
 ("salmon","China"): [(1,1,"BioMar–Tongwei Wuxi: ração BAP de truta (canal, sem teste)","R48"),(2,2,"BioMar–Tongwei: Haiwei 150 kt + Wuxi 50 kt = 200 kt (Wuxi dobra em 1T2027)","R12;R14"),(2,2,"2 fábricas BioMar (Haiwei, Wuxi)","R12;R14"),(1,1,"Corbion entrou na China em 2025 com executivos locais","R08")],
 ("shrimp","Ecuador"): [(1,1,"BioMar Ecuador (410 kt) – cliente global com fábrica; uso AlgaPrime não documentado","R12;R13"),(3,3,"BioMar Equador 410 kt (2026)","R13"),(1,1,"1 fábrica BioMar (Durán)","R13"),(0,1,"Presença Corbion no Equador "+U,"")],
 ("shrimp","India"): [(0,0,"Sem cliente identificado","R37"),(0,0,"—",""),(0,0,"—",""),(0,1,"Presença Corbion na Índia "+U,"")],
 ("shrimp","Vietnam"): [(1,1,"BioMar–Viet-Uc JV (Châu Thành)","R12"),(0,0,"BioMar–Viet-Uc ~30 kt (<30 kt)","R12"),(1,1,"1 fábrica BioMar","R12"),(0,1,"Presença Corbion no Vietnã "+U,"")],
 ("shrimp","Indonesia"): [(0,0,"Sem cliente identificado","R37"),(0,0,"—",""),(0,0,"—",""),(0,1,U,"")],
 ("shrimp","China"): [(1,1,"BioMar–Tongwei (Haiwei, Wuxi) – canal + GACC","R12;R14;R08"),(2,2,"BioMar–Tongwei 200 kt (→250 kt em 2027)","R12;R14"),(2,2,"2 fábricas BioMar (Haiwei, Wuxi)","R12;R14"),(1,1,"Corbion China desde 2025","R08")],
 ("shrimp","Thailand"): [(2,3,"Thai Union Feedmill: adoção 2019-20 (>3 anos; notícias 2025 não reconfirmam uso)","R17;R18"),(0,0,"Sem fábrica BioMar na Tailândia (TFM não é BioMar)","R12"),(0,0,"—",""),(1,1,"Fábrica Corbion em Rayong","R06")],
 ("shrimp","Brazil"): [(0,0,"Sem cliente de camarão identificado","R37"),(0,0,"—",""),(0,0,"—",""),(1,1,"Orindiúva (sede da produção)","R34")],
 ("shrimp","Mexico"): [(0,0,"Sem cliente identificado","R37"),(0,0,"—",""),(0,0,"—",""),(0,1,U,"")],
 ("shrimp","Saudi Arabia"): [(0,0,"Sem cliente identificado","R37"),(0,0,"—",""),(0,0,"—",""),(0,0,"Sem presença","")],
 ("shrimp","Philippines"): [(0,0,"Sem cliente identificado","R37"),(0,0,"—",""),(0,0,"—",""),(0,0,"Sem presença","")],
 ("shrimp","Bangladesh"): [(0,0,"Sem cliente identificado","R37"),(0,0,"—",""),(0,0,"—",""),(0,0,"Sem presença","")],
 ("shrimp","Honduras"): [(0,0,"Sem cliente identificado","R37"),(0,0,"—",""),(0,0,"—",""),(0,0,"Sem presença","")],
}
for c in ["Germany","France","Italy","Spain","Poland"]:
    canal[("pet",c)] = [(1,1,"IQI Petfood distribui AlgaPrime DHA (canal)","R16;R19"),(0,2,"Cobertura do distribuidor "+U,"R16"),(1,1,"Só IQI","R16"),(1,1,"Corbion Europa (sede NL; fábrica em Montmeló, ES)","R05")]
canal.update({
 ("pet","United States"): [(1,1,"IQI Petfood (América do Norte) + one-pagers AlgaPrime pet","R16;R19"),(0,2,"Cobertura do distribuidor "+U,"R16"),(1,1,"Só IQI","R16"),(1,1,"Corbion US","R04")],
 ("pet","Canada"): [(1,1,"IQI Petfood (América do Norte)","R16"),(0,2,U,""),(1,1,"Só IQI","R16"),(0,1,U,"")],
 ("pet","United Kingdom"): [(0,1,"IQI no Reino Unido não documentado",""),(0,1,U,""),(0,1,U,""),(1,1,"Corbion Europa (região)","R05")],
 ("pet","Brazil"): [(0,0,"Sem canal pet identificado","R37"),(0,0,"—",""),(0,0,"—",""),(1,1,"Orindiúva","R34")],
 ("pet","China"): [(0,0,"Sem canal pet identificado (só GACC)","R08"),(0,0,"—",""),(0,0,"—",""),(1,1,"Corbion China desde 2025","R08")],
 ("pet","Japan"): [(0,0,"Sem canal pet identificado",""),(0,0,"—",""),(0,0,"—",""),(0,1,"Escritório Corbion no Japão "+U,"")],
 ("pet","Mexico"): [(0,0,"Sem canal",""),(0,0,"—",""),(0,0,"—",""),(0,1,U,"")],
 ("pet","Argentina"): [(0,0,"Sem canal",""),(0,0,"—",""),(0,0,"—",""),(0,0,"Sem presença","")],
 ("pet","Australia"): [(0,0,"Sem canal",""),(0,0,"—",""),(0,0,"—",""),(0,1,U,"")],
 ("pet","Thailand"): [(0,0,"Sem canal pet",""),(0,0,"—",""),(0,0,"—",""),(1,1,"Fábrica Corbion em Rayong","R06")],
})
for (n,c),v in canal.items():
    for k,(lo,hi,ev,s) in zip("ABCD",v): add(n,c,"canal",k,lo,hi,ev,s)
# ---------------- REGISTRO (A status 0-4, B prazo 0-2, C barreiras 0-2, D incentivo 0-2)
EU_A = (3,3,"Catálogo UE de matérias-primas (Reg. 68/2013) + uso/distribuição documentados; nº do SKU não visto","R37;R16")
reg = {
 ("salmon","Norway"): [(3,3,"Uso comercial documentado; catálogo EEE; nº do SKU não visto","R15;R37"),(2,2,"Catálogo: sem pré-aprovação",""),(2,2,"Nenhuma barreira documentada (cepa não OGM)","R19"),(2,2,"Padrão ASC Feed; metas de redução de óleo de peixe; marca Kvarøy","R37")],
 ("salmon","Chile"): [(3,3,"Uso comercial documentado","R37"),(1,2,"Registro SAG "+U,""),(2,2,"Nenhuma documentada",""),(1,2,"ASC; marca Ventisqueros","R37")],
 ("salmon","United Kingdom"): [(3,3,"Uso comercial documentado; catálogo retido pós-Brexit","R37"),(2,2,"Catálogo",""),(2,2,"Nenhuma documentada",""),(2,2,"ASC; pressão do varejo","R37")],
 ("salmon","Faroe Islands"): [(1,2,"Regras feroesas seguem UE "+U,""),(1,2,U,""),(2,2,"Nenhuma documentada",""),(1,1,"ASC parcial","R37")],
 ("salmon","Iceland"): [(2,2,"EEE: catálogo UE","R37"),(2,2,"Catálogo",""),(2,2,"Nenhuma documentada",""),(1,1,"ASC parcial","R37")],
 ("salmon","Canada"): [(1,2,"Registro CFIA de ingrediente "+U,""),(0,1,"CFIA costuma ser lento "+U,""),(2,2,"Nenhuma documentada",""),(1,1,"ASC/BAP voluntário","")],
 ("salmon","Australia"): [(0,2,U,""),(0,1,U,""),(1,2,"Permissão de biossegurança (DAFF) para ingrediente importado",""),(1,1,"ASC voluntário","")],
 ("salmon","New Zealand"): [(0,2,U,""),(0,1,U,""),(1,2,"Requisitos MPI de importação",""),(1,1,"Certificação voluntária","")],
 ("salmon","Turkey"): [(0,2,U,""),(0,1,U,""),(1,2,U,""),(0,0,"Nenhum incentivo documentado","")],
 ("salmon","United States"): [(3,3,"Definições AAFCO para algas; AlgaPrime vendido nos EUA (pet)","R19"),(1,2,U,""),(2,2,"Nenhuma documentada",""),(1,1,"BAP/ASC voluntário","")],
 ("salmon","China"): [(3,3,"Aprovações GACC (8/7/2025) incl. aquicultura; nº MARA não visto","R08"),(0,1,"Regime MARA de novos ingredientes "+U,""),(1,1,"Certificado sanitário bilateral e controle de importação",""),(0,1,U,"")],
 ("shrimp","Ecuador"): [(0,2,"Registro Agrocalidad "+U,""),(1,2,U,""),(1,2,U,""),(1,1,"Sustainable Shrimp Partnership/ASC para exportação","")],
 ("shrimp","India"): [(0,2,U,""),(0,1,"Licença de importação de insumo de ração "+U,""),(0,1,"Controles de importação de ingredientes",""),(1,1,"ASC/BAP para exportação","")],
 ("shrimp","Vietnam"): [(1,2,"Lista de ingredientes de ração permitidos "+U,""),(1,2,U,""),(1,2,U,""),(1,1,"ASC/BAP para exportação","")],
 ("shrimp","Indonesia"): [(0,2,U,""),(0,1,U,""),(1,2,U,""),(1,1,"ASC/BAP para exportação","")],
 ("shrimp","China"): [(3,3,"Aprovações GACC (8/7/2025) incl. aquicultura; nº MARA não visto","R08"),(0,1,U,""),(1,1,"Certificado sanitário bilateral",""),(0,1,U,"")],
 ("shrimp","Thailand"): [(3,3,"Uso comercial na TFM documentado","R17"),(1,2,U,""),(2,2,"Nenhuma documentada",""),(1,1,"SeaChange (Thai Union)","R18")],
 ("shrimp","Brazil"): [(1,3,"Registro MAPA não verificado (G11)","R11"),(1,1,"MAPA: prazo médio",""),(2,2,"Produção local: sem barreira de importação","R34"),(0,0,"Nenhum incentivo documentado","")],
 ("shrimp","Mexico"): [(0,2,U,""),(1,2,U,""),(1,2,U,""),(0,0,"Nenhum documentado","")],
 ("shrimp","Saudi Arabia"): [(0,2,U,""),(0,1,"Registro SFDA "+U,""),(1,1,"Registro SFDA obrigatório",""),(0,0,"Nenhum documentado","")],
 ("shrimp","Philippines"): [(0,2,U,""),(0,1,U,""),(1,2,U,""),(0,0,"Nenhum documentado","")],
 ("shrimp","Bangladesh"): [(0,2,U,""),(0,0,"Processos lentos",""),(0,1,U,""),(0,0,"Nenhum documentado","")],
 ("shrimp","Honduras"): [(0,2,U,""),(1,2,U,""),(1,2,U,""),(1,1,"ASC/BAP para exportação","")],
}
for c in ["Germany","France","Italy","Spain","Poland"]:
    reg[("pet",c)] = [EU_A,(2,2,"Catálogo: sem pré-aprovação",""),(2,2,"Nenhuma documentada",""),(1,1,"Alegações de sustentabilidade em pet premium","")]
reg.update({
 ("pet","United States"): [(3,3,"Definições AAFCO; distribuição IQI documentada","R16;R19"),(1,2,U,""),(2,2,"Nenhuma documentada",""),(1,1,"Alegações de sustentabilidade","")],
 ("pet","United Kingdom"): [(2,3,"Catálogo retido pós-Brexit; distribuição não documentada",""),(2,2,"Catálogo",""),(2,2,"Nenhuma documentada",""),(1,1,"Alegações de sustentabilidade","")],
 ("pet","Canada"): [(2,3,"Distribuição IQI América do Norte; CFIA "+U,"R16"),(1,2,U,""),(2,2,"Nenhuma documentada",""),(1,1,"Alegações de sustentabilidade","")],
 ("pet","Brazil"): [(1,3,"Registro MAPA não verificado","R11"),(1,1,"MAPA: prazo médio",""),(2,2,"Produção local","R34"),(0,0,"Nenhum documentado","")],
 ("pet","China"): [(3,3,"GACC (2025) cobre pet food","R08"),(0,1,U,""),(1,1,"Certificado sanitário bilateral",""),(0,0,"Nenhum documentado","")],
 ("pet","Japan"): [(1,2,"Lei de segurança de pet food: sem pré-aprovação de ingrediente "+U,""),(1,2,U,""),(2,2,"Nenhuma documentada",""),(1,1,"Alegações de sustentabilidade","")],
 ("pet","Mexico"): [(0,2,U,""),(1,2,U,""),(1,2,U,""),(0,0,"Nenhum documentado","")],
 ("pet","Argentina"): [(0,2,U,""),(1,2,"Mercosul (origem Brasil)",""),(1,2,U,""),(0,0,"Nenhum documentado","")],
 ("pet","Australia"): [(0,2,U,""),(1,2,U,""),(1,2,"Biossegurança DAFF",""),(1,1,"Alegações de sustentabilidade","")],
 ("pet","Thailand"): [(1,2,"Registro de pet food "+U,""),(1,2,U,""),(2,2,"Nenhuma documentada",""),(0,0,"Nenhum documentado","")],
})
for (n,c),v in reg.items():
    for k,(lo,hi,ev,s) in zip("ABCD",v): add(n,c,"registro",k,lo,hi,ev,s)
# ---------------- POSIÇÃO COMPETITIVA (A concorrente 0-3, B ajuste 0-3, C custo entregue 0-2, D alavanca de marca 0-2)
FIT = {"salmon": (1,1,"Só DHA; salmão precisa de EPA+DHA e Veramaris entrega os dois","R39;R20"),
       "shrimp": (2,2,"DHA é crítico em larvicultura e reprodutores; EPA também conta","R39"),
       "pet": (2,2,"Alegações de DHA (filhotes/cognição); EPA para articulações vem de outra fonte","R19")}
LOCAL = {("salmon","United States"):"Veramaris Blair (EUA)",("pet","United States"):"Veramaris Blair (EUA)",
         ("salmon","Canada"):"Mara Renewables (Canadá)",
         ("pet","China"):"CABIO (China)"}
compA = {("salmon","Norway"):(1,1,"Veramaris via Skretting (Lingalaks 2018) – uso comercial","R31"),
         ("salmon","United States"):(1,1,"Veramaris na Atlantic Sapphire (2021); Nuseed Aquaterra","R31;R25"),
         ("salmon","Canada"):(1,2,"Veramaris em teste Cargill–Cermaq; Mara Renewables local","R31;R32"),
         ("salmon","Australia"):(1,2,"Nuseed Aquaterra (canola GM) – status não verificado","R25"),
         ("salmon","China"):(2,3,"Premissa Corbion: produtores chineses (CABIO/Runke/Huison) focam infantil/pet, sem foco em ração aquícola; nenhum uso aquícola documentado","R22;R37"),
         ("shrimp","China"):(2,3,"Idem: DHA algal chinês sem foco/uso documentado em ração de camarão","R22;R37"),
         ("shrimp","Thailand"):(1,2,"Mara Renewables tem a Thai Union Ingredients como investidora","R32"),
         ("pet","United States"):(1,1,"Veramaris O3 Max Pure lançado no Petfood Forum (abr/2026)","R21"),
         ("pet","China"):(0,0,"CABIO: DHA algal para pet com produção local","R22")}
compD = {("salmon","Norway"):(2,2,"Kvarøy Arctic: salmão 'alimentado com algas' no varejo","R37"),
         ("salmon","Chile"):(2,2,"Ventisqueros: salmão com DHA de algas","R37"),
         ("salmon","United Kingdom"):(1,2,"Pressão do varejo britânico por ração sustentável",""),
         ("salmon","United States"):(1,1,"Kvarøy vendido no varejo dos EUA","R37"),
         ("shrimp","Thailand"):(1,1,"SeaChange (Thai Union)","R18"),("shrimp","Ecuador"):(1,1,"Sustainable Shrimp Partnership",""),
         ("pet","United States"):(1,2,"Pet premium com alegações de sustentabilidade",""),("pet","United Kingdom"):(1,2,"Idem",""),
         ("salmon","Turkey"):(0,0,"Nenhuma",""),("shrimp","Saudi Arabia"):(0,0,"Nenhuma",""),("shrimp","Bangladesh"):(0,0,"Nenhuma","")}
for c in ["Germany","France","Italy","Spain","Poland"]: compD[("pet",c)] = (1,2,"Pet premium com alegações de sustentabilidade","")
# C2 (rev. 26/10): preço entregue, não prazo. Tarifa aplicada ao produto de origem Brasil (≤5% = 1).
TARIFF = {("salmon","Chile"):(0,"ACE-35 Mercosul–Chile: 0% para origem Brasil"),("salmon","United States"):(0,"MFN"),
          ("salmon","China"):(4,"alíquota provisória aplicada 4% (MFN 6,5%)"),("shrimp","China"):(4,"provisória 4%"),
          ("pet","China"):(4,"provisória 4%"),("shrimp","India"):(17.5,"MFN"),("shrimp","Vietnam"):(7.5,"MFN"),
          ("shrimp","Indonesia"):(2.5,"MFN"),("shrimp","Thailand"):(10,"MFN"),("shrimp","Brazil"):(0,"produção doméstica"),
          ("pet","Brazil"):(0,"produção doméstica"),("pet","United States"):(0,"MFN")}
for (n,c) in list(canal):
    a = compA.get((n,c), (2,3,"Nenhum concorrente algal documentado ("+U+")",""))
    add(n,c,"competicao","A",*a)
    add(n,c,"competicao","B",*FIT[n])
    loc = LOCAL.get((n,c))
    add(n,c,"competicao","C1",0 if loc else 1,0 if loc else 1,("Produção concorrente local: "+loc) if loc else "Sem produção concorrente local documentada","R20;R22;R32" if loc else "")
    t = TARIFF.get((n,c))
    if t is None:
        add(n,c,"competicao","C2",0,1,"Tarifa aplicada à origem Brasil "+U,"R45")
    else:
        add(n,c,"competicao","C2",float(t[0] <= 5),float(t[0] <= 5),f"Tarifa aplicada {t[0]:g}% ({t[1]}); 1 se ≤5%","R45")
    add(n,c,"competicao","D",*compD.get((n,c),(0,1,"Alavanca de marca "+U,"")))
with open(OUT,"w",newline="") as f:
    w=csv.writer(f); w.writerow(["niche","country","rubric","component","lo","hi","evidence","source_id"]); w.writerows(R)
print(len(R))
