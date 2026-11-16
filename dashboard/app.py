# app.py
# Dashboard do projeto (Streamlit). Mostra o microcredito por UF, regiao,
# segmento e modalidade, e cruza com o perfil de sexo e raca do IBGE por UF
# pras ODS 5 e 18.
#
# os dados vem do banco da Aiven quando existe a variavel AIVEN_PG_URL (no
# terminal) ou o segredo AIVEN_PG_URL (no Streamlit Cloud). sem isso ele le os
# csvs do repositorio, assim da pra testar sem banco.
#
# uso: streamlit run dashboard/app.py

import os
import pandas as pd
import plotly.express as px
import streamlit as st

from contas import agregar, fmt_num, fmt_reais, participacao_grupo, spearman

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

METRICAS = {
    "Carteira ativa (R$)": "carteira",
    "Inadimplência (%)": "inadimplencia",
    "Operações (sem as negativas)": "operacoes",
    "Carteira por ocupado (R$)": "carteira_por_ocupado",
}

RESSALVA = (
    "Os dados de microcrédito do SCR.data são agregados por UF e não têm sexo, gênero, "
    "cor ou raça. O cruzamento com o IBGE descreve o território, não o perfil de quem "
    "pegou o crédito. Concluir algo sobre pessoas a partir de médias por estado é "
    "falácia ecológica."
)


# ler os dados

def pegar_url():
    url = os.environ.get("AIVEN_PG_URL")
    if not url:
        try:
            url = st.secrets["AIVEN_PG_URL"]
        except Exception:
            url = None
    return url


def consulta(conn, sql):
    cur = conn.cursor()
    cur.execute(sql)
    colunas = [c[0] for c in cur.description]
    return pd.DataFrame(cur.fetchall(), columns=colunas)


SQL_REGIONAL = """
    SELECT u.sigla_uf AS uf, u.regiao, m.segmento, m.nome_modalidade AS modalidade,
           f.data_referencia, f.valor_carteira_ativa, f.taxa_inadimplencia,
           f.quantidade_operacoes
    FROM fato_credito_regional f
    JOIN dim_uf u USING (uf_id)
    JOIN dim_modalidade m USING (modalidade_id)
"""

SQL_PERFIL = """
    SELECT u.sigla_uf AS uf, p.ano, p.sexo, p.cor_raca, p.ocupados
    FROM perfil_ocupados_uf p
    JOIN dim_uf u USING (uf_id)
"""

SQL_NACIONAL = """
    SELECT serie_id, descricao_serie, data_referencia, valor
    FROM fato_microcredito_nacional
"""


def csv_regional():
    df = pd.read_csv(os.path.join(BASE, "data", "processed", "fato_credito_regional.csv"))
    df["regiao"] = df["uf"].map(REGIAO)
    return df


def csv_perfil():
    return pd.read_csv(os.path.join(BASE, "data", "ibge_sexo_raca_uf_2022.csv"))


def csv_nacional():
    return pd.read_csv(os.path.join(BASE, "data", "processed", "fato_microcredito_nacional.csv"))


@st.cache_data(ttl=3600, show_spinner="carregando os dados...")
def carregar_dados(url):
    avisos = []
    fonte = "arquivos CSV do repositório"
    regional = perfil = nacional = None

    if url:
        try:
            import psycopg2
            conn = psycopg2.connect(url, connect_timeout=10)
            regional = consulta(conn, SQL_REGIONAL)
            nacional = consulta(conn, SQL_NACIONAL)
            fonte = "banco PostgreSQL (Aiven)"
            try:
                perfil = consulta(conn, SQL_PERFIL)
            except Exception:
                # a tabela de perfil pode ainda nao ter sido carregada
                conn.rollback()
                avisos.append("A tabela perfil_ocupados_uf ainda não está no banco, usei o CSV do IBGE.")
            conn.close()
        except Exception as erro:
            avisos.append(f"O banco não respondeu ({type(erro).__name__}), usei os CSVs do repositório.")
            regional = nacional = None

    if regional is None:
        regional, nacional = csv_regional(), csv_nacional()
    if perfil is None or perfil.empty:
        perfil = csv_perfil()

    regional["data_referencia"] = pd.to_datetime(regional["data_referencia"])
    nacional["data_referencia"] = pd.to_datetime(nacional["data_referencia"])
    for col in ["valor_carteira_ativa", "taxa_inadimplencia", "quantidade_operacoes"]:
        regional[col] = pd.to_numeric(regional[col])
    return {"regional": regional, "perfil": perfil, "nacional": nacional}, fonte, avisos


# ajuste dos graficos

def ajustar(fig):
    fig.update_layout(separators=",.", margin=dict(t=40, b=10, l=10, r=10), legend_title_text="")
    return fig


# tela

st.set_page_config(page_title="Microcrédito e inclusão financeira regional", layout="wide")
st.title("Microcrédito e inclusão financeira regional")
st.caption("Tema 05 · dados abertos do Banco Central (SCR.data e SGS) e do IBGE (Censo 2022)")

