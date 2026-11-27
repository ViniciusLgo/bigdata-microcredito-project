"""Testes da aplicação real usando a API pública Streamlit AppTest.

Instalar dashboard/requirements.txt antes de executar. Não acessam a Aiven:
variável de ambiente e segredo de conexão ficam vazios na sessão simulada.
Documentação: https://docs.streamlit.io/develop/api-reference/app-testing
"""

import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import pandas as pd

try:
    import plotly.express as px
    import streamlit as st
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None

PASTA_DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard"
sys.path.insert(0, str(PASTA_DASHBOARD))


@unittest.skipIf(AppTest is None, "Instale dashboard/requirements.txt para executar os testes AppTest.")
class DashboardAppTest(unittest.TestCase):
    def setUp(self):
        ambiente = patch.dict(os.environ, {"AIVEN_PG_URL": ""})
        ambiente.start()
        self.addCleanup(ambiente.stop)
        st.cache_data.clear()
        self.at = AppTest.from_file(PASTA_DASHBOARD / "app.py", default_timeout=30)
        self.at.secrets["AIVEN_PG_URL"] = ""
        self.at.run()
        self.assert_sem_erro()

    def widget(self, colecao, rotulo):
        encontrados = [elemento for elemento in colecao if elemento.label == rotulo]
        self.assertEqual(len(encontrados), 1, f"Widget não encontrado: {rotulo}")
        return encontrados[0]

    def assert_sem_erro(self):
        self.assertEqual(len(self.at.exception), 0, str(self.at.exception))
        self.assertEqual(len(self.at.error), 0, str(self.at.error))

    def tabela_recorte(self):
        tabelas = [elemento.value for elemento in self.at.dataframe]
        return next(tabela for tabela in tabelas if "valor_carteira_ativa" in tabela.columns)

    @staticmethod
    def series_sgs(chamadas):
        # Observa os dados enviados à API pública do Plotly. Evita acessar
        # estruturas privadas/protobuf do Streamlit para gráficos Plotly.
        return [chamada.args[0] for chamada in chamadas
                if chamada.args and isinstance(chamada.args[0], pd.DataFrame)
                and "serie_id" in chamada.args[0].columns]

    def test_abertura_padrao_exibe_fontes_e_indicadores(self):
        self.assertEqual(self.at.title[0].value, "Microcrédito no Brasil")
        self.assertEqual(len(self.at.metric), 8)
        self.assertEqual(len(self.tabela_recorte()), 7081)
        self.assertTrue(any("arquivos CSV" in item.value for item in self.at.caption))
        self.assertTrue(any("falácia ecológica" in item.value for item in self.at.info))

    def test_recorte_sem_registros_exibe_estado_vazio(self):
        self.widget(self.at.multiselect, "Estado (UF)").set_value(["AC"])
        self.widget(self.at.multiselect, "Tipo de cliente").set_value(["PJ"])
        self.widget(self.at.multiselect, "Modalidade").set_value(["Financiamentos - Microcrédito"])
        self.widget(self.at.select_slider, "Período mensal").set_range("2021-01", "2021-01")
        self.at.run()
        self.assert_sem_erro()
        self.assertTrue(any("Não há registros neste recorte" in item.value for item in self.at.info))
        self.assertEqual(len(self.at.metric), 0)

    def test_periodos_anual_e_mensal_limitam_os_graficos_sgs(self):
        ods_antes = {item.label: item.value for item in self.at.metric[4:]}
        for inicio, fim, quantidade in [("2022-01", "2022-12", 12), ("2022-06", "2022-06", 1)]:
            with self.subTest(inicio=inicio, fim=fim):
                self.widget(self.at.select_slider, "Período mensal").set_range(inicio, fim)
                with patch.object(px, "line", wraps=px.line) as line:
                    self.at.run()
                self.assert_sem_erro()
                series = self.series_sgs(line.call_args_list)
                self.assertEqual(len(series), 2)
                self.assertEqual({int(s.serie_id.iloc[0]) for s in series}, {20618, 20712})
                for serie in series:
                    self.assertEqual(len(serie), quantidade)
                    meses = serie.data_referencia.dt.strftime("%Y-%m")
                    self.assertTrue(meses.between(inicio, fim).all())
                meses_regionais = self.tabela_recorte().data_referencia.dt.strftime("%Y-%m")
                self.assertTrue(meses_regionais.between(inicio, fim).all())
                # ODS continua com referência fixa em 2022, mesmo com um só
                # mês selecionado na análise temporal.
                self.assertEqual({item.label: item.value for item in self.at.metric[4:]}, ods_antes)

    def test_perfil_constante_nao_exibe_nan_ou_infinito(self):
        self.widget(self.at.selectbox, "Sexo no perfil territorial").set_value("Todos")
        self.widget(self.at.multiselect, "Cor ou raça no perfil territorial").set_value([])
        with patch.object(px, "scatter", wraps=px.scatter) as scatter:
            self.at.run()
        self.assert_sem_erro()
        self.assertEqual(len(scatter.call_args_list), 1)
        pontos = scatter.call_args.args[0]
        self.assertTrue(pontos.part_pct.eq(100).all())
        for metric in self.at.metric:
            self.assertNotRegex(str(metric.value).lower(), r"\b(?:nan|inf|infinity)\b")
        razao = self.widget(self.at.metric, "Razão maior / menor presença")
        self.assertEqual(razao.value, "Indisponível")
        self.assertTrue(any("Correlação não calculável" in item.value for item in self.at.caption))

    def test_uf_unica_filtra_tabela_e_trata_comparacao_ods(self):
        self.widget(self.at.multiselect, "Estado (UF)").set_value(["BA"])
        self.at.run()
        self.assert_sem_erro()
        tabela = self.tabela_recorte()
        self.assertFalse(tabela.empty)
        self.assertEqual(set(tabela.uf), {"BA"})
        self.assertTrue(any("1 UFs no recorte" in item.value for item in self.at.caption))
        self.assertEqual(self.widget(self.at.metric, "Razão maior / menor presença").value, "Indisponível")
        self.assertTrue(any("Correlação não calculável" in item.value for item in self.at.caption))


if __name__ == "__main__":
    unittest.main()
