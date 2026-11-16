"""
test_tratamento.py

Testes das funcoes que convertem numero no etl/tratar.py. Nao precisam de
banco nem dos csvs grandes.

Rodar (da raiz do projeto):
    python -m unittest tests.test_tratamento -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "etl"))
import tratar  # noqa: E402


class TesteNumeroScr(unittest.TestCase):
    def test_milhar_com_ponto_e_decimal_com_virgula(self):
        self.assertEqual(tratar.numero_scr("1.234,56"), 1234.56)

    def test_numero_sem_separador(self):
        self.assertEqual(tratar.numero_scr("42"), 42.0)

    def test_so_decimal(self):
        self.assertEqual(tratar.numero_scr("0,05"), 0.05)

    def test_negativo(self):
        self.assertEqual(tratar.numero_scr("-32"), -32.0)

    def test_vazio_vira_nulo(self):
        self.assertIsNone(tratar.numero_scr(""))
        self.assertIsNone(tratar.numero_scr("   "))
        self.assertIsNone(tratar.numero_scr(None))


class TesteNumeroSgs(unittest.TestCase):
    def test_inteiro(self):
        # e assim que vem nos json que a gente tem hoje
        self.assertEqual(tratar.numero_sgs("6939"), 6939.0)

    def test_ponto_e_decimal_nao_milhar(self):
        # com a funcao do scr isso viraria 12345
        self.assertEqual(tratar.numero_sgs("123.45"), 123.45)

    def test_vazio_vira_nulo(self):
        self.assertIsNone(tratar.numero_sgs(""))
        self.assertIsNone(tratar.numero_sgs(None))


class TesteDiferencaEntreAsDuas(unittest.TestCase):
    def test_a_mesma_string_da_numero_diferente(self):
        # mostra porque a gente separou as duas funcoes
        self.assertEqual(tratar.numero_scr("123.45"), 12345.0)
        self.assertEqual(tratar.numero_sgs("123.45"), 123.45)


if __name__ == "__main__":
    unittest.main()
