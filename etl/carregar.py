# carregar.py
# Ultima etapa: cria as tabelas (sql/schema.sql) e sobe os csvs tratados pro
# Postgres da Aiven. A connection string fica numa variavel de ambiente
# (AIVEN_PG_URL) pra ninguem deixar senha espalhada no codigo/no git.
#
# uso:
#   export AIVEN_PG_URL="postgres://usuario:senha@host:porta/defaultdb?sslmode=require"
#   python carregar.py

import os
import sys
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

BASE = os.path.join(os.path.dirname(__file__), "..")
PASTA_PROC = os.path.join(BASE, "data", "processed")

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


def conectar():
    url = os.environ.get("AIVEN_PG_URL")
    if not url:
        print("faltou definir a variavel AIVEN_PG_URL")
        sys.exit(1)
    return psycopg2.connect(url)


def criar_schema(conn):
    with open(os.path.join(BASE, "sql", "schema.sql"), encoding="utf-8") as f:
        sql = f.read()
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    print("schema criado")


def carregar_dim_uf(conn):
    cur = conn.cursor()
    linhas = [(sigla, nome, regiao) for sigla, (nome, regiao) in UFS_BRASIL.items()]
    execute_values(
        cur,
        "INSERT INTO dim_uf (sigla_uf, nome_uf, regiao) VALUES %s ON CONFLICT (sigla_uf) DO NOTHING",
        linhas,
    )
    conn.commit()


def carregar_fato_nacional(conn):
    caminho = os.path.join(PASTA_PROC, "fato_microcredito_nacional.csv")
    if not os.path.exists(caminho):
        return
    df = pd.read_csv(caminho)
    cur = conn.cursor()
    execute_values(
        cur,
        """INSERT INTO fato_microcredito_nacional
           (serie_id, descricao_serie, data_referencia, valor)
           VALUES %s ON CONFLICT (serie_id, data_referencia) DO NOTHING""",
        list(df.itertuples(index=False, name=None)),
    )
    conn.commit()
    print(f"fato_microcredito_nacional: {len(df)} linhas carregadas")


def carregar_fato_regional(conn):
    caminho = os.path.join(PASTA_PROC, "fato_credito_regional.csv")
    if not os.path.exists(caminho):
        return
    df = pd.read_csv(caminho)
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

    # sobe em lotes de 200 com commit a cada um: o plano gratis da aiven
    # derrubou a conexao uma vez numa carga grande de uma vez so, assim se
    # cair da pra rodar de novo (o ON CONFLICT pula o que ja entrou)
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


if __name__ == "__main__":
    conn = conectar()
    criar_schema(conn)
    carregar_dim_uf(conn)
    carregar_fato_nacional(conn)
    carregar_fato_regional(conn)
    conn.close()
    print("carga concluida")
