# app.py
# Versao simples do dashboard: uma pagina que conta uma historia, de cima pra
# baixo. Cada secao e uma pergunta, tem um grafico e uma frase explicando
# o que esta sendo comparado.
#
# uso: streamlit run dashboard/app.py

import pandas as pd
import plotly.express as px
import streamlit as st

from contas import agregar, fmt_num, fmt_reais, participacao_grupo, razao_alta_baixa
from dados import REGIAO, carregar_dados, pegar_url

LARANJA = "#E8710A"   # destaque do Nordeste
AZUL = "#4C78A8"      # as outras regioes

# os grupos que da pra comparar. cada um e (sexo, cores)
GRUPOS = {
    "Mulheres pretas e pardas": ("Mulheres", ["Preta", "Parda"]),
    "Mulheres": ("Mulheres", []),
    "Pessoas pretas e pardas": ("Todos", ["Preta", "Parda"]),
}


def ajustar(fig, altura=380):
    fig.update_layout(separators=",.", height=altura, margin=dict(t=20, b=10, l=10, r=10),
                      legend_title_text="", plot_bgcolor="white")
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#E5E7EB")
    return fig


st.set_page_config(page_title="Microcrédito no Brasil", layout="wide")

dados, fonte, avisos = carregar_dados(pegar_url())
regional, perfil = dados["regional"], dados["perfil"]
ocupados = perfil.groupby("uf")["ocupados"].sum().to_dict()
for aviso in avisos:
    st.warning(aviso)

# ---------------------------------------------------------------- topo
st.title("Onde está o microcrédito no Brasil?")
st.write(
    "Mostramos quanto há de microcrédito em cada estado e se isso tem relação com o perfil de "
    "quem trabalha por conta própria. Os dados são do Banco Central e do IBGE."
)

# filtros, todos juntos aqui em cima
anos = sorted(regional["data_referencia"].dt.year.unique())
todas_regioes = sorted(regional["regiao"].unique())
f1, f2, f3 = st.columns([1, 2, 2])
ano = f1.selectbox("Ano", anos, index=len(anos) - 1)
regioes = f2.multiselect("Região", todas_regioes, default=todas_regioes)
tipo = f3.radio("Tipo de cliente", ["Pessoa física e jurídica", "Só pessoa física", "Só pessoa jurídica"],
                horizontal=True)
with st.expander("Mais filtros"):
    g1, g2 = st.columns(2)
    modalidades = g1.multiselect("Modalidade", sorted(regional["modalidade"].unique()),
                                 default=sorted(regional["modalidade"].unique()))
    ufs_possiveis = sorted(regional[regional["regiao"].isin(regioes)]["uf"].unique())
    ufs = g2.multiselect("Só estes estados (vazio = todos)", ufs_possiveis)

tipos = {"Pessoa física e jurídica": ["PF", "PJ"], "Só pessoa física": ["PF"], "Só pessoa jurídica": ["PJ"]}[tipo]
base_geral = regional[regional["segmento"].isin(tipos) & regional["modalidade"].isin(modalidades)]
base = base_geral[base_geral["regiao"].isin(regioes)]
if ufs:
    base = base[base["uf"].isin(ufs)]

noano = base[base["data_referencia"].dt.year == ano]
if noano.empty:
    st.error("Não há dados com esses filtros. Escolha mais regiões ou modalidades.")
    st.stop()

# o mes que vale e o ultimo do ano escolhido (dezembro, ou o ultimo que existe)
mes = noano["data_referencia"].max()
agora = base[base["data_referencia"] == mes]
antes = base[base["data_referencia"].dt.to_period("M") == (mes.to_period("M") - 12)]

# ---------------------------------------------------------------- 1. numeros
st.header("1. Os números principais")
tot = agregar(agora.assign(tudo="x"), ["tudo"], ocupados).iloc[0]
tot_antes = agregar(antes.assign(tudo="x"), ["tudo"], ocupados).iloc[0] if not antes.empty else None
parte_ne = agora[agora["regiao"] == "Nordeste"]["valor_carteira_ativa"].sum() / agora["valor_carteira_ativa"].sum()

