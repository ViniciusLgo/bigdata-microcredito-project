"""
test_dashboard.py

Testes das contas do dashboard (dashboard/contas.py). Nao precisam de banco
nem do streamlit.

Rodar (da raiz do projeto):
    python -m unittest tests.test_dashboard -v
"""

import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))
import contas  # noqa: E402

OCUPADOS = {"AC": 100, "AM": 300, "BA": 1000}


def linhas(*itens):
    # cada item: (uf, regiao, mes, carteira, taxa, operacoes)
    return pd.DataFrame(
        [{
            "uf": uf, "regiao": regiao, "segmento": "PF", "modalidade": "Emprestimos",
            "data_referencia": pd.Timestamp(mes), "valor_carteira_ativa": carteira,
            "taxa_inadimplencia": taxa, "quantidade_operacoes": ops,
        } for uf, regiao, mes, carteira, taxa, ops in itens]
    )


class TesteAgregar(unittest.TestCase):
    def test_inadimplencia_e_ponderada_pela_carteira(self):
        # 10% de 100 e 50% de 300 da (10 + 150) / 400 = 40%, nao a media simples (30%)
        df = linhas(("AC", "Norte", "2026-01-31", 100, 0.10, 5),
                    ("AM", "Norte", "2026-01-31", 300, 0.50, 5))
        g = contas.agregar(df.assign(tudo="x"), ["tudo"], OCUPADOS)
        self.assertAlmostEqual(g["inadimplencia"].iloc[0], 40.0)

    def test_operacoes_negativas_ficam_de_fora(self):
        df = linhas(("AC", "Norte", "2026-01-31", 100, 0.1, 10),
                    ("AM", "Norte", "2026-01-31", 100, 0.1, -3))
        g = contas.agregar(df.assign(tudo="x"), ["tudo"], OCUPADOS)
        self.assertEqual(g["operacoes"].iloc[0], 10)

    def test_carteira_por_ocupado_por_uf(self):
        df = linhas(("AC", "Norte", "2026-01-31", 500, 0.1, 1))
        g = contas.agregar(df, ["uf"], OCUPADOS)
        self.assertAlmostEqual(g["carteira_por_ocupado"].iloc[0], 5.0)

    def test_populacao_da_regiao_depende_do_mes(self):
        # em janeiro so o AM tem dado, em fevereiro AC e AM. o denominador de
        # janeiro tem que ser so o do AM (300), e nao o de AC mais AM (400)
        df = linhas(("AM", "Norte", "2026-01-31", 300, 0.1, 1),
                    ("AC", "Norte", "2026-02-28", 100, 0.1, 1),
                    ("AM", "Norte", "2026-02-28", 300, 0.1, 1))
        g = contas.agregar(df, ["data_referencia", "regiao"], OCUPADOS).set_index("data_referencia")
        self.assertAlmostEqual(g.loc["2026-01-31", "carteira_por_ocupado"], 300 / 300)
        self.assertAlmostEqual(g.loc["2026-02-28", "carteira_por_ocupado"], 400 / 400)

    def test_detalhe_da_uf_mantem_a_carteira_por_ocupado(self):
        # o detalhe de uma uf agrupa por modalidade e segmento, e a uf tem que
        # ficar no agrupamento, senao a metrica vira vazia
        df = linhas(("AC", "Norte", "2026-01-31", 200, 0.1, 1),
                    ("AC", "Norte", "2026-02-28", 300, 0.1, 1))
        g = contas.agregar(df, ["uf", "data_referencia", "modalidade", "segmento"], OCUPADOS)
        self.assertFalse(g["carteira_por_ocupado"].isna().any())
        self.assertEqual(list(g["carteira_por_ocupado"]), [2.0, 3.0])

    def test_sem_uf_nem_regiao_nao_tem_carteira_por_ocupado(self):
        df = linhas(("AC", "Norte", "2026-01-31", 200, 0.1, 1))
        g = contas.agregar(df, ["segmento"], OCUPADOS)
        self.assertTrue(g["carteira_por_ocupado"].isna().all())


