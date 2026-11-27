"""Testes das unidades temporais, cobertura e valores ausentes do painel."""

import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))
import contas


def base(linhas):
    return pd.DataFrame([
        {"uf": uf, "regiao": "Nordeste", "segmento": "PF", "modalidade": "Microcrédito",
         "data_referencia": pd.Timestamp(data), "valor_carteira_ativa": carteira,
         "taxa_inadimplencia": 0.1, "quantidade_operacoes": operacoes}
        for uf, data, carteira, operacoes in linhas
    ], columns=["uf", "regiao", "segmento", "modalidade", "data_referencia",
                "valor_carteira_ativa", "taxa_inadimplencia", "quantidade_operacoes"])


class TesteValoresAusentes(unittest.TestCase):
    def test_operacoes_todas_invalidas_nao_sao_zero(self):
        df = base([("BA", "2022-01-01", 100, -1), ("BA", "2022-01-01", 50, -2)])
        resultado = contas.agregar(df, ["uf"], {"BA": 10}).iloc[0]
        self.assertTrue(pd.isna(resultado["operacoes"]))
        self.assertEqual(resultado["linhas_operacoes_invalidas"], 2)
        self.assertEqual(resultado["carteira"], 150)

    def test_zero_valido_e_preservado_e_parcial_identificado(self):
        df = base([("BA", "2022-01-01", 100, 0), ("BA", "2022-01-01", 50, -1)])
        resultado = contas.agregar(df, ["uf"], {"BA": 10}).iloc[0]
        self.assertEqual(resultado["operacoes"], 0)
        self.assertEqual(resultado["linhas_operacoes_validas"], 1)
        self.assertEqual(resultado["linhas_operacoes_invalidas"], 1)

    def test_taxa_com_carteira_zero_nao_infinita(self):
        resultado = contas.agregar(base([("BA", "2022-01-01", 0, 0)]), ["uf"], {"BA": 0}).iloc[0]
        self.assertTrue(pd.isna(resultado["inadimplencia"]))
        self.assertTrue(pd.isna(resultado["carteira_por_ocupado"]))

    def test_correlacao_constante_e_vazia_sao_indefinidas(self):
        for x, y in [([1, 1, 1], [1, 2, 3]), ([], []), ([1], [1]), ([1, 2], [None, 3])]:
            self.assertTrue(pd.isna(contas.spearman(pd.Series(x, dtype=float), pd.Series(y, dtype=float))))

    def test_correlacao_remove_pares_antes_de_ordenar(self):
        x = pd.Series([1, 2, 100, 3])
        y = pd.Series([10, 20, None, 30])
        self.assertAlmostEqual(contas.spearman(x, y), 1)

    def test_formatacao_nao_mostra_nan_ou_inf(self):
        for numero in [None, float("nan"), float("inf")]:
            self.assertEqual(contas.fmt_num(numero), "indisponível")
            self.assertEqual(contas.fmt_reais(numero), "indisponível")


class TesteMeses(unittest.TestCase):
    def test_inicio_e_fim_do_mes_sao_mesma_referencia(self):
        df = base([("BA", "2022-01-01", 10, 1), ("BA", "2022-01-31", 20, 1),
                   ("BA", "2022-02-01", 30, 1)])
        resultado = contas.filtrar_meses(df, "2022-01-15", "2022-01-15")
        self.assertEqual(list(resultado["valor_carteira_ativa"]), [10, 20])
        self.assertEqual(len(df), 3)

    def test_periodo_invertido_e_rejeitado(self):
        with self.assertRaises(ValueError):
            contas.filtrar_meses(base([]), "2022-02", "2022-01")

    def test_intervalo_comum_respeita_fontes_com_dias_diferentes(self):
        a = base([("BA", "2022-01-31", 10, 1), ("BA", "2022-07-31", 20, 1)])
        b = base([("BA", "2022-02-01", 10, 1), ("BA", "2022-08-01", 20, 1)])
        self.assertEqual(contas.intervalo_mensal_comum(a, b),
                         (pd.Timestamp("2022-02-01"), pd.Timestamp("2022-07-01")))
        self.assertIsNone(contas.intervalo_mensal_comum(a, base([])))
        self.assertIsNone(contas.intervalo_mensal_comum())

    def test_intervalos_sem_intersecao(self):
        a = base([("BA", "2021-01-31", 10, 1)])
        b = base([("BA", "2022-01-01", 10, 1)])
        self.assertIsNone(contas.intervalo_mensal_comum(a, b))


