"""
carregar.py

Ultima etapa: sobe os csvs tratados pro Postgres da Aiven. A connection
string fica na variavel de ambiente AIVEN_PG_URL pra ninguem deixar senha
espalhada no codigo ou no git.

Antes esse script apagava e recriava as tabelas toda vez que rodava, e isso
era perigoso. Agora cada coisa tem a sua flag:
    sem flag        so carrega os dados (as tabelas ja precisam existir)
    --criar-schema  cria as tabelas que faltam (sql/schema.sql) e depois carrega
    --limpar        apaga as 4 tabelas (sql/limpar.sql) e para, nao carrega nada

Uso:
    export AIVEN_PG_URL="postgres://usuario:senha@host:porta/defaultdb?sslmode=require"
    python etl/carregar.py
    python etl/carregar.py --criar-schema
    python etl/carregar.py --limpar
"""

import argparse
import os
import sys
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

BASE = os.path.join(os.path.dirname(__file__), "..")
PASTA_PROC = os.path.join(BASE, "data", "processed")
CSV_REGIONAL = os.path.join(PASTA_PROC, "fato_credito_regional.csv")
CSV_NACIONAL = os.path.join(PASTA_PROC, "fato_microcredito_nacional.csv")

UFS_BRASIL = {
    "AC": ("Acre", "Norte"), "AM": ("Amazonas", "Norte"), "AP": ("Amapá", "Norte"),
    "PA": ("Pará", "Norte"), "RO": ("Rondônia", "Norte"), "RR": ("Roraima", "Norte"),
    "TO": ("Tocantins", "Norte"),
    "AL": ("Alagoas", "Nordeste"), "BA": ("Bahia", "Nordeste"), "CE": ("Ceará", "Nordeste"),
    "MA": ("Maranhão", "Nordeste"), "PB": ("Paraíba", "Nordeste"), "PE": ("Pernambuco", "Nordeste"),
    "PI": ("Piauí", "Nordeste"), "RN": ("Rio Grande do Norte", "Nordeste"), "SE": ("Sergipe", "Nordeste"),
    "DF": ("Distrito Federal", "Centro-Oeste"), "GO": ("Goiás", "Centro-Oeste"),
    "MS": ("Mato Grosso do Sul", "Centro-Oeste"), "MT": ("Mato Grosso", "Centro-Oeste"),
    "ES": ("Espírito Santo", "Sudeste"), "MG": ("Minas Gerais", "Sudeste"),
    "RJ": ("Rio de Janeiro", "Sudeste"), "SP": ("São Paulo", "Sudeste"),
    "PR": ("Paraná", "Sul"), "RS": ("Rio Grande do Sul", "Sul"), "SC": ("Santa Catarina", "Sul"),
}

TABELAS = ["dim_uf", "dim_modalidade", "fato_credito_regional", "fato_microcredito_nacional"]


def parar(mensagem):
    print("erro:", mensagem)
    sys.exit(1)


def ler_csv(caminho, colunas_obrigatorias):
    # confiro o csv antes de abrir a conexao, assim nada e escrito se der erro
    if not os.path.exists(caminho):
        parar(f"nao achei o arquivo {caminho}. rode o tratar.py antes")
    df = pd.read_csv(caminho)
    faltando = [c for c in colunas_obrigatorias if c not in df.columns]
    if faltando:
        parar(f"faltam colunas em {os.path.basename(caminho)}: {faltando}")
    if df.empty:
        parar(f"o arquivo {os.path.basename(caminho)} esta vazio")
    return df


def validar_arquivos():
    regional = ler_csv(CSV_REGIONAL, [
        "uf", "segmento", "modalidade", "data_referencia",
        "valor_carteira_ativa", "taxa_inadimplencia", "quantidade_operacoes",
    ])
    nacional = ler_csv(CSV_NACIONAL, ["serie_id", "descricao_serie", "data_referencia", "valor"])

    # as colunas que formam a chave nao podem ter vazio
    for nome, df, chave in [
        ("fato_credito_regional.csv", regional, ["uf", "segmento", "modalidade", "data_referencia"]),
        ("fato_microcredito_nacional.csv", nacional, ["serie_id", "data_referencia", "valor"]),
    ]:
        vazios = df[chave].isna().any(axis=1).sum()
        if vazios:
            parar(f"{nome} tem {vazios} linhas com campo da chave vazio")

    ufs_invalidas = sorted(set(regional["uf"]) - set(UFS_BRASIL))
    if ufs_invalidas:
        parar(f"UF que nao existe no Brasil no csv regional: {ufs_invalidas}")

    segmentos_invalidos = sorted(set(regional["segmento"]) - {"PF", "PJ"})
    if segmentos_invalidos:
        parar(f"segmento diferente de PF e PJ no csv regional: {segmentos_invalidos}")

    return regional, nacional


def conectar():
    url = os.environ.get("AIVEN_PG_URL")
    if not url:
        parar("faltou definir a variavel AIVEN_PG_URL")
    return psycopg2.connect(url)


