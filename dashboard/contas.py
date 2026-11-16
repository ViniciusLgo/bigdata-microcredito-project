# contas.py
# As contas do dashboard, separadas do app.py pra poder testar sem abrir o
# streamlit (ver tests/test_dashboard.py).

import pandas as pd


def fmt_num(v, casas=0):
    s = f"{v:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_reais(v):
    if v >= 1e9:
        return "R$ " + fmt_num(v / 1e9, 2) + " bi"
    if v >= 1e6:
        return "R$ " + fmt_num(v / 1e6, 1) + " mi"
    return "R$ " + fmt_num(v)


def agregar(df, por, ocupados):
    # soma por grupo. a inadimplencia e ponderada pela carteira (media simples
    # das taxas estaria errada) e as operacoes negativas ficam de fora porque
    # o bcb nao explica o que elas sao
    d = df.copy()
    d["inadimplido"] = d["taxa_inadimplencia"] * d["valor_carteira_ativa"]
    d["ops_validas"] = d["quantidade_operacoes"].where(d["quantidade_operacoes"] >= 0)
    g = d.groupby(por, as_index=False).agg(
        carteira=("valor_carteira_ativa", "sum"),
        inadimplido=("inadimplido", "sum"),
        operacoes=("ops_validas", "sum"),
    )
    g["inadimplencia"] = g["inadimplido"] / g["carteira"] * 100

    # carteira por ocupado so faz sentido quando o grupo tem uf ou regiao.
    # a populacao de cada grupo e a soma dos ocupados das UFs que aparecem
    # naquele grupo (e naquele mes, se o mes estiver em "por"), senao o
    # denominador mudaria conforme o periodo escolhido
    g["carteira_por_ocupado"] = float("nan")
    if "uf" in por or "regiao" in por:
        colunas = por if "uf" in por else por + ["uf"]
        ufs = d[colunas].drop_duplicates().copy()
        ufs["pop"] = ufs["uf"].map(ocupados)
        pop = ufs.groupby(por, as_index=False)["pop"].sum()
        g = g.merge(pop, on=por, how="left")
        g["carteira_por_ocupado"] = g["carteira"] / g["pop"]
    return g


def participacao_grupo(perfil, sexo, cores):
    # quantos % dos ocupados de cada uf sao do grupo escolhido (sexo e cor)
    total = perfil.groupby("uf")["ocupados"].sum()
    grupo = perfil.copy()
    if sexo != "Todos":
        grupo = grupo[grupo["sexo"] == sexo]
    if cores:
        grupo = grupo[grupo["cor_raca"].isin(cores)]
    return (grupo.groupby("uf")["ocupados"].sum() / total).rename("part_grupo").reset_index()


def spearman(x, y):
    # spearman = correlacao dos postos
    return x.rank().corr(y.rank())
