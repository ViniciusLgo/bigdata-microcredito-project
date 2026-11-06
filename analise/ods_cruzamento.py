"""Cruzamento territorial: microcredito (SCR.data) x perfil dos ocupados por conta
propria e empregadores (IBGE, Censo 2022) - ODS 5 e ODS 18.

Unidade de analise: a UF. Nao ha juncao no nivel da pessoa e nenhum atributo
demografico e atribuido a nenhuma operacao de credito. Ver docs/DECISOES_TECNICAS.md,
decisao D-16, e a ressalva sobre falacia ecologica em docs/ODS_ANALISE.md.

Entradas:
  data/processed/fato_credito_regional.csv   (nosso fato regional)
  data/ibge_ocupacao_uf_2022.csv             (tabela SIDRA 10261)
Saidas:
  docs/evidencias/ods_cruzamento_uf.csv
  docs/evidencias/ods_cruzamento.png

uso:  python analise/ods_cruzamento.py
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from scipy import stats

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
P = lambda *p: os.path.join(BASE, *p)

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

AZUL, LARANJA = "#2a78d6", "#eb6834"
TINTA, TINTA2 = "#0b0b0b", "#52514e"


def carteira_por_uf(df, rotulo):
    """Agrega carteira e inadimplencia por UF.

    A taxa agregada e PONDERADA pela carteira: reconstroi o valor inadimplido
    (taxa x carteira) linha a linha, soma, e divide pela carteira somada. Media
    simples das taxas seria errada (ver decisao D-09).
    """
    d = df.copy()
    d["valor_inadimplencia"] = d["taxa_inadimplencia"] * d["valor_carteira_ativa"]
    meses = d["data_referencia"].nunique()
    g = d.groupby("uf", as_index=False).agg(
        soma_carteira=("valor_carteira_ativa", "sum"),
        soma_inadimplido=("valor_inadimplencia", "sum"),
    )
    g[f"carteira_{rotulo}"] = g["soma_carteira"] / meses   # estoque medio mensal
    g[f"inadimplencia_{rotulo}"] = g["soma_inadimplido"] / g["soma_carteira"]
    return g[["uf", f"carteira_{rotulo}", f"inadimplencia_{rotulo}"]]


def sp(x, y):
    r = stats.spearmanr(x, y)
    return r.statistic, r.pvalue


def montar():
    fato = pd.read_csv(P("data", "processed", "fato_credito_regional.csv"))
    fato["data_referencia"] = pd.to_datetime(fato["data_referencia"])
    ibge = pd.read_csv(P("data", "ibge_ocupacao_uf_2022.csv"))

    a2022 = fato[fato["data_referencia"].dt.year == 2022]            # ano do Censo
    ultimo = fato[fato["data_referencia"] == fato["data_referencia"].max()]  # robustez

    base = (ibge.merge(carteira_por_uf(a2022, "2022"), on="uf")
                .merge(carteira_por_uf(ultimo, "2026_07"), on="uf"))
    pop = base["ocupados_empregador_contapropria"]
    base["carteira_per_capita_2022"] = base["carteira_2022"] / pop
    base["carteira_per_capita_2026_07"] = base["carteira_2026_07"] / pop
    base["regiao"] = base["uf"].map(REGIAO)
    return base.sort_values("uf").reset_index(drop=True), a2022, ultimo


def relatar(base):
    print(f"UFs: {len(base)}   carteira do Nordeste em 2022: "
          f"{base[base.regiao == 'Nordeste'].carteira_2022.sum() / base.carteira_2022.sum():.1%} "
          f"do total nacional\n")

    print("correlacoes de Spearman (n = 27 UFs)")
    print(f"{'relacao':<62} {'rho':>7} {'p':>8}")
    print("-" * 79)
    pares = [
        ("part_mulheres", "carteira_per_capita_2022", "ODS 5  mulheres x carteira per capita (2022)"),
        ("part_mulheres", "inadimplencia_2022", "ODS 5  mulheres x inadimplencia (2022)"),
        ("part_preta_parda", "carteira_per_capita_2022", "ODS 18 pretas e pardas x carteira per capita (2022)"),
        ("part_preta_parda", "inadimplencia_2022", "ODS 18 pretas e pardas x inadimplencia (2022)"),
        ("carteira_per_capita_2022", "inadimplencia_2022", "controle: carteira per capita x inadimplencia (2022)"),
        ("part_mulheres", "carteira_per_capita_2026_07", "robustez: mulheres x carteira per capita (jul/2026)"),
        ("part_preta_parda", "carteira_per_capita_2026_07", "robustez: pretas e pardas x carteira per capita (jul/2026)"),
    ]
    for x, y, rot in pares:
        r, p = sp(base[x], base[y])
        print(f"{rot:<62} {r:>7.3f} {p:>8.4f}")

    sn = base[base.regiao != "Nordeste"]
    print(f"\nexcluindo as 9 UFs do Nordeste (n = {len(sn)})")
    for col, rot in [("part_preta_parda", "pretas e pardas x carteira per capita"),
                     ("part_mulheres", "mulheres x carteira per capita")]:
        r, p = sp(sn[col], sn["carteira_per_capita_2022"])
        print(f"{rot:<62} {r:>7.3f} {p:>8.4f}")

    print("\nmediana por regiao")
    print(base.groupby("regiao").agg(
        ufs=("uf", "size"),
        carteira_per_capita=("carteira_per_capita_2022", "median"),
        inadimplencia=("inadimplencia_2022", "median"),
        part_mulheres=("part_mulheres", "median"),
        part_preta_parda=("part_preta_parda", "median"),
    ).round(3).to_string())


def posicionar_rotulos(ax, pontos):
    """Escreve a sigla de cada UF perto do seu ponto evitando sobreposicao.

    Testa alguns deslocamentos em ordem e usa o primeiro que nao colide com um
    rotulo ja colocado, medindo em pixels (nao em unidades de dado, que mudam
    com a escala log).
    """
    opcoes = [(0, 9), (0, -15), (13, -3), (-13, -3), (13, 7), (-13, 7),
              (0, 17), (0, -23)]
    ocupados = []
    for x, y, sigla in pontos:
        px, py = ax.transData.transform((x, y))
        for dx, dy in opcoes:
            caixa = (px + dx - 9, py + dy - 5, px + dx + 9, py + dy + 5)
            if all(caixa[2] < o[0] or caixa[0] > o[2] or
                   caixa[3] < o[1] or caixa[1] > o[3] for o in ocupados):
                break
        ocupados.append(caixa)
        ax.annotate(sigla, (x, y), textcoords="offset points", xytext=(dx, dy),
                    ha="center", va="center", fontsize=7.5, color=TINTA2, zorder=4)


def grafico(base, destino):
    fig, eixos = plt.subplots(1, 2, figsize=(12.5, 5.6), sharey=True)
    fig.patch.set_facecolor("#fcfcfb")

    painel = [
        ("part_preta_parda", "Participação de pessoas pretas e pardas",
         "ODS 18 — Igualdade Étnico-Racial"),
        ("part_mulheres", "Participação de mulheres",
         "ODS 5 — Igualdade de Gênero"),
    ]

    for ax, (col, rotulo_x, titulo) in zip(eixos, painel):
        ax.set_facecolor("#fcfcfb")
        for ne, cor, nome in [(True, LARANJA, "Nordeste"), (False, AZUL, "Demais UFs")]:
            d = base[(base.regiao == "Nordeste") == ne]
            ax.scatter(d[col] * 100, d["carteira_per_capita_2022"],
                       s=70, color=cor, edgecolor="#fcfcfb", linewidth=2,
                       zorder=3, label=nome if ax is eixos[0] else None)

        rho, p = sp(base[col], base["carteira_per_capita_2022"])
        ax.set_yscale("log")
        ax.set_title(titulo, fontsize=11.5, color=TINTA, pad=14, loc="left")
        ax.set_xlabel(f"{rotulo_x} entre conta própria e empregadores (%)\n"
                      f"IBGE, Censo 2022", fontsize=9, color=TINTA2)
        ax.annotate(f"Spearman ρ = {rho:.2f}   p = {p:.3f}",
                    xy=(0.98, 0.04), xycoords="axes fraction", ha="right",
                    fontsize=9, color=TINTA2)
        ax.grid(True, which="major", color="#e4e3df", linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)
        for lado in ("top", "right"):
            ax.spines[lado].set_visible(False)
        for lado in ("left", "bottom"):
            ax.spines[lado].set_color("#d6d5d0")
        ax.tick_params(colors=TINTA2, labelsize=9)

    eixos[0].set_ylabel("Carteira ativa de microcrédito por pessoa ocupada\n"
                        "por conta própria ou como empregadora (R$, escala log)",
                        fontsize=9, color=TINTA2)
    eixos[0].legend(frameon=False, loc="upper left", fontsize=9,
                    labelcolor=TINTA2, handletextpad=0.4)

    fig.suptitle("Microcrédito e perfil dos ocupados por conta própria, por UF — 2022",
                 fontsize=13.5, color=TINTA, x=0.065, ha="left", y=0.99)
    fig.text(0.065, 0.015,
             "Carteira ativa: SCR.data (BCB), submodalidade Microcrédito, média dos 12 meses de 2022. "
             "Denominador: IBGE, Censo 2022, tabela SIDRA 10261.\n"
             "A análise descreve territórios, não o perfil de quem tomou crédito — "
             "a base do BCB não contém sexo nem cor ou raça.",
             fontsize=8, color=TINTA2, ha="left")

    fig.tight_layout(rect=[0, 0.075, 1, 0.945])

    # os rotulos entram depois do layout final, quando a escala em pixels ja esta
    # definida e da para medir colisao de verdade
    fig.canvas.draw()
    for ax, (col, _, _) in zip(eixos, painel):
        d = base.sort_values("carteira_per_capita_2022", ascending=False)
        posicionar_rotulos(ax, list(zip(d[col] * 100,
                                        d["carteira_per_capita_2022"], d["uf"])))

    fig.savefig(destino, dpi=200, facecolor=fig.get_facecolor())
    print(f"\ngrafico salvo em {destino}")


def main():
    base, _, _ = montar()
    os.makedirs(P("docs", "evidencias"), exist_ok=True)
    csv_saida = P("docs", "evidencias", "ods_cruzamento_uf.csv")
    base.to_csv(csv_saida, index=False)
    print(f"tabela salva em {csv_saida}\n")
    relatar(base)
    grafico(base, P("docs", "evidencias", "ods_cruzamento.png"))


if __name__ == "__main__":
    main()
