"""Painel de microcrédito: saldos mensais e contexto territorial das ODS."""
import math
import os

import pandas as pd
import plotly.express as px
import streamlit as st

from contas import (
    agregar, carteira_media_anual_uf, filtrar_meses, fmt_num, fmt_reais,
    participacao_grupo, participacao_ponderada, razao_alta_baixa,
    rotulo_grupo, spearman, variacao_carteira_anual,
)
from dados import REGIAO, carregar_dados

st.set_page_config(page_title="Microcrédito no Brasil", page_icon="📊", layout="wide")
CORES = {"Nordeste": "#187a70", "Norte": "#6993b8", "Sudeste": "#263e68", "Sul": "#b47c32", "Centro-Oeste": "#9b7aa8"}
METRICAS = {"Carteira ativa": ("carteira", "R$"), "Inadimplência": ("inadimplencia", "%"), "Carteira por ocupado": ("carteira_por_ocupado", "R$ por ocupado")}
RESSALVA = (
    "Os dados de microcrédito do SCR.data são agregados por UF e não têm sexo, gênero, "
    "cor ou raça. O cruzamento com o IBGE descreve o território, não o perfil de quem "
    "pegou o crédito. Concluir algo sobre pessoas a partir de médias por estado é falácia ecológica."
)
st.markdown("""<style>
.block-container {max-width: 1440px; padding-top: 2.3rem; padding-bottom: 3rem;}
h1 {letter-spacing: -.045em; font-weight: 700 !important;}
h2,h3 {letter-spacing: -.02em;}
[data-testid="stMetric"] {border: 1px solid #dce3e9; border-radius: 8px; padding: 1rem 1.1rem; background: #fff; min-height: 128px;}
[data-testid="stMetricLabel"] {color: #475569;}
[data-testid="stMetricValue"] {font-size: 1.8rem; color: #183449;}
[data-testid="stSidebar"] {border-right: 1px solid #dce3e9;}
[data-baseweb="tab-list"] {gap: 1.6rem; border-bottom: 1px solid #dce3e9;}
[data-baseweb="tab"] {font-size: 1rem;}
</style>""", unsafe_allow_html=True)


def numero(valor, casas=1, sufixo=""):
    return fmt_num(valor, casas) + sufixo if pd.notna(valor) and math.isfinite(float(valor)) else "Indisponível"


def reais(valor):
    return fmt_reais(valor) if pd.notna(valor) and math.isfinite(float(valor)) else "Indisponível"