dados, fonte, avisos = carregar_dados(pegar_url())
regional, perfil, nacional = dados["regional"], dados["perfil"], dados["nacional"]
ocupados = perfil.groupby("uf")["ocupados"].sum().to_dict()

for aviso in avisos:
    st.warning(aviso)

# filtros
st.sidebar.header("Filtros")
st.sidebar.caption(f"Fonte dos dados: {fonte}")

anos = sorted(regional["data_referencia"].dt.year.unique())
ano_ini, ano_fim = st.sidebar.select_slider("Período (anos)", options=anos, value=(anos[0], anos[-1]))
regioes = st.sidebar.multiselect("Região", sorted(regional["regiao"].unique()), default=[])
ufs_possiveis = sorted(regional[regional["regiao"].isin(regioes)]["uf"].unique()) if regioes else sorted(regional["uf"].unique())
ufs = st.sidebar.multiselect("UF", ufs_possiveis, default=[])
segmentos = st.sidebar.multiselect("Segmento", sorted(regional["segmento"].unique()), default=[])
modalidades = st.sidebar.multiselect("Modalidade", sorted(regional["modalidade"].unique()), default=[])

st.sidebar.subheader("Perfil da UF (IBGE, 2022)")
sexo = st.sidebar.radio("Sexo", ["Todos", "Mulheres", "Homens"], index=1)
cores = st.sidebar.multiselect("Cor ou raça", ["Branca", "Preta", "Parda", "Amarela", "Indígena"],
                               default=["Preta", "Parda"])
minimo = st.sidebar.slider("Participação mínima do grupo na UF (%)", 0, 100, 0)

rotulo_grupo = (sexo if sexo != "Todos" else "Ocupados") + (" " + ", ".join(cores).lower() if cores else "")
part = participacao_grupo(perfil, sexo, cores)

# o que vem de fora do periodo (usado pra comparar com 12 meses antes)
base = regional.copy()
if regioes:
    base = base[base["regiao"].isin(regioes)]
if ufs:
    base = base[base["uf"].isin(ufs)]
if segmentos:
    base = base[base["segmento"].isin(segmentos)]
if modalidades:
    base = base[base["modalidade"].isin(modalidades)]
ufs_do_perfil = part[part["part_grupo"] * 100 >= minimo]["uf"]
base = base[base["uf"].isin(ufs_do_perfil)]

filtrado = base[(base["data_referencia"].dt.year >= ano_ini) & (base["data_referencia"].dt.year <= ano_fim)]

if filtrado.empty:
    st.error("Nenhum dado com esses filtros. Tire algum filtro para continuar.")
    st.stop()

metrica_nome = st.radio("Métrica analisada", list(METRICAS), horizontal=True)
metrica = METRICAS[metrica_nome]

# indicadores (kpis) do ultimo mes do periodo
ultimo = filtrado["data_referencia"].max()
agora = filtrado[filtrado["data_referencia"] == ultimo]
antes = base[base["data_referencia"].dt.to_period("M") == (ultimo.to_period("M") - 12)]

tot = agregar(agora.assign(tudo="Brasil"), ["tudo"], ocupados).iloc[0]
tot_antes = agregar(antes.assign(tudo="Brasil"), ["tudo"], ocupados).iloc[0] if not antes.empty else None
por_uf = agregar(agora, ["uf"], ocupados).sort_values("carteira", ascending=False)
pop_total = sum(ocupados[u] for u in agora["uf"].unique())
top3 = por_uf["carteira"].head(3).sum() / por_uf["carteira"].sum() * 100

c1, c2, c3, c4 = st.columns(4)
delta = None
if tot_antes is not None:
    delta = f"{(tot['carteira'] / tot_antes['carteira'] - 1) * 100:+.1f}% em 12 meses".replace(".", ",")
c1.metric(f"Carteira ativa em {ultimo:%m/%Y}", fmt_reais(tot["carteira"]), delta)
c2.metric("Inadimplência", fmt_num(tot["inadimplencia"], 1) + "%",
          help="Ponderada pela carteira: soma do valor inadimplente dividida pela soma da carteira.")
c3.metric("Carteira por ocupado", "R$ " + fmt_num(tot["carteira"] / pop_total),
          help="Carteira dividida pelos ocupados por conta própria e empregadores das UFs (Censo 2022).")
c4.metric("As 3 maiores UFs", fmt_num(top3, 1) + "% da carteira",
          help="Quanto da carteira está nas 3 UFs com maior saldo. Mostra a concentração.")

aba1, aba2, aba3, aba4 = st.tabs(["Evolução", "Ranking e detalhe", "ODS 5 e 18", "Dados"])

