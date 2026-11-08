"""
test_carga.py

Testes da carga no banco (etl/carregar.py).

Eles precisam de um Postgres DESCARTAVEL, porque cada teste apaga e recria as
tabelas. Por seguranca so rodam se a variavel TESTE_PG_URL apontar pra
localhost, entao nunca encostam no banco da Aiven.

Subindo um postgres de teste com docker:
    docker run -d --name pg-teste -e POSTGRES_PASSWORD=teste -p 55432:5432 postgres:17

Rodando os testes (PowerShell):
    $env:TESTE_PG_URL = "postgres://postgres:teste@localhost:55432/postgres?sslmode=disable"
    python -m unittest discover -s tests -v

Sem a variavel, os testes que usam banco sao pulados e os outros rodam normal.
"""

import contextlib
import io
import os
import sys
import unittest
from urllib.parse import urlparse

import pandas as pd
import psycopg2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "etl"))
import carregar  # noqa: E402

URL_TESTE = os.environ.get("TESTE_PG_URL", "")
HOST_TESTE = urlparse(URL_TESTE).hostname if URL_TESTE else None
BANCO_LOCAL = HOST_TESTE in ("localhost", "127.0.0.1")


def silencioso(funcao, *args):
    # o script imprime bastante, aqui eu escondo a saida pra ela nao poluir o teste
    with contextlib.redirect_stdout(io.StringIO()):
        return funcao(*args)


def df_regional(valores=(1000.0, 2000.0, 3000.0)):
    # tres linhas de exemplo: BA em dois meses e SP em um
    return pd.DataFrame({
        "uf": ["BA", "BA", "SP"],
        "segmento": ["PF", "PF", "PJ"],
        "modalidade": ["Empréstimos - Microcrédito"] * 3,
        "data_referencia": ["2026-01-31", "2026-02-28", "2026-01-31"],
        "valor_carteira_ativa": list(valores),
        "taxa_inadimplencia": [0.01, 0.02, 0.03],
        "quantidade_operacoes": [10, 20, 30],
    })


class TestValidacaoSemBanco(unittest.TestCase):
    def test_chave_repetida_para_a_carga(self):
        df = pd.concat([df_regional(), df_regional().head(1)])
        with self.assertRaises(SystemExit):
            silencioso(carregar.conferir_chaves_repetidas, df,
                       ["uf", "segmento", "modalidade", "data_referencia"], "teste.csv")

    def test_chaves_diferentes_passam(self):
        silencioso(carregar.conferir_chaves_repetidas, df_regional(),
                   ["uf", "segmento", "modalidade", "data_referencia"], "teste.csv")

    def test_ou_nulo_troca_nan_por_none(self):
        self.assertIsNone(carregar.ou_nulo(float("nan")))
        self.assertEqual(carregar.ou_nulo(pd.Series([1.5]).iloc[0]), 1.5)


@unittest.skipUnless(BANCO_LOCAL, "defina TESTE_PG_URL apontando pra um postgres em localhost")
class TestCargaNoBanco(unittest.TestCase):
    def setUp(self):
        self.conn = psycopg2.connect(URL_TESTE)
        silencioso(carregar.executar_sql_arquivo, self.conn, "limpar.sql")
        silencioso(carregar.executar_sql_arquivo, self.conn, "schema.sql")
        silencioso(carregar.carregar_dim_uf, self.conn)
        self.lote_original = carregar.TAMANHO_LOTE

    def tearDown(self):
        carregar.TAMANHO_LOTE = self.lote_original
        self.conn.rollback()
        silencioso(carregar.executar_sql_arquivo, self.conn, "limpar.sql")
        self.conn.close()

    def contar(self, tabela="fato_credito_regional"):
        cur = self.conn.cursor()
        cur.execute(f"SELECT count(*) FROM {tabela}")
        return cur.fetchone()[0]

    def test_primeira_carga_insere_tudo(self):
        resultado = silencioso(carregar.carregar_fato_regional, self.conn, df_regional())
        self.assertEqual(resultado, (3, 0, 0))
        self.assertEqual(self.contar(), 3)

    def test_segunda_carga_igual_nao_muda_nada(self):
        silencioso(carregar.carregar_fato_regional, self.conn, df_regional())
        resultado = silencioso(carregar.carregar_fato_regional, self.conn, df_regional())
        self.assertEqual(resultado, (0, 0, 3))
        self.assertEqual(self.contar(), 3)

    def test_valor_que_mudou_e_atualizado(self):
        silencioso(carregar.carregar_fato_regional, self.conn, df_regional())
        resultado = silencioso(carregar.carregar_fato_regional, self.conn,
                               df_regional(valores=(1000.0, 9999.0, 3000.0)))
        self.assertEqual(resultado, (0, 1, 2))
        cur = self.conn.cursor()
        cur.execute("SELECT valor_carteira_ativa FROM fato_credito_regional "
                    "WHERE data_referencia = '2026-02-28'")
        self.assertEqual(float(cur.fetchone()[0]), 9999.0)
        self.assertEqual(self.contar(), 3)

    def test_dimensao_que_falta_para_a_carga(self):
        df = df_regional()
        df.loc[0, "uf"] = "ZZ"
        with self.assertRaises(SystemExit):
            silencioso(carregar.carregar_fato_regional, self.conn, df)
        self.assertEqual(self.contar(), 0)

    def test_falha_no_meio_guarda_o_que_ja_entrou_e_retoma(self):
        carregar.TAMANHO_LOTE = 2
        df = df_regional()
        df["valor_carteira_ativa"] = df["valor_carteira_ativa"].astype(float)
        df.loc[2, "valor_carteira_ativa"] = 1e20
        with self.assertRaises(SystemExit):
            silencioso(carregar.carregar_fato_regional, self.conn, df)
        self.assertEqual(self.contar(), 2)

        df.loc[2, "valor_carteira_ativa"] = 3000.0
        resultado = silencioso(carregar.carregar_fato_regional, self.conn, df)
        self.assertEqual(resultado, (1, 0, 2))
        self.assertEqual(self.contar(), 3)

    def test_carga_nacional_insere_e_atualiza(self):
        df = pd.DataFrame({
            "serie_id": [20618, 20618],
            "descricao_serie": ["saldo", "saldo"],
            "data_referencia": ["2026-01-01", "2026-02-01"],
            "valor": [100.5, 200.5],
        })
        self.assertEqual(silencioso(carregar.carregar_fato_nacional, self.conn, df), (2, 0, 0))
        df.loc[1, "valor"] = 250.5
        self.assertEqual(silencioso(carregar.carregar_fato_nacional, self.conn, df), (0, 1, 1))
        self.assertEqual(self.contar("fato_microcredito_nacional"), 2)


if __name__ == "__main__":
    unittest.main()
