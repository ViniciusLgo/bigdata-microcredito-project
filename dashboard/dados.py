# dados.py
# De onde o dashboard pega os dados. Tenta o banco da Aiven (variavel
# AIVEN_PG_URL no terminal ou segredo AIVEN_PG_URL no Streamlit Cloud) e, se
# nao der, usa os csvs do repositorio.

import os
import pandas as pd
import streamlit as st

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


def csv_regional():
    df = pd.read_csv(os.path.join(BASE, "data", "processed", "fato_credito_regional.csv"))
    df["regiao"] = df["uf"].map(REGIAO)
    return df


def csv_perfil():
    return pd.read_csv(os.path.join(BASE, "data", "ibge_sexo_raca_uf_2022.csv"))


@st.cache_data(ttl=3600, show_spinner="carregando os dados...")
def carregar_dados(url):
    avisos = []
    fonte = "arquivos CSV do repositório"
    regional = perfil = None

    if url:
        try:
            import psycopg2
            conn = psycopg2.connect(url, connect_timeout=10)
            regional = consulta(conn, SQL_REGIONAL)
            fonte = "banco PostgreSQL da Aiven"
            try:
                perfil = consulta(conn, SQL_PERFIL)
            except Exception:
                # a tabela de perfil pode ainda nao ter sido carregada
                conn.rollback()
                avisos.append("A tabela de perfil ainda não está no banco, usei o CSV do IBGE.")
            conn.close()
        except Exception as erro:
            avisos.append(f"O banco não respondeu ({type(erro).__name__}), usei os CSVs do repositório.")
            regional = None

    if regional is None:
        regional = csv_regional()
    if perfil is None or perfil.empty:
        perfil = csv_perfil()

    regional["data_referencia"] = pd.to_datetime(regional["data_referencia"])
    for col in ["valor_carteira_ativa", "taxa_inadimplencia", "quantidade_operacoes"]:
        regional[col] = pd.to_numeric(regional[col])
    return {"regional": regional, "perfil": perfil}, fonte, avisos
