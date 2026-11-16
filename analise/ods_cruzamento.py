# ods_cruzamento.py
# Cruza o microcredito de cada UF (nosso fato regional) com o perfil de quem
# trabalha por conta propria ou como empregador naquela UF (IBGE, Censo 2022),
# pras ODS 5 e 18.
#
# a unidade aqui e a UF, nao a pessoa. a base do bcb nao tem sexo nem raca,
# entao isso descreve territorio e nao quem pegou o credito (falacia
# ecologica, ver docs/ODS_ANALISE.md).
#
# precisa de:
#   data/processed/fato_credito_regional.csv   (gerado pelo tratar.py)
#   data/ibge_ocupacao_uf_2022.csv             (totais por sexo e por raca)
#   data/ibge_sexo_raca_uf_2022.csv            (gerado pelo baixar_ibge.py)
# gera:
#   docs/evidencias/ods_cruzamento_uf.csv
#   docs/evidencias/ods_cruzamento.png

import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

BASE = os.path.join(os.path.dirname(__file__), "..")

REGIAO = {
    "AC": "Norte", "AM": "Norte", "AP": "Norte", "PA": "Norte", "RO": "Norte",
    "RR": "Norte", "TO": "Norte",
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste",
    "PB": "Nordeste", "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste",
    "SE": "Nordeste",
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MS": "Centro-Oeste", "MT": "Centro-Oeste",
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    "PR": "Sul", "RS": "Sul", "SC": "Sul",
}


def carteira_por_uf(df, rotulo):
    # carteira e um saldo, entao uso a media dos meses e nao a soma.
    # a inadimplencia e ponderada pela carteira (media simples das taxas
    # estaria errada)
    d = df.copy()
    d["inadimplido"] = d["taxa_inadimplencia"] * d["valor_carteira_ativa"]
    meses = d["data_referencia"].nunique()
    g = d.groupby("uf", as_index=False).agg(
        soma_carteira=("valor_carteira_ativa", "sum"),
        soma_inadimplido=("inadimplido", "sum"),
    )
    g["carteira_" + rotulo] = g["soma_carteira"] / meses
    g["inadimplencia_" + rotulo] = g["soma_inadimplido"] / g["soma_carteira"]
    return g[["uf", "carteira_" + rotulo, "inadimplencia_" + rotulo]]


def mulheres_pretas_pardas():
    # esse csv tem sexo e raca cruzados, ai da pra contar mulheres pretas e
    # pardas. os valores cruzados vem arredondados pelo ibge, entao a soma
    # difere ate 0,1% dos totais do outro csv
    d = pd.read_csv(os.path.join(BASE, "data", "ibge_sexo_raca_uf_2022.csv"))
    total = d.groupby("uf")["ocupados"].sum()
    mulheres = d[d["sexo"] == "Mulheres"]
    mpp = mulheres[mulheres["cor_raca"].isin(["Preta", "Parda"])].groupby("uf")["ocupados"].sum()
    mulheres_total = mulheres.groupby("uf")["ocupados"].sum()
    return pd.DataFrame({
        "mulheres_pretas_pardas": mpp,
        "part_mulheres_pretas_pardas": mpp / total,
        "mulheres_pp_entre_mulheres": mpp / mulheres_total,
    }).reset_index()


def montar():
    fato = pd.read_csv(os.path.join(BASE, "data", "processed", "fato_credito_regional.csv"))
    fato["data_referencia"] = pd.to_datetime(fato["data_referencia"])
    ibge = pd.read_csv(os.path.join(BASE, "data", "ibge_ocupacao_uf_2022.csv"))
    ibge = ibge.merge(mulheres_pretas_pardas(), on="uf")

    # 2022 e o ano do censo. julho/2026 e so uma checagem
    a2022 = fato[fato["data_referencia"].dt.year == 2022]
    ultimo = fato[fato["data_referencia"] == fato["data_referencia"].max()]

    base = ibge.merge(carteira_por_uf(a2022, "2022"), on="uf")
    base = base.merge(carteira_por_uf(ultimo, "2026_07"), on="uf")

    # divide pelo numero de ocupados pra nao medir so o tamanho da economia
    pop = base["ocupados_empregador_contapropria"]
    base["carteira_per_capita_2022"] = base["carteira_2022"] / pop
    base["carteira_per_capita_2026_07"] = base["carteira_2026_07"] / pop
    base["regiao"] = base["uf"].map(REGIAO)
    return base.sort_values("uf").reset_index(drop=True)


def spearman(x, y):
    r = stats.spearmanr(x, y)
    return r.statistic, r.pvalue