def grafico(fig, altura=380):
    fig.update_layout(template="plotly_white", height=altura, separators=",.",
                      margin=dict(t=18, b=25, l=5, r=15), font=dict(family="Arial", size=14, color="#334155"),
                      legend_title_text="", legend=dict(orientation="h", y=1.12, x=0),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#edf0f4", zeroline=False)
    return fig


def escopo(df, regioes, ufs, segmentos, modalidades):
    d = df.copy()
    for col, valores in [("regiao", regioes), ("uf", ufs), ("segmento", segmentos), ("modalidade", modalidades)]:
        if valores:
            d = d[d[col].isin(valores)]
    return d


def url_banco():
    if os.environ.get("AIVEN_PG_URL"):
        return os.environ["AIVEN_PG_URL"]
    try:
        return st.secrets.get("AIVEN_PG_URL")
    except (FileNotFoundError, KeyError):
        return None


@st.cache_data(ttl=3600, show_spinner="Lendo as bases do projeto…")
def dados_painel(url):
    return carregar_dados(url)


try:
    dados, fonte, avisos = dados_painel(url_banco())
except (ValueError, OSError):
    st.error("Não foi possível carregar as bases. Confira os CSVs em data/processed e o perfil do IBGE em data/.")
    st.stop()
regional, nacional, perfil = dados["regional"], dados["nacional"], dados["perfil"]
ocupados = perfil.groupby("uf")["ocupados"].sum().to_dict()

st.caption("BIG DATA & ANALYTICS  /  TEMA 05")
st.title("Microcrédito no Brasil")
st.write("Evolução da carteira, diferenças entre estados e contexto territorial de gênero e raça.")
for aviso in avisos:
    st.warning(aviso)

with st.sidebar:
    st.header("Recorte da análise")
    meses = sorted(regional["data_referencia"].dt.strftime("%Y-%m").unique())
    inicio, fim = st.select_slider("Período mensal", options=meses, value=(meses[0], meses[-1]),
                                  format_func=lambda m: f"{m[5:]}/{m[:4]}")
    regioes = st.multiselect("Região", list(CORES))
    possiveis = sorted(regional.loc[regional["regiao"].isin(regioes), "uf"].unique()) if regioes else sorted(regional["uf"].unique())
    ufs = st.multiselect("Estado (UF)", possiveis)
    segmentos = st.multiselect("Tipo de cliente", ["PF", "PJ"], help="PF: pessoa física. PJ: pessoa jurídica.")
    modalidades = st.multiselect("Modalidade", sorted(regional["modalidade"].unique()))
    st.caption("Seleção vazia inclui todas as opções. Os filtros territoriais também se aplicam à seção ODS; o período ODS é fixo em 2022.")
    st.divider()
    st.caption(f"Fonte carregada: {fonte}")
    st.caption(f"SCR: {regional.data_referencia.min():%m/%Y}–{regional.data_referencia.max():%m/%Y} · SGS: {nacional.data_referencia.min():%m/%Y}–{nacional.data_referencia.max():%m/%Y} · IBGE: Censo 2022")
    if st.button("Atualizar leitura", use_container_width=True):
        dados_painel.clear()
        st.rerun()

base = escopo(regional, regioes, ufs, segmentos, modalidades)
filtrado = filtrar_meses(base, inicio, fim)
if filtrado.empty:
    st.info("Não há registros neste recorte. Amplie o período ou remova algum filtro.")
    st.stop()
ultimo = filtrado["data_referencia"].max()
agora = filtrado[filtrado["data_referencia"] == ultimo]
total = agregar(agora.assign(total="Recorte"), ["total"], ocupados).iloc[0]
por_uf = agregar(agora, ["uf"], ocupados).sort_values("carteira", ascending=False)
pop = sum(ocupados[u] for u in agora["uf"].unique())
yoy = variacao_carteira_anual(base, ultimo)
delta = numero(yoy["variacao_pct"], 1, "% em 12 meses") if yoy["comparavel"] else None
st.caption(f"{len(por_uf)} UFs no recorte · Indicadores de {ultimo:%m/%Y} · Série de {inicio[5:]}/{inicio[:4]} a {fim[5:]}/{fim[:4]}")

panorama, evolucao, ods, fontes = st.tabs(["Panorama", "Evolução e estados", "Contexto ODS", "Fontes e dados"])

with panorama:
    a, b, c, d = st.columns(4)
    a.metric("Carteira ativa", reais(total["carteira"]), delta, delta_color="off",
             help="Saldo no fim do mês. A unidade em reais é uma hipótese documentada pelo projeto.")
    b.metric("Inadimplência ponderada", numero(total["inadimplencia"], 2, "%"),
             help="Ponderação pela carteira. Aproximação a partir de taxas já arredondadas na base tratada.")
    c.metric("Carteira por ocupado", reais(total["carteira"] / pop) if pop else "Indisponível",
             help="Saldo atual / ocupados por conta própria ou empregadores do Censo 2022. Não é valor recebido por pessoa.")
    d.metric("Concentração nas 3 maiores UFs", numero(por_uf["carteira"].head(3).sum() / total["carteira"] * 100, 1, "%"))
    if not yoy["comparavel"]:
        st.caption("Variação anual indisponível: " + yoy["motivo"])
    st.caption("Carteira ativa é saldo, não concessão mensal. Valores regionais tratados como reais por inferência; denominador populacional fixo no Censo 2022.")
    st.divider()
    left, right = st.columns([1.3, 1])
    with left:
        st.subheader("Onde está a carteira")
        rank = por_uf.head(10).sort_values("carteira")
        fig = px.bar(rank, x="carteira", y="uf", orientation="h", labels={"carteira": "Carteira ativa (R$)", "uf": "UF"}, color_discrete_sequence=["#187a70"])
        fig.update_xaxes(title="Carteira ativa (R$)")
        st.plotly_chart(grafico(fig, 410), width="stretch")
        st.caption(f"Até 10 maiores UFs entre as selecionadas · {ultimo:%m/%Y}")
    with right:
        st.subheader("Distribuição regional")
        reg = agregar(agora, ["regiao"], ocupados).sort_values("carteira", ascending=False)
        reg["Participação (%)"] = reg["carteira"] / reg["carteira"].sum() * 100
        fig = px.bar(reg, x="regiao", y="Participação (%)", color="regiao", color_discrete_map=CORES, text_auto=".1f")
        fig.update_layout(showlegend=False)
        st.plotly_chart(grafico(fig, 410), width="stretch")
        lider = reg.iloc[0]
        st.caption(f"{lider['regiao']}: {numero(lider['Participação (%)'], 1, '%')} da carteira do recorte selecionado.")
    st.info("A análise de gênero e raça está em Contexto ODS. Ela compara características dos estados e não identifica quem recebeu o crédito.")

with evolucao:
    st.subheader("Evolução do microcrédito")
    l, r = st.columns([2, 1])
    metrica_nome = l.radio("Métrica", list(METRICAS), horizontal=True)
    metrica, unidade = METRICAS[metrica_nome]
    agrupamentos = {"Região": "regiao", "UF": "uf"}
    if metrica != "carteira_por_ocupado":
        agrupamentos.update({"Tipo de cliente": "segmento", "Modalidade": "modalidade"})
    escolha = r.selectbox("Comparar por", list(agrupamentos))
    coluna = agrupamentos[escolha]
    serie = agregar(filtrado, ["data_referencia", coluna], ocupados)
    fig = px.line(serie, x="data_referencia", y=metrica, color=coluna, color_discrete_map=CORES,
                  labels={metrica: f"{metrica_nome} ({unidade})", "data_referencia": "Mês"})
    st.plotly_chart(grafico(fig), width="stretch")
    st.caption("Ausência de registro não significa zero. Carteira por ocupado utiliza o denominador fixo do Censo 2022.")
    st.subheader(f"Detalhamento em {ultimo:%m/%Y}")
    regiao = st.selectbox("Abrir região", ["Todas"] + sorted(agora["regiao"].unique()))
    detalhe = agora if regiao == "Todas" else agora[agora["regiao"] == regiao]
    ranking = agregar(detalhe, ["uf"], ocupados).sort_values(metrica, ascending=False)
    fig = px.bar(ranking, x="uf", y=metrica, labels={metrica: f"{metrica_nome} ({unidade})"}, color_discrete_sequence=["#263e68"])
    st.plotly_chart(grafico(fig, 300), width="stretch")
    uf = st.selectbox("Abrir modalidades de uma UF", ["Selecione"] + sorted(detalhe["uf"].unique()))
    if uf != "Selecione":
        det = agregar(filtrado[filtrado["uf"] == uf], ["data_referencia", "uf", "modalidade", "segmento"], ocupados)
        det["Modalidade / cliente"] = det["modalidade"] + " · " + det["segmento"]
        st.plotly_chart(grafico(px.line(det, x="data_referencia", y=metrica, color="Modalidade / cliente",
                                       labels={metrica: f"{metrica_nome} ({unidade})"})), width="stretch")
    with st.expander("Contexto nacional · séries SGS"):
        st.caption("Mesmo período mensal selecionado. Filtros de UF, região, PF/PJ e modalidade não se aplicam às séries nacionais. Somente PF e recursos direcionados; universo diferente do SCR regional.")
        n = filtrar_meses(nacional, inicio, fim)
        for sid, titulo in [(20618, "Saldo da carteira · microempreendedores"), (20712, "Concessões mensais · microcrédito total")]:
            st.write(f"**{titulo}**")
            s = n[n["serie_id"] == sid].sort_values("data_referencia")
            if s.empty:
                st.info("Série sem dados neste período.")
            else:
                st.plotly_chart(grafico(px.line(s, x="data_referencia", y="valor", labels={"valor": "R$ milhões"},
                                               color_discrete_sequence=["#187a70"]), 240), width="stretch")
        st.caption(f"A base SGS vai até {nacional.data_referencia.max():%m/%Y}; o regional vai até {regional.data_referencia.max():%m/%Y}. As séries completas podem ser baixadas em Fontes e dados.")

with ods:
    st.subheader("Gênero, raça e distribuição territorial")
    st.write("ODS 5 · Igualdade de gênero  /  ODS 18 · Igualdade étnico-racial (iniciativa brasileira)")
    st.info(RESSALVA)
    st.caption("Referência fixa: 2022. Carteira média dos saldos mensais de 2022 e perfil do Censo do mesmo ano. Filtros de território, cliente e modalidade são preservados; o período mensal da lateral não altera esta seção.")
    c1, c2 = st.columns([1, 2])
    sexo = c1.selectbox("Sexo no perfil territorial", ["Mulheres", "Homens", "Todos"])
    cores = c2.multiselect("Cor ou raça no perfil territorial", ["Branca", "Preta", "Parda", "Amarela", "Indígena"], default=["Preta", "Parda"])
    minimo = st.slider("Participação mínima do grupo na UF (%)", 0, 100, 0)
    st.caption("Nenhuma cor/raça selecionada inclui todas. Não há faixa etária na base preparada: o universo é de ocupados com 14 anos ou mais, por conta própria ou empregadores.")
    grupo = rotulo_grupo(sexo, cores)
    part = participacao_grupo(perfil, sexo, cores)
    anual = carteira_media_anual_uf(base, ocupados, 2022)
    pontos = anual.merge(part, on="uf")
    pontos["part_pct"] = pontos["part_grupo"] * 100
    pontos = pontos[pontos["cobertura_completa"] & (pontos["part_pct"] >= minimo)].copy()
    pontos["regiao"] = pontos["uf"].map(REGIAO)
    if pontos.empty:
        st.info("Nenhuma UF tem dados completos de 2022 para este recorte. Amplie os filtros territoriais ou de modalidade.")
    else:
        mediana = pontos["part_pct"].median()
        alta = pontos.loc[pontos["part_pct"] > mediana, "carteira_por_ocupado"]
        baixa = pontos.loc[pontos["part_pct"] <= mediana, "carteira_por_ocupado"]
        razao = razao_alta_baixa(pontos)
        p = participacao_ponderada(perfil, pontos["uf"].unique(), sexo, cores)
        st.write(f"**{grupo}** · {len(pontos)} UFs comparáveis")
        a, b, c, d = st.columns(4)
        a.metric("Participação do grupo", numero(p * 100, 1, "%"), help="Participação entre os ocupados do conjunto de UFs, ponderada pela população ocupada.")
        b.metric("Carteira/ocupado · maior presença", reais(alta.median()), help="Mediana da carteira por ocupado nas UFs acima da mediana de participação do grupo.")
        c.metric("Carteira/ocupado · menor presença", reais(baixa.median()), help="Mediana da carteira por ocupado nas demais UFs.")
        d.metric("Razão maior / menor presença", numero(razao, 2, "×") if razao is not None else "Indisponível", help="Compara as duas medianas. Exige ao menos quatro UFs e grupos válidos; não mede crédito recebido pelo grupo.")
        st.caption(f"Corte entre grupos de UFs: {numero(mediana, 1, '%')} de participação. Não são valores destinados às pessoas do grupo.")
        fig = px.scatter(pontos, x="part_pct", y="carteira_por_ocupado", color="regiao", color_discrete_map=CORES,
                         text="uf", hover_data={"carteira_media": ":.2f", "regiao": True},
                         labels={"part_pct": "Participação do grupo entre os ocupados (%)", "carteira_por_ocupado": "Carteira média por ocupado (R$)"})
        fig.update_traces(textposition="top center", marker_size=11)
        fig.update_xaxes(title="Participação do grupo entre os ocupados (%)")
        st.plotly_chart(grafico(fig, 440), width="stretch")
        rho = spearman(pontos["part_pct"], pontos["carteira_por_ocupado"])
        if pd.isna(rho):
            st.caption("Correlação não calculável: são necessárias UFs suficientes e variação nos dois indicadores.")
        else:
            st.write(f"Correlação de Spearman: **{numero(rho, 2)}** · {len(pontos)} UFs.")
        sem_ne = pontos[pontos["regiao"] != "Nordeste"]
        if len(sem_ne) >= 3 and len(sem_ne) < len(pontos):
            st.caption(f"Análise de sensibilidade sem Nordeste: {numero(spearman(sem_ne['part_pct'], sem_ne['carteira_por_ocupado']), 2)} · {len(sem_ne)} UFs. Compare a estabilidade da associação ao retirar essa região.")
        st.caption("Correlação não implica causalidade. O denominador inclui pessoas ocupadas, enquanto a carteira pode incluir PF e PJ. UFs sem os 12 meses completos são excluídas desta comparação.")
        st.download_button("Baixar comparação ODS", pontos.to_csv(index=False).encode("utf-8"), "microcredito_ods_2022.csv", "text/csv")

with fontes:
    st.subheader("Dados abertos, leitura transparente")
    st.write(f"Fonte utilizada nesta sessão: **{fonte}**.")
    st.dataframe(pd.DataFrame([
        {"Base": "SCR.data / BCB", "Registros": len(regional), "Referência": f"{regional.data_referencia.min():%m/%Y}–{regional.data_referencia.max():%m/%Y}", "O que descreve": "Saldos por UF, cliente e modalidade"},
        {"Base": "SGS / BCB", "Registros": len(nacional), "Referência": f"{nacional.data_referencia.min():%m/%Y}–{nacional.data_referencia.max():%m/%Y}", "O que descreve": "Saldo e concessões nacionais, em R$ milhões"},
        {"Base": "IBGE / Censo 2022", "Registros": len(perfil), "Referência": "2022", "O que descreve": "Perfil dos ocupados por UF, sexo e cor/raça"},
    ]), hide_index=True, width="stretch")
    negativas = int((regional["quantidade_operacoes"] < 0).sum())
    st.warning(f"Quantidade de operações: {fmt_num(negativas)} registros negativos na base regional. O significado não foi confirmado; esse campo fica disponível na tabela original, mas não é usado como KPI nem como métrica dos gráficos.")
    st.markdown("""**Como interpretar**
- Carteira ativa é saldo ao fim do mês; análises anuais usam média dos saldos, não soma.
- Inadimplência é ponderada pela carteira e aproximada a partir das taxas arredondadas no ETL.
- A unidade monetária do SCR é tratada como reais por inferência do projeto; SGS informa milhões de reais.
- Meses ou combinações ausentes não são preenchidos como zero.
- O IBGE descreve o território em 2022; não revela sexo ou raça de tomadores de crédito.
- A base preparada não permite filtros por idade nem conclusões individuais de acesso ao crédito.
""")
    st.markdown("[Banco Central · SCR.data](https://www.bcb.gov.br/estabilidadefinanceira/scrdata) · [IBGE · tabela 10261](https://sidra.ibge.gov.br/tabela/10261) · [Dicionário e metodologia do projeto](https://github.com/ViniciusLgo/bigdata-microcredito-project/tree/main/docs)")
    st.subheader("Registros do recorte selecionado")
    st.caption(f"{fmt_num(len(filtrado))} registros · CSV mantém as colunas e valores originais tratados.")
    tabela = filtrado.sort_values(["data_referencia", "uf", "segmento", "modalidade"])
    st.dataframe(tabela, hide_index=True, width="stretch", height=320)
    a, b = st.columns(2)
    a.download_button("Baixar dados do recorte", tabela.to_csv(index=False).encode("utf-8"), "microcredito_recorte.csv", "text/csv")
    b.download_button("Baixar séries nacionais completas", nacional.to_csv(index=False).encode("utf-8"), "microcredito_sgs.csv", "text/csv")

st.divider()
st.caption("Projeto acadêmico · UCSal · Big Data & Analytics · Fontes públicas: Banco Central e IBGE")
