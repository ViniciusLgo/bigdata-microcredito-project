# extrair_sgs.py
# Baixa as duas series de microcredito do Banco Central (API SGS) e salva o
# JSON cru em data/raw/. Essa parte da base e so pra ter numeros nacionais
# como referencia, a base principal mesmo e a do SCR.data (ver filtrar_scr.py).
#
# series escolhidas (ver Etapa 1 do trabalho):
# 20618 -> saldo da carteira PF em microcredito a microempreendedores
# 20712 -> concessoes de microcredito PF

import os
import requests

PASTA_RAW = os.path.join(os.path.dirname(__file__), "..", "data", "raw")

series = {
    20618: "saldo carteira PF - microcredito a microempreendedores",
    20712: "concessoes PF - microcredito total",
}

data_inicial = "01/01/2021"  # mesmo recorte temporal que a gente definiu na etapa 1


def baixar(serie_id):
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie_id}/dados?formato=json&dataInicial={data_inicial}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.text


if __name__ == "__main__":
    os.makedirs(PASTA_RAW, exist_ok=True)
    for serie_id, nome in series.items():
        print(f"baixando serie {serie_id} ({nome})")
        conteudo = baixar(serie_id)
        caminho = os.path.join(PASTA_RAW, f"sgs_{serie_id}.json")
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(conteudo)
        print("salvo em", caminho)