def executar_sql_arquivo(conn, nome_arquivo):
    with open(os.path.join(BASE, "sql", nome_arquivo), encoding="utf-8") as f:
        sql = f.read()
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()


def limpar_tabelas(conn):
    # essa e a unica parte que apaga dados, por isso peco pra digitar APAGAR
    print("isso vai apagar as tabelas e todos os dados que tem nelas:", ", ".join(TABELAS))
    resposta = input("pra confirmar digite APAGAR: ")
    if resposta.strip() != "APAGAR":
        parar("nao confirmou, entao nao apaguei nada")
    executar_sql_arquivo(conn, "limpar.sql")
    print("tabelas apagadas. pra criar de novo use --criar-schema")


def tabelas_que_faltam(conn):
    cur = conn.cursor()
    cur.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    )
    existentes = {linha[0] for linha in cur.fetchall()}
    return [t for t in TABELAS if t not in existentes]


def carregar_dim_uf(conn):
    cur = conn.cursor()
    linhas = [(sigla, nome, regiao) for sigla, (nome, regiao) in UFS_BRASIL.items()]
    execute_values(
        cur,
        "INSERT INTO dim_uf (sigla_uf, nome_uf, regiao) VALUES %s ON CONFLICT (sigla_uf) DO NOTHING",
        linhas,
    )
    conn.commit()


def carregar_fato_nacional(conn, df):
    cur = conn.cursor()
    colunas = ["serie_id", "descricao_serie", "data_referencia", "valor"]
    execute_values(
        cur,
        """INSERT INTO fato_microcredito_nacional
           (serie_id, descricao_serie, data_referencia, valor)
           VALUES %s ON CONFLICT (serie_id, data_referencia) DO NOTHING""",
        list(df[colunas].itertuples(index=False, name=None)),
    )
    conn.commit()
    print(f"fato_microcredito_nacional: {len(df)} linhas carregadas")


def carregar_fato_regional(conn, df):
    cur = conn.cursor()

    # cada combinacao modalidade + segmento (PF/PJ) vira uma linha da dimensao
    for modalidade, segmento in df[["modalidade", "segmento"]].drop_duplicates().itertuples(index=False):
        cur.execute(
            "INSERT INTO dim_modalidade (nome_modalidade, segmento) VALUES (%s, %s) "
            "ON CONFLICT (nome_modalidade, segmento) DO NOTHING",
            (modalidade, segmento),
        )
    conn.commit()

    cur.execute("SELECT sigla_uf, uf_id FROM dim_uf")
    mapa_uf = dict(cur.fetchall())
    cur.execute("SELECT nome_modalidade, segmento, modalidade_id FROM dim_modalidade")
    mapa_modalidade = {(nome, seg): mid for nome, seg, mid in cur.fetchall()}

    linhas = []
    for _, r in df.iterrows():
        uf_id = mapa_uf.get(r["uf"])
        modalidade_id = mapa_modalidade.get((r["modalidade"], r["segmento"]))
        if uf_id is None or modalidade_id is None:
            continue
        linhas.append((
            uf_id, modalidade_id, r["data_referencia"],
            r["valor_carteira_ativa"], r["taxa_inadimplencia"], r["quantidade_operacoes"],
        ))

    # lotes de 200 com commit em cada um, se a conexao cair da pra rodar de novo
    for i in range(0, len(linhas), 200):
        execute_values(
            cur,
            """INSERT INTO fato_credito_regional
               (uf_id, modalidade_id, data_referencia, valor_carteira_ativa, taxa_inadimplencia, quantidade_operacoes)
               VALUES %s
               ON CONFLICT (uf_id, modalidade_id, data_referencia) DO NOTHING""",
            linhas[i:i + 200],
        )
        conn.commit()
    print(f"fato_credito_regional: {len(linhas)} linhas carregadas")


def main():
    parser = argparse.ArgumentParser(description="carrega os csvs tratados no postgres da aiven")
    parser.add_argument("--criar-schema", action="store_true",
                        help="cria as tabelas que faltam e depois carrega os dados")
    parser.add_argument("--limpar", action="store_true",
                        help="APAGA as tabelas e para (pede confirmacao)")
    args = parser.parse_args()

    if args.limpar and args.criar_schema:
        parar("use --limpar e --criar-schema em comandos separados, de proposito")

    if args.limpar:
        conn = conectar()
        limpar_tabelas(conn)
        conn.close()
        return

    # primeiro confiro os arquivos, so depois mexo no banco
    regional, nacional = validar_arquivos()

    conn = conectar()
    if args.criar_schema:
        executar_sql_arquivo(conn, "schema.sql")
        print("schema criado (so o que faltava, nada foi apagado)")

    faltam = tabelas_que_faltam(conn)
    if faltam:
        conn.close()
        parar(f"faltam as tabelas {faltam}. rode de novo com --criar-schema")

    carregar_dim_uf(conn)
    carregar_fato_nacional(conn, nacional)
    carregar_fato_regional(conn, regional)
    conn.close()
    print("carga concluida")


if __name__ == "__main__":
    main()