k1, k2, k3, k4 = st.columns(4)
k1.metric(f"Saldo em {mes:%m/%Y}", fmt_reais(tot["carteira"]))
k1.caption("Quanto os clientes ainda devem de microcrédito.")
if tot_antes is not None:
    k2.metric("Mudança em 12 meses", f"{(tot['carteira'] / tot_antes['carteira'] - 1) * 100:+.1f}%".replace(".", ","))
else:
    k2.metric("Mudança em 12 meses", "sem dado")
k2.caption("Comparado com o mesmo mês do ano anterior.")
k3.metric("Inadimplência", fmt_num(tot["inadimplencia"], 1) + "%")
k3.caption("Parte do saldo com parcela atrasada há mais de 90 dias.")
k4.metric("Parte no Nordeste", fmt_num(parte_ne * 100, 0) + "%")
k4.caption("Quanto do saldo está nos 9 estados do Nordeste.")

# ---------------------------------------------------------------- 2. tempo
st.header("2. Como o saldo mudou desde 2021?")
ver = st.radio("Mostrar", ["Brasil todo", "Por região"], horizontal=True)
if ver == "Brasil todo":
    serie = agregar(base, ["data_referencia"], ocupados)
    fig = px.line(serie, x="data_referencia", y=serie["carteira"] / 1e9,
                  labels={"data_referencia": "", "y": "Saldo (R$ bilhões)"})
    fig.update_traces(line_color=AZUL, line_width=3)
else:
    serie = agregar(base, ["data_referencia", "regiao"], ocupados)
    fig = px.line(serie, x="data_referencia", y=serie["carteira"] / 1e9, color="regiao",
                  labels={"data_referencia": "", "y": "Saldo (R$ bilhões)"})
    fig.update_traces(line_width=3)
st.plotly_chart(ajustar(fig), width="stretch")
st.caption("Cada ponto é o saldo de microcrédito no fim do mês, em bilhões de reais.")

# ---------------------------------------------------------------- 3. estados
st.header("3. Em quais estados está o microcrédito?")
comparar = st.radio(
    "O que comparar",
    ["Total do estado", "Por pessoa que trabalha por conta própria"],
    horizontal=True,
)
if comparar == "Total do estado":
    st.write("Quanto cada estado tem de saldo de microcrédito, em milhões de reais.")
    coluna, rotulo = "carteira", "Saldo (R$ milhões)"
else:
    st.write("Dividimos o saldo pelo número de pessoas que trabalham por conta própria ou como empregador. "
             "Assim dá para comparar estados grandes e pequenos.")
    coluna, rotulo = "carteira_por_ocupado", "Saldo por pessoa (R$)"

por_uf = agregar(agora, ["uf"], ocupados).sort_values(coluna)
por_uf["regiao"] = por_uf["uf"].map(REGIAO)
por_uf["grupo"] = por_uf["regiao"].map(lambda r: "Nordeste" if r == "Nordeste" else "Outras regiões")
por_uf["texto"] = por_uf[coluna].map(fmt_reais if coluna == "carteira" else lambda v: "R$ " + fmt_num(v))
por_uf["x"] = por_uf[coluna] / 1e6 if coluna == "carteira" else por_uf[coluna]
fig = px.bar(por_uf, x="x", y="uf", orientation="h", color="grupo", text="texto",
             color_discrete_map={"Nordeste": LARANJA, "Outras regiões": AZUL},
             labels={"x": rotulo, "uf": ""})
fig.update_traces(textposition="outside", cliponaxis=False)
fig.update_yaxes(dtick=1)
st.plotly_chart(ajustar(fig, altura=max(380, 24 * len(por_uf) + 60)), width="stretch")
st.caption(f"Posição em {mes:%m/%Y}. Os estados do Nordeste aparecem em laranja.")

st.subheader("Ver um estado com mais detalhe")
uf_sel = st.selectbox("Estado", sorted(agora["uf"].unique()))
det = agregar(base[base["uf"] == uf_sel], ["data_referencia", "modalidade", "segmento"], ocupados)
det["linha"] = det["modalidade"].str.replace(" - Microcrédito", "", regex=False) + ", " + det["segmento"]
fig = px.line(det, x="data_referencia", y=det["carteira"] / 1e6, color="linha",
              labels={"data_referencia": "", "y": "Saldo (R$ milhões)"})
