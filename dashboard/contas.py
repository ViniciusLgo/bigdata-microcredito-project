# contas.py
# As contas do dashboard, separadas do app.py pra poder testar sem abrir o
# streamlit (ver tests/test_dashboard.py).

import math

import pandas as pd


def fmt_num(v, casas=0):
    if v is None or pd.isna(v) or not math.isfinite(v):
        return "indisponível"
    s = f"{v:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_reais(v):
    if v is None or pd.isna(v) or not math.isfinite(v):
        return "indisponível"
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
        # Um grupo sem nenhuma contagem válida é desconhecido, não zero.
        operacoes=("ops_validas", lambda valores: valores.sum(min_count=1)),
        linhas_operacoes_invalidas=("ops_validas", lambda valores: valores.isna().sum()),
        linhas_operacoes_validas=("ops_validas", "count"),
    )
    g["inadimplencia"] = g["inadimplido"] / g["carteira"].where(g["carteira"] > 0) * 100

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
        g["carteira_por_ocupado"] = g["carteira"] / g["pop"].where(g["pop"] > 0)
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
    # Remover pares incompletos antes de ordenar evita alterar seus postos.
    pares = pd.concat([x.rename("x"), y.rename("y")], axis=1)
    pares = pares.replace([float("inf"), -float("inf")], float("nan")).dropna()
    if len(pares) < 2 or pares["x"].nunique() < 2 or pares["y"].nunique() < 2:
        return float("nan")
    return pares["x"].rank().corr(pares["y"].rank())


def participacao_ponderada(perfil, ufs, sexo, cores):
    # quantos % dos ocupados do conjunto de UFs sao do grupo escolhido. soma as
    # pessoas antes de dividir, entao UF grande pesa mais que UF pequena
    p = perfil[perfil["uf"].isin(ufs)]
    total = p["ocupados"].sum()
    if total == 0:
        return float("nan")
    grupo = p
    if sexo != "Todos":
        grupo = grupo[grupo["sexo"] == sexo]
    if cores:
        grupo = grupo[grupo["cor_raca"].isin(cores)]
    return grupo["ocupados"].sum() / total


def razao_alta_baixa(pontos, col_part="part_pct", col_valor="carteira_por_ocupado"):
    # compara a carteira por ocupado das UFs onde o grupo tem mais participacao
    # (acima da mediana) com as outras. da quantas vezes uma e da outra.
    # precisa de pelo menos 4 UFs, senao nao compara
    pontos = pontos.replace([float("inf"), -float("inf")], float("nan")).dropna(subset=[col_part, col_valor])
    if len(pontos) < 4:
        return None
    corte = pontos[col_part].median()
    alta = pontos[pontos[col_part] > corte][col_valor]
    baixa = pontos[pontos[col_part] <= corte][col_valor]
    if alta.empty or baixa.empty or not baixa.median():
        return None
    return alta.median() / baixa.median()


def filtrar_meses(df, inicio, fim):
    """Seleciona meses completos, independentemente do dia usado pela fonte."""
    inicio = pd.Period(inicio, freq="M")
    fim = pd.Period(fim, freq="M")
    if inicio > fim:
        raise ValueError("O mês inicial deve ser anterior ou igual ao final.")
    meses = pd.to_datetime(df["data_referencia"]).dt.to_period("M")
    return df.loc[meses.between(inicio, fim)].copy()


def intervalo_mensal_comum(*bases):
    """Interseção dos intervalos das fontes; não afirma que não há lacunas."""
    if not bases:
        return None
    limites = []
    for df in bases:
        meses = pd.to_datetime(df["data_referencia"]).dropna().dt.to_period("M")
        if meses.empty:
            return None
        limites.append((meses.min(), meses.max()))
    inicio = max(limite[0] for limite in limites)
    fim = min(limite[1] for limite in limites)
    return (inicio.to_timestamp(), fim.to_timestamp()) if inicio <= fim else None


