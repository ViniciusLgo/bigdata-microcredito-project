"""Valida a seleção de fonte do painel sem acessar nenhum banco externo."""

from decimal import Decimal
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard"))
import dados


def bases_validas(decimal=False):
    numero = Decimal if decimal else float
    regional = pd.DataFrame([{
        "uf": "BA", "segmento": "PF", "modalidade": "Empréstimos - Microcrédito",
        "data_referencia": "2026-07-31", "valor_carteira_ativa": numero("1000"),
        "quantidade_operacoes": numero("-1"), "taxa_inadimplencia": numero("0.05"),
    }])
    perfil = pd.DataFrame([
        {"uf": "BA", "ano": numero("2022"), "sexo": sexo, "cor_raca": cor,
         "ocupados": numero("10")}
        for sexo in ["Homens", "Mulheres"]
        for cor in ["Branca", "Preta", "Amarela", "Parda", "Indígena"]
    ])
    nacional = pd.DataFrame([
        {"serie_id": numero(str(serie)), "descricao_serie": "Série nacional",
         "data_referencia": "2026-08-01", "valor": numero("123.45")}
        for serie in [20618, 20712]
    ])
    return {"regional": regional, "perfil": perfil, "nacional": nacional}


class CarregamentoDadosTest(unittest.TestCase):
    def banco_simulado(self, bases=None, erro=None):
        conn = MagicMock()
        connect = MagicMock(return_value=conn)
        if erro is not None:
            connect.side_effect = erro
        driver = SimpleNamespace(connect=connect)
        consultas = [bases[k] for k in ["regional", "perfil", "nacional"]] if bases else []
        return conn, driver, consultas

    def test_csv_sem_url_tem_fonte_correta_e_preserva_operacao_negativa(self):
        bases = bases_validas()
        with patch.object(dados.pd, "read_csv", side_effect=[bases[k] for k in dados.ARQUIVOS]):
            resultado, fonte, avisos = dados.carregar_dados()
        self.assertEqual(fonte, dados.FONTE_CSV)
        self.assertEqual(avisos, [])
        self.assertEqual(resultado["regional"].iloc[0]["regiao"], "Nordeste")
        self.assertEqual(resultado["regional"].iloc[0]["quantidade_operacoes"], -1)

    def test_banco_valido_converte_decimal_em_todas_as_bases_e_fecha_conexao(self):
        conn, driver, consultas = self.banco_simulado(bases_validas(decimal=True))
        with patch.dict(sys.modules, {"psycopg2": driver}), patch.object(
            dados, "consulta", side_effect=consultas
        ), patch.object(dados, "_carregar_csvs") as csvs:
            resultado, fonte, avisos = dados.carregar_dados("postgres://exemplo")
        self.assertEqual(fonte, dados.FONTE_BANCO)
        self.assertEqual(avisos, [])
        csvs.assert_not_called()
        conn.set_session.assert_called_once_with(readonly=True)
        conn.close.assert_called_once()
        for nome, colunas in dados.NUMERICAS.items():
            for coluna in colunas:
                self.assertTrue(pd.api.types.is_numeric_dtype(resultado[nome][coluna]))
        self.assertAlmostEqual(resultado["nacional"].iloc[0]["valor"], 123.45)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(resultado["regional"]["data_referencia"]))

    def test_erro_de_conexao_nao_expoe_credencial(self):
        segredo = "postgres://usuario:senha-secreta@host/base"
        _, driver, _ = self.banco_simulado(erro=RuntimeError(segredo))
        locais = bases_validas()
        with patch.dict(sys.modules, {"psycopg2": driver}), patch.object(
            dados, "_carregar_csvs", return_value=locais
        ):
            resultado, fonte, avisos = dados.carregar_dados(segredo)
        self.assertIs(resultado, locais)
        self.assertEqual(fonte, dados.FONTE_CSV)
        self.assertEqual(len(avisos), 1)
        self.assertNotIn("senha-secreta", str(avisos))
        self.assertNotIn("postgres://", str(avisos))

    def test_tabela_ausente_fecha_conexao_e_recarrega_todas_as_bases(self):
        conn, driver, consultas = self.banco_simulado(bases_validas())
        locais = bases_validas()
        with patch.dict(sys.modules, {"psycopg2": driver}), patch.object(
            dados, "consulta", side_effect=[consultas[0], RuntimeError("tabela ausente")]
        ), patch.object(dados, "_carregar_csvs", return_value=locais) as csvs:
            resultado, fonte, avisos = dados.carregar_dados("postgres://exemplo")
        self.assertIs(resultado, locais)
        self.assertEqual(fonte, dados.FONTE_CSV)
        self.assertIn("Todos os dados", avisos[0])
        csvs.assert_called_once()
        conn.close.assert_called_once()

    def test_base_vazia_ou_malformada_nao_recebe_rotulo_de_banco(self):
        for defeito in ["regional_vazio", "perfil_vazio", "nacional_vazio", "nacional_decimal_invalido",
                        "perfil_incompleto", "data_invalida", "duplicata", "coluna_ausente"]:
            with self.subTest(defeito=defeito):
                bases = bases_validas()
                if defeito.endswith("_vazio"):
                    nome = defeito.split("_")[0]
                    bases[nome] = bases[nome].iloc[:0]
                elif defeito == "nacional_decimal_invalido":
                    bases["nacional"]["valor"] = "não numérico"
                elif defeito == "perfil_incompleto":
                    bases["perfil"] = bases["perfil"].iloc[:-1]
                elif defeito == "data_invalida":
                    bases["regional"]["data_referencia"] = "inválida"
                elif defeito == "duplicata":
                    bases["regional"] = pd.concat([bases["regional"]] * 2, ignore_index=True)
                else:
                    bases["nacional"] = bases["nacional"].drop(columns="valor")
                conn, driver, consultas = self.banco_simulado(bases)
                locais = bases_validas()
                with patch.dict(sys.modules, {"psycopg2": driver}), patch.object(
                    dados, "consulta", side_effect=consultas
                ), patch.object(dados, "_carregar_csvs", return_value=locais):
                    resultado, fonte, avisos = dados.carregar_dados("postgres://exemplo")
                self.assertIs(resultado, locais)
                self.assertEqual(fonte, dados.FONTE_CSV)
                self.assertEqual(len(avisos), 1)
                conn.close.assert_called_once()

    def test_csv_invalido_falha_com_mensagem_limpa(self):
        with patch.object(dados.pd, "read_csv", side_effect=OSError("detalhe sensível")):
            with self.assertRaisesRegex(ValueError, "Não foi possível ler o CSV da base regional") as erro:
                dados.carregar_dados()
        self.assertNotIn("sensível", str(erro.exception))

    def test_consulta_fecha_cursor_tambem_quando_sql_falha(self):
        conn = MagicMock()
        cursor = conn.cursor.return_value
        cursor.execute.side_effect = RuntimeError("consulta falhou")
        with self.assertRaises(RuntimeError):
            dados.consulta(conn, dados.SQL_REGIONAL)
        cursor.close.assert_called_once()

    def test_csvs_versionados_passam_na_validacao(self):
        resultado, fonte, avisos = dados.carregar_dados()
        self.assertEqual(fonte, dados.FONTE_CSV)
        self.assertEqual(avisos, [])
        self.assertEqual({nome: len(df) for nome, df in resultado.items()},
                         {"regional": 7081, "perfil": 270, "nacional": 136})


if __name__ == "__main__":
    unittest.main()