class TesteVariacaoAnual(unittest.TestCase):
    def test_mes_comparavel_calcula_crescimento_sem_somar_ano(self):
        df = base([("BA", "2021-01-31", 100, 1), ("BA", "2021-02-28", 9999, 1),
                   ("BA", "2022-01-01", 120, 1)])
        r = contas.variacao_carteira_anual(df)
        self.assertTrue(r["comparavel"])
        self.assertAlmostEqual(r["variacao_pct"], 20)
        self.assertEqual(r["carteira_anterior"], 100)

    def test_mudanca_de_cobertura_nao_parece_crescimento(self):
        df = base([("BA", "2021-01-01", 100, 1), ("BA", "2022-01-01", 100, 1),
                   ("SE", "2022-01-01", 100, 1)])
        r = contas.variacao_carteira_anual(df)
        self.assertFalse(r["comparavel"])
        self.assertIsNone(r["variacao_pct"])
        self.assertEqual((r["celulas_atual"], r["celulas_anterior"]), (2, 1))

    def test_mes_anterior_ausente_ou_zero(self):
        for valores in [[("BA", "2022-01-01", 100, 1)],
                        [("BA", "2021-01-01", 0, 0), ("BA", "2022-01-01", 100, 1)]]:
            self.assertIsNone(contas.variacao_carteira_anual(base(valores))["variacao_pct"])

    def test_base_vazia_e_referencia_explicita(self):
        self.assertIsNone(contas.variacao_carteira_anual(base([]))["variacao_pct"])
        df = base([("BA", "2021-01-01", 100, 1), ("BA", "2022-01-01", 120, 1),
                   ("BA", "2022-02-01", 130, 1)])
        self.assertAlmostEqual(contas.variacao_carteira_anual(df, "2022-01")["variacao_pct"], 20)


class TesteCruzamentoAnual(unittest.TestCase):
    def test_media_anual_soma_modalidades_por_mes_antes_da_media(self):
        linhas = []
        for mes in range(1, 13):
            linhas.extend([("BA", f"2022-{mes:02}-01", mes * 100, 1),
                           ("BA", f"2022-{mes:02}-01", mes * 10, 1)])
        linhas.append(("BA", "2023-01-01", 1_000_000, 1))
        r = contas.carteira_media_anual_uf(base(linhas), {"BA": 10}).iloc[0]
        self.assertEqual(r["meses_disponiveis"], 12)
        self.assertTrue(r["cobertura_completa"])
        self.assertEqual(r["carteira_media"], 715)
        self.assertEqual(r["carteira_por_ocupado"], 71.5)

    def test_ano_incompleto_nao_comparado_com_ano_inteiro(self):
        r = contas.carteira_media_anual_uf(base([("BA", "2022-01-01", 100, 1)]), {"BA": 10}).iloc[0]
        self.assertEqual(r["meses_disponiveis"], 1)
        self.assertFalse(r["cobertura_completa"])
        self.assertTrue(pd.isna(r["carteira_media"]))
        self.assertTrue(pd.isna(r["carteira_por_ocupado"]))

    def test_ano_ausente_retorna_tabela_vazia(self):
        r = contas.carteira_media_anual_uf(base([("BA", "2023-01-01", 100, 1)]), {"BA": 10})
        self.assertTrue(r.empty)
        self.assertIn("carteira_por_ocupado", r.columns)


if __name__ == "__main__":
    unittest.main()