def variacao_carteira_anual(df, referencia=None, chaves=("uf", "segmento", "modalidade")):
    """Variação de saldos em 12 meses somente com a mesma cobertura de células.

    ``df`` deve já conter os filtros de UF/segmento/modalidade, mas ainda ter o
    histórico anterior ao período da tela. Uma comparação com cobertura distinta
    é omitida, em vez de confundir entrada/saída de células com crescimento.
    """
    meses = pd.to_datetime(df["data_referencia"]).dt.to_period("M")
    mes = pd.Period(referencia, freq="M") if referencia is not None else meses.max()
    resultado = {
        "variacao_pct": None, "comparavel": False, "motivo": "Sem dados no período.",
        "referencia": mes.to_timestamp() if not pd.isna(mes) else pd.NaT,
        "referencia_anterior": (mes - 12).to_timestamp() if not pd.isna(mes) else pd.NaT,
        "carteira_atual": float("nan"), "carteira_anterior": float("nan"),
        "celulas_atual": 0, "celulas_anterior": 0,
    }
    if pd.isna(mes):
        return resultado
    atual = df.loc[meses == mes]
    anterior = df.loc[meses == mes - 12]
    cols = list(chaves)
    celulas_atual = set(atual[cols].itertuples(index=False, name=None))
    celulas_anterior = set(anterior[cols].itertuples(index=False, name=None))
    resultado.update(
        carteira_atual=atual["valor_carteira_ativa"].sum(min_count=1),
        carteira_anterior=anterior["valor_carteira_ativa"].sum(min_count=1),
        celulas_atual=len(celulas_atual), celulas_anterior=len(celulas_anterior),
    )
    if not celulas_atual or not celulas_anterior:
        resultado["motivo"] = "Não há dados nos dois meses da comparação."
    elif celulas_atual != celulas_anterior:
        resultado["motivo"] = "As UFs, segmentos ou modalidades disponíveis diferem entre os meses."
    elif atual["valor_carteira_ativa"].isna().any() or anterior["valor_carteira_ativa"].isna().any():
        resultado["motivo"] = "Há valores de carteira ausentes na comparação."
    elif not resultado["carteira_anterior"] > 0:
        resultado["motivo"] = "A carteira do mês de comparação não é positiva."
    else:
        resultado.update(
            comparavel=True, motivo="Mesmas UFs, segmentos e modalidades nos dois meses.",
            variacao_pct=(resultado["carteira_atual"] / resultado["carteira_anterior"] - 1) * 100,
        )
    return resultado


def carteira_media_anual_uf(df, ocupados, ano=2022):
    """Média dos 12 saldos mensais por UF, para cruzamento com o Censo.

    Não soma saldos ao longo do ano. Só apresenta a média e o valor por ocupado
    onde há os 12 meses; ``meses_disponiveis`` mantém visível a cobertura.
    """
    dados = filtrar_meses(df, f"{ano}-01", f"{ano}-12")
    dados["mes"] = pd.to_datetime(dados["data_referencia"]).dt.to_period("M")
    mensal = dados.groupby(["uf", "mes"], as_index=False)["valor_carteira_ativa"].sum(min_count=1)
    medias = mensal.groupby("uf", as_index=False).agg(
        carteira_media=("valor_carteira_ativa", "mean"),
        meses_disponiveis=("valor_carteira_ativa", "count"),
    )
    medias["ano"] = ano
    medias["cobertura_completa"] = medias["meses_disponiveis"] == 12
    medias["carteira_media"] = medias["carteira_media"].where(medias["cobertura_completa"])
    populacao = medias["uf"].map(ocupados)
    medias["carteira_por_ocupado"] = medias["carteira_media"] / populacao.where(populacao > 0)
    return medias


def rotulo_grupo(sexo, cores):
    # monta o nome do grupo no plural certo, tipo "Mulheres pretas e pardas"
    fem = {"Branca": "brancas", "Preta": "pretas", "Parda": "pardas", "Amarela": "amarelas", "Indígena": "indígenas"}
    masc = {"Branca": "brancos", "Preta": "pretos", "Parda": "pardos", "Amarela": "amarelos", "Indígena": "indígenas"}
    base = {"Mulheres": "Mulheres", "Homens": "Homens"}.get(sexo, "Pessoas")
    if not cores:
        return "Ocupados" if sexo == "Todos" else base
    # "pessoas" e "mulheres" pedem o feminino, so "homens" usa o masculino
    nomes = [(masc if sexo == "Homens" else fem)[c] for c in cores]
    texto = nomes[0] if len(nomes) == 1 else ", ".join(nomes[:-1]) + " e " + nomes[-1]
    return f"{base} {texto}"