# ---- evolucao no tempo
with aba1:
    agrupar_por = st.selectbox("Agrupar por", ["Região", "UF", "Segmento (PF/PJ)", "Modalidade"])
    coluna = {"Região": "regiao", "UF": "uf", "Segmento (PF/PJ)": "segmento", "Modalidade": "modalidade"}[agrupar_por]
    serie = agregar(filtrado, ["data_referencia", coluna], ocupados)
    if serie[metrica].isna().all():
        st.info("Carteira por ocupado só existe quando o agrupamento é por região ou UF.")
    else:
        fig = px.line(serie, x="data_referencia", y=metrica, color=coluna,
                      labels={"data_referencia": "", metrica: metrica_nome})
        st.plotly_chart(ajustar(fig), width="stretch")
    if metrica == "carteira":
        st.caption("Carteira ativa é um saldo no fim de cada mês, não o valor concedido no mês.")
    if metrica == "operacoes":
        negativas = (filtrado["quantidade_operacoes"] < 0).sum()
        st.caption(f"{negativas} linhas com número de operações negativo ficaram de fora (o BCB não explica esse valor).")

    with st.expander("Séries nacionais do Banco Central (SGS)"):
        st.caption("Valores em milhões de reais, só pessoa física, crédito direcionado. "
                   "Não é o mesmo universo do recorte por UF.")
        fig = px.line(nacional, x="data_referencia", y="valor", color="descricao_serie",
                      labels={"data_referencia": "", "valor": "R$ milhões"})
        st.plotly_chart(ajustar(fig), width="stretch")

# ---- ranking e detalhe (drill-down)
with aba2:
    st.write(f"Posição em {ultimo:%m/%Y}. Escolha uma região para abrir as UFs e depois uma UF para abrir as modalidades.")
    regiao_sel = st.selectbox("Detalhar a região", ["(todas)"] + sorted(agora["regiao"].unique()))

    if regiao_sel == "(todas)":
        rank = agregar(agora, ["regiao"], ocupados).sort_values(metrica, ascending=False)
        fig = px.bar(rank, x="regiao", y=metrica, labels={"regiao": "", metrica: metrica_nome})
    else:
        rank = agregar(agora[agora["regiao"] == regiao_sel], ["uf"], ocupados).sort_values(metrica, ascending=False)
        fig = px.bar(rank, x="uf", y=metrica, labels={"uf": "", metrica: metrica_nome},
                     title=f"UFs da região {regiao_sel}")
    st.plotly_chart(ajustar(fig), width="stretch")

    if regiao_sel != "(todas)":
        uf_sel = st.selectbox("Detalhar a UF", ["(nenhuma)"] + list(rank["uf"]))
        if uf_sel != "(nenhuma)":
            det = agregar(filtrado[filtrado["uf"] == uf_sel], ["uf", "data_referencia", "modalidade", "segmento"], ocupados)
            det["grupo"] = det["modalidade"] + " · " + det["segmento"]
            fig = px.line(det, x="data_referencia", y=metrica, color="grupo",
                          labels={"data_referencia": "", metrica: metrica_nome}, title=f"{uf_sel} por modalidade e segmento")
            st.plotly_chart(ajustar(fig), width="stretch")

# ---- ods 5 e 18
with aba3:
    st.warning(RESSALVA)
    pontos = agregar(agora, ["uf"], ocupados).merge(part, on="uf")
    pontos["regiao"] = pontos["uf"].map(REGIAO)
    pontos["part_pct"] = pontos["part_grupo"] * 100
    if len(pontos) < 3:
        st.info("Poucas UFs com esses filtros para comparar.")
    else:
        # carteira e operacoes seguem o tamanho da UF, entao aqui uso a carteira
        # por ocupado. a inadimplencia ja e uma taxa e fica como esta
        if metrica == "inadimplencia":
            y, y_nome = "inadimplencia", "Inadimplência (%)"
        else:
            y, y_nome = "carteira_por_ocupado", "Carteira por ocupado (R$)"
        fig = px.scatter(pontos, x="part_pct", y=y, color="regiao", text="uf", log_y=(y != "inadimplencia"),
                         labels={"part_pct": "Participação do grupo entre os ocupados da UF (%)", y: y_nome})
        fig.update_traces(textposition="top center")
        st.plotly_chart(ajustar(fig), width="stretch")
        rho = spearman(pontos["part_pct"], pontos[y])
        st.write(f"Grupo escolhido: **{rotulo_grupo}**. Correlação de Spearman entre a participação do grupo "
                 f"e {y_nome.lower()}: **{fmt_num(rho, 2)}** com {len(pontos)} UFs.")
        sem_ne = pontos[pontos["regiao"] != "Nordeste"]
        if len(sem_ne) >= 3 and len(sem_ne) < len(pontos):
            st.write(f"Sem as UFs do Nordeste: **{fmt_num(spearman(sem_ne['part_pct'], sem_ne[y]), 2)}** "
                     f"com {len(sem_ne)} UFs. O Nordeste tem a maior parte da carteira do país e muda bastante o resultado.")
        st.caption("Perfil: pessoas de 14 anos ou mais ocupadas como empregador ou conta própria, Censo 2022 (IBGE). "
                   "Correlação não é causa, e com poucas UFs um estado atípico muda o resultado.")

# ---- dados
with aba4:
    st.write(f"{len(filtrado)} linhas com os filtros atuais.")
    tabela = filtrado.sort_values(["data_referencia", "uf"])
    st.dataframe(tabela, width="stretch", hide_index=True)
    st.download_button("Baixar em CSV", tabela.to_csv(index=False).encode("utf-8"),
                       file_name="microcredito_filtrado.csv", mime="text/csv")
