"""Leitura e validação das bases do painel, sem depender do Streamlit.

O banco é usado somente quando as três bases estão disponíveis e válidas.
Em caso de falha, o conjunto inteiro volta aos CSVs versionados para não
misturar versões de crédito e perfil demográfico sem avisar o leitor.
"""

from contextlib import closing
from pathlib import Path

import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parents[1]
FONTE_CSV = "arquivos CSV do repositório"
FONTE_BANCO = "banco PostgreSQL (Aiven)"

REGIAO = {
    "AC": "Norte", "AM": "Norte", "AP": "Norte", "PA": "Norte",
    "RO": "Norte", "RR": "Norte", "TO": "Norte",
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste",
    "PB": "Nordeste", "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste", "SE": "Nordeste",
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
SQL_NACIONAL = """
    SELECT serie_id, descricao_serie, data_referencia, valor
    FROM fato_microcredito_nacional
"""

ARQUIVOS = {
    "regional": "data/processed/fato_credito_regional.csv",
    "perfil": "data/ibge_sexo_raca_uf_2022.csv",
    "nacional": "data/processed/fato_microcredito_nacional.csv",
}
COLUNAS = {
    "regional": ["uf", "segmento", "modalidade", "data_referencia",
                 "valor_carteira_ativa", "quantidade_operacoes", "taxa_inadimplencia"],
    "perfil": ["uf", "ano", "sexo", "cor_raca", "ocupados"],
    "nacional": ["serie_id", "descricao_serie", "data_referencia", "valor"],
}
CHAVES = {
    "regional": ["uf", "segmento", "modalidade", "data_referencia"],
    "perfil": ["uf", "ano", "sexo", "cor_raca"],
    "nacional": ["serie_id", "data_referencia"],
}
NUMERICAS = {
    "regional": ["valor_carteira_ativa", "quantidade_operacoes", "taxa_inadimplencia"],
    "perfil": ["ano", "ocupados"],
    "nacional": ["serie_id", "valor"],
}


def consulta(conn, sql):
    """Executa apenas as consultas SELECT fixas e fecha o cursor."""
    with closing(conn.cursor()) as cursor:
        cursor.execute(sql)
        return pd.DataFrame(cursor.fetchall(), columns=[col[0] for col in cursor.description])


def _validar_base(nome, original):
    if not isinstance(original, pd.DataFrame) or original.empty:
        raise ValueError(f"A base {nome} está vazia.")
    if not set(COLUNAS[nome]).issubset(original.columns):
        raise ValueError(f"A base {nome} não tem todas as colunas necessárias.")
    df = original.copy()
    if df[COLUNAS[nome]].isna().any().any():
        raise ValueError(f"A base {nome} contém campos vazios.")

    for coluna in NUMERICAS[nome]:
        # psycopg2 retorna DECIMAL como Decimal; normalizar todas as fontes.
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce").astype(float)
        if not np.isfinite(df[coluna].to_numpy()).all():
            raise ValueError(f"A base {nome} contém números inválidos.")
    for coluna in set(COLUNAS[nome]) - set(NUMERICAS[nome]) - {"data_referencia"}:
        df[coluna] = df[coluna].astype(str).str.strip()
        if df[coluna].eq("").any():
            raise ValueError(f"A base {nome} contém campos vazios.")
    if "data_referencia" in df:
        df["data_referencia"] = pd.to_datetime(df["data_referencia"], errors="coerce")
        if df["data_referencia"].isna().any():
            raise ValueError(f"A base {nome} contém datas inválidas.")
    if "uf" in df and not df["uf"].isin(REGIAO).all():
        raise ValueError(f"A base {nome} contém UF inválida.")
    if df.duplicated(CHAVES[nome]).any():
        raise ValueError(f"A base {nome} contém chaves repetidas.")

    if nome == "regional":
        if not df["segmento"].isin(["PF", "PJ"]).all():
            raise ValueError("A base regional contém tipo de cliente inválido.")
        if not df["modalidade"].isin(["Empréstimos - Microcrédito", "Financiamentos - Microcrédito"]).all():
            raise ValueError("A base regional contém modalidade fora do recorte de microcrédito.")
        if (df["valor_carteira_ativa"] <= 0).any() or not df["taxa_inadimplencia"].between(0, 1).all():
            raise ValueError("A base regional contém carteira ou taxa inválida.")
        if (df["quantidade_operacoes"] % 1 != 0).any():
            raise ValueError("A base regional contém contagem fracionária de operações.")
        # Valores negativos de operações são preservados, conforme o dicionário.
        df["regiao"] = df["uf"].map(REGIAO)
    elif nome == "perfil":
        if not df["ano"].eq(2022).all():
            raise ValueError("O perfil territorial precisa corresponder ao Censo 2022.")
        if not df["sexo"].isin(["Homens", "Mulheres"]).all() or not df["cor_raca"].isin(
            ["Branca", "Preta", "Amarela", "Parda", "Indígena"]
        ).all():
            raise ValueError("A base perfil contém categorias incompatíveis com o Censo.")
        if (df["ocupados"] < 0).any() or (df["ocupados"] % 1 != 0).any():
            raise ValueError("A base perfil contém quantidades inválidas.")
        if not df.groupby("uf").size().eq(10).all() or not df.groupby("uf")["ocupados"].sum().gt(0).all():
            raise ValueError("A base perfil está incompleta por UF.")
        df[["ano", "ocupados"]] = df[["ano", "ocupados"]].astype("int64")
    elif nome == "nacional":
        if set(df["serie_id"]) != {20618, 20712} or (df["valor"] < 0).any():
            raise ValueError("A base nacional contém séries ou valores inválidos.")
        df["serie_id"] = df["serie_id"].astype("int64")
    return df


def _validar_conjunto(bases):
    validas = {nome: _validar_base(nome, bases[nome]) for nome in ARQUIVOS}
    if not set(validas["regional"]["uf"]).issubset(validas["perfil"]["uf"]):
        raise ValueError("O perfil do IBGE não cobre todas as UFs do crédito.")
    return validas


def _carregar_csvs():
    bases = {}
    for nome, arquivo in ARQUIVOS.items():
        try:
            bases[nome] = pd.read_csv(BASE / arquivo)
        except Exception:
            raise ValueError(f"Não foi possível ler o CSV da base {nome}.") from None
    return _validar_conjunto(bases)


def carregar_dados(url=None):
    """Retorna (bases, fonte, avisos); nenhuma consulta modifica o banco."""
    avisos = []
    if url:
        try:
            import psycopg2

            with closing(psycopg2.connect(url, connect_timeout=10)) as conn:
                conn.set_session(readonly=True)
                bases = {
                    "regional": consulta(conn, SQL_REGIONAL),
                    "perfil": consulta(conn, SQL_PERFIL),
                    "nacional": consulta(conn, SQL_NACIONAL),
                }
                bases = _validar_conjunto(bases)
            return bases, FONTE_BANCO, avisos
        except Exception:
            # Não expor detalhes da exceção: podem conter a URL e a senha.
            avisos.append(
                "Não foi possível validar as três bases do banco. "
                "Todos os dados exibidos foram carregados dos CSVs do repositório."
            )
    return _carregar_csvs(), FONTE_CSV, avisos