fig.update_traces(line_width=3)
st.plotly_chart(ajustar(fig, altura=340), width="stretch")
st.caption(f"Saldo de {uf_sel} por tipo de crédito (empréstimo ou financiamento) e por tipo de cliente (PF ou PJ).")

# ---------------------------------------------------------------- 4. genero e raca
st.header("4. Gênero e raça: existe relação com o microcrédito?")
st.info(
    "A base do Banco Central não diz o sexo nem a cor de quem pegou o crédito. Por isso a comparação é "
    "entre estados, e não entre pessoas. Esta parte usa todos os estados, não só os filtrados acima."
)
nome_grupo = st.selectbox("Qual grupo você quer comparar?", list(GRUPOS))
sexo, cores = GRUPOS[nome_grupo]
minusculo = nome_grupo[0].lower() + nome_grupo[1:]

part = participacao_grupo(perfil, sexo, cores)
snap = base_geral[base_geral["data_referencia"] == mes]
pontos = agregar(snap, ["uf"], ocupados).merge(part, on="uf")
pontos["regiao"] = pontos["uf"].map(REGIAO)
pontos["part_pct"] = pontos["part_grupo"] * 100

st.write(
    f"**Como foi feita a comparação:** separamos os 27 estados em dois grupos de tamanho parecido. "
    f"Um com mais {minusculo} entre quem trabalha por conta própria ou como empregador, e outro com menos. "
    "Depois vimos quanto de microcrédito cada grupo tem por pessoa (valor do meio de cada grupo)."
)


def comparar_grupos(df):
    corte = df["part_pct"].median()
    mais = df[df["part_pct"] > corte]["carteira_por_ocupado"].median()
    menos = df[df["part_pct"] <= corte]["carteira_por_ocupado"].median()
    tabela = pd.DataFrame({
        "grupo": [f"Estados com menos {minusculo}", f"Estados com mais {minusculo}"],
        "valor": [menos, mais],
    })
    tabela["texto"] = tabela["valor"].map(lambda v: "R$ " + fmt_num(v))
    return tabela


def grafico_grupos(df, cor):
    fig = px.bar(comparar_grupos(df), x="grupo", y="valor", text="texto",
                 labels={"grupo": "", "valor": "Saldo por pessoa (R$)"})
    fig.update_traces(marker_color=cor, textposition="outside", cliponaxis=False)
    fig.update_yaxes(rangemode="tozero")
    return ajustar(fig, altura=340)


sem_ne = pontos[pontos["regiao"] != "Nordeste"]
razao_todos = razao_alta_baixa(pontos)
razao_sem = razao_alta_baixa(sem_ne)

c1, c2 = st.columns(2)
with c1:
    st.subheader("Todos os estados")
    st.plotly_chart(grafico_grupos(pontos, AZUL), width="stretch")
    if razao_todos:
        st.write(f"Os estados com mais {minusculo} têm **{fmt_num(razao_todos, 1)} vezes** o microcrédito por pessoa dos estados com menos.")
with c2:
    st.subheader("Sem os estados do Nordeste")
    if len(sem_ne) >= 4:
        st.plotly_chart(grafico_grupos(sem_ne, LARANJA), width="stretch")
        if razao_sem and 0.8 <= razao_sem <= 1.25:
            st.write("Sem o Nordeste, os dois grupos ficam **quase iguais**. A diferença some.")
        elif razao_sem:
            st.write(f"Sem o Nordeste, os estados com mais {minusculo} têm **{fmt_num(razao_sem, 1)} vezes** o microcrédito por pessoa dos estados com menos.")
    else:
        st.write("Estados demais ficaram de fora para comparar.")

st.warning(
    "Como ler: o Nordeste concentra a maior parte do microcrédito do país e tem muitas pessoas pretas e "
    "pardas. Por isso ele puxa a diferença. O resultado mostra onde o microcrédito está, e não quem tem acesso a ele."
)

st.caption(f"Fonte dos dados: {fonte}. Banco Central (SCR.data, microcrédito) e IBGE (Censo 2022, tabela 10261).")