def relatar(base):
    ne = base[base.regiao == "Nordeste"].carteira_2022.sum() / base.carteira_2022.sum()
    print(f"UFs: {len(base)} | carteira do Nordeste em 2022: {ne:.1%} do total\n")

    print("correlacoes de spearman (27 UFs)")
    pares = [
        ("part_mulheres", "carteira_per_capita_2022", "ODS 5: mulheres x carteira (2022)"),
        ("part_mulheres", "inadimplencia_2022", "ODS 5: mulheres x inadimplencia (2022)"),
        ("part_preta_parda", "carteira_per_capita_2022", "ODS 18: pretas e pardas x carteira (2022)"),
        ("part_preta_parda", "inadimplencia_2022", "ODS 18: pretas e pardas x inadimplencia (2022)"),
        ("part_mulheres_pretas_pardas", "carteira_per_capita_2022", "ODS 5 e 18: mulheres pretas e pardas x carteira (2022)"),
        ("part_mulheres_pretas_pardas", "inadimplencia_2022", "ODS 5 e 18: mulheres pretas e pardas x inadimplencia (2022)"),
        ("carteira_per_capita_2022", "inadimplencia_2022", "controle: carteira x inadimplencia (2022)"),
        ("part_mulheres", "carteira_per_capita_2026_07", "checagem: mulheres x carteira (jul/2026)"),
        ("part_preta_parda", "carteira_per_capita_2026_07", "checagem: pretas e pardas x carteira (jul/2026)"),
    ]
    for x, y, nome in pares:
        r, p = spearman(base[x], base[y])
        print(f"{nome:<62} rho = {r:6.3f}   p = {p:.4f}")

    # o nordeste puxa tudo, entao repito sem ele
    sem_ne = base[base.regiao != "Nordeste"]
    print(f"\nsem as 9 UFs do Nordeste ({len(sem_ne)} UFs)")
    for col, nome in [("part_preta_parda", "pretas e pardas"),
                      ("part_mulheres", "mulheres"),
                      ("part_mulheres_pretas_pardas", "mulheres pretas e pardas")]:
        r, p = spearman(sem_ne[col], sem_ne["carteira_per_capita_2022"])
        print(f"{nome + ' x carteira':<62} rho = {r:6.3f}   p = {p:.4f}")

    print("\nmediana por regiao")
    print(base.groupby("regiao").agg(
        ufs=("uf", "size"),
        carteira_per_capita=("carteira_per_capita_2022", "median"),
        inadimplencia=("inadimplencia_2022", "median"),
        part_mulheres=("part_mulheres", "median"),
        part_preta_parda=("part_preta_parda", "median"),
        part_mulheres_pretas_pardas=("part_mulheres_pretas_pardas", "median"),
    ).round(3).to_string())


def grafico(base, destino):
    paineis = [
        ("part_preta_parda", "ODS 18: pretas e pardas"),
        ("part_mulheres", "ODS 5: mulheres"),
        ("part_mulheres_pretas_pardas", "ODS 5 e 18: mulheres pretas e pardas"),
    ]
    fig, eixos = plt.subplots(1, 3, figsize=(15, 5), sharey=True)
    for ax, (col, titulo) in zip(eixos, paineis):
        cores = base["regiao"].map(lambda r: "tab:orange" if r == "Nordeste" else "tab:blue")
        ax.scatter(base[col] * 100, base["carteira_per_capita_2022"], c=cores)
        for _, linha in base.iterrows():
            ax.annotate(linha["uf"], (linha[col] * 100, linha["carteira_per_capita_2022"]),
                        textcoords="offset points", xytext=(4, 4), fontsize=7)
        rho, p = spearman(base[col], base["carteira_per_capita_2022"])
        ax.set_title(f"{titulo}\nrho = {rho:.2f}, p = {p:.3f}", fontsize=10)
        ax.set_xlabel("participação entre conta própria e empregadores (%)")
        ax.set_yscale("log")
        ax.grid(alpha=0.3)
    eixos[0].set_ylabel("carteira de microcrédito por ocupado (R$, escala log)")
    fig.suptitle("Microcrédito e perfil dos ocupados por UF, 2022 (laranja = Nordeste)")
    fig.text(0.01, 0.01, "Descreve territórios, não quem pegou o crédito: a base do BCB não tem sexo nem raça.",
             fontsize=8)
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    fig.savefig(destino, dpi=150)


if __name__ == "__main__":
    base = montar()
    pasta = os.path.join(BASE, "docs", "evidencias")
    os.makedirs(pasta, exist_ok=True)
    base.to_csv(os.path.join(pasta, "ods_cruzamento_uf.csv"), index=False)
    relatar(base)
    grafico(base, os.path.join(pasta, "ods_cruzamento.png"))
    print("\ntabela e grafico salvos em docs/evidencias/")