class TesteParticipacao(unittest.TestCase):
    def perfil(self):
        return pd.DataFrame({
            "uf": ["AC"] * 4,
            "sexo": ["Mulheres", "Mulheres", "Homens", "Homens"],
            "cor_raca": ["Preta", "Branca", "Preta", "Branca"],
            "ocupados": [10, 30, 20, 40],
        })

    def test_mulheres_pretas(self):
        p = contas.participacao_grupo(self.perfil(), "Mulheres", ["Preta"])
        self.assertAlmostEqual(p["part_grupo"].iloc[0], 10 / 100)

    def test_todos_sem_cor_e_100_por_cento(self):
        p = contas.participacao_grupo(self.perfil(), "Todos", [])
        self.assertAlmostEqual(p["part_grupo"].iloc[0], 1.0)


class TesteKpisInterseccionais(unittest.TestCase):
    def perfil(self):
        # AC: 40 de 100 sao mulheres pretas. AM: 10 de 100
        return pd.DataFrame({
            "uf": ["AC", "AC", "AM", "AM"],
            "sexo": ["Mulheres", "Homens", "Mulheres", "Homens"],
            "cor_raca": ["Preta", "Preta", "Preta", "Branca"],
            "ocupados": [40, 60, 10, 90],
        })

    def test_participacao_pondera_pelo_numero_de_pessoas(self):
        # (40 + 10) mulheres pretas em 200 pessoas = 25%
        p = contas.participacao_ponderada(self.perfil(), ["AC", "AM"], "Mulheres", ["Preta"])
        self.assertAlmostEqual(p, 0.25)

    def test_participacao_so_das_ufs_escolhidas(self):
        p = contas.participacao_ponderada(self.perfil(), ["AC"], "Mulheres", ["Preta"])
        self.assertAlmostEqual(p, 0.40)

    def test_participacao_sem_ufs_da_nan(self):
        p = contas.participacao_ponderada(self.perfil(), [], "Mulheres", ["Preta"])
        self.assertTrue(p != p)

    def pontos(self, part, valor):
        return pd.DataFrame({"part_pct": part, "carteira_por_ocupado": valor})

    def test_razao_compara_ufs_com_mais_e_menos_o_grupo(self):
        # participacao baixa: carteira 100 e 200. alta: carteira 300 e 500
        # mediana baixa = 150, mediana alta = 400, razao = 400 / 150
        r = contas.razao_alta_baixa(self.pontos([10, 20, 60, 80], [100, 200, 300, 500]))
        self.assertAlmostEqual(r, 400 / 150)

    def test_razao_precisa_de_4_ufs(self):
        self.assertIsNone(contas.razao_alta_baixa(self.pontos([10, 50, 90], [1, 2, 3])))

    def test_razao_sem_variacao_na_participacao_nao_compara(self):
        # todas iguais: nenhuma fica acima da mediana
        self.assertIsNone(contas.razao_alta_baixa(self.pontos([30, 30, 30, 30], [1, 2, 3, 4])))


class TesteRotulo(unittest.TestCase):
    def test_plural_certo_para_cada_sexo(self):
        self.assertEqual(contas.rotulo_grupo("Mulheres", ["Preta", "Parda"]), "Mulheres pretas e pardas")
        self.assertEqual(contas.rotulo_grupo("Homens", ["Preta", "Parda"]), "Homens pretos e pardos")
        self.assertEqual(contas.rotulo_grupo("Todos", ["Preta"]), "Pessoas pretas")

    def test_sem_cor_e_sem_sexo(self):
        self.assertEqual(contas.rotulo_grupo("Mulheres", []), "Mulheres")
        self.assertEqual(contas.rotulo_grupo("Todos", []), "Ocupados")

    def test_tres_cores(self):
        self.assertEqual(contas.rotulo_grupo("Mulheres", ["Branca", "Preta", "Parda"]), "Mulheres brancas, pretas e pardas")


class TesteFormato(unittest.TestCase):
    def test_numero_em_portugues(self):
        self.assertEqual(contas.fmt_num(1234567.891, 2), "1.234.567,89")

    def test_reais_em_bilhoes_e_milhoes(self):
        self.assertEqual(contas.fmt_reais(9_440_000_000), "R$ 9,44 bi")
        self.assertEqual(contas.fmt_reais(2_500_000), "R$ 2,5 mi")


class TesteSpearman(unittest.TestCase):
    def test_ordem_igual_da_1_e_invertida_da_menos_1(self):
        x = pd.Series([1, 2, 3, 4])
        self.assertAlmostEqual(contas.spearman(x, pd.Series([10, 20, 30, 40])), 1.0)
        self.assertAlmostEqual(contas.spearman(x, pd.Series([40, 30, 20, 10])), -1.0)


if __name__ == "__main__":
    unittest.main()
