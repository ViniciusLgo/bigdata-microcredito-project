# filtrar_scr.py
# Essa e a parte mais pesada do pipeline. O SCR.data vem em zips mensais com
# todo o Brasil e todas as modalidades de credito (cada csv tem uns 85-90MB),
# e o plano gratis do Postgres na Aiven so aguenta 1GB no total. Entao a
# gente usa Pandas Chunking (lendo o csv em pedacos, sem carregar tudo na
# memoria de uma vez) pra ja filtrar linha por linha enquanto le, em vez de
# abrir o arquivo inteiro.
#
# dois filtros aplicados aqui:
#   - uf tem que ser uma das 27 UFs do Brasil (antes era so Nordeste, depois
#     ampliamos pro pais todo porque o volume agregado cabe folgado no 1GB)
#   - submodalidade tem que ser "Microcredito" (olhando o cabecalho do csv
#     real do bcb, nao existe uma coluna "modalidade = microcredito", o
#     microcredito aparece dentro da coluna submodalidade)
#
# o resultado sai bem menor que o original e vai pra data/raw/, pra depois
# o tratar_scr.py fazer a agregacao final.

import os
import zipfile
import pandas as pd

PASTA_ZIP = os.path.join(os.path.dirname(__file__), "..", "data", "zip")
PASTA_RAW = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
SAIDA = os.path.join(PASTA_RAW, "scr_microcredito_brasil_raw.csv")

UFS_BRASIL = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT",
    "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
]

TAMANHO_CHUNK = 200_000  # linhas por pedaco


def processar_zip(caminho_zip, primeiro_arquivo):
    with zipfile.ZipFile(caminho_zip) as z:
        nomes = [n for n in z.namelist() if n.endswith(".csv")]
        for nome in nomes:
            print("  lendo", nome)
            with z.open(nome) as f:
                leitor = pd.read_csv(
                    f,
                    sep=";",
                    encoding="utf-8-sig",
                    chunksize=TAMANHO_CHUNK,
                    dtype=str,
                )
                for pedaco in leitor:
                    filtrado = pedaco[
                        pedaco["uf"].isin(UFS_BRASIL)
                        & (pedaco["submodalidade"] == "Microcrédito")
                    ]
                    if not filtrado.empty:
                        filtrado.to_csv(
                            SAIDA,
                            mode="a",
                            index=False,
                            header=primeiro_arquivo[0],
                            sep=";",
                        )
                        primeiro_arquivo[0] = False


if __name__ == "__main__":
    os.makedirs(PASTA_RAW, exist_ok=True)
    if os.path.exists(SAIDA):
        os.remove(SAIDA)

    zips = sorted(f for f in os.listdir(PASTA_ZIP) if f.endswith(".zip"))
    primeiro = [True]  # lista so pra poder mudar o valor dentro da funcao
    for nome_zip in zips:
        print("processando", nome_zip)
        processar_zip(os.path.join(PASTA_ZIP, nome_zip), primeiro)

    print("pronto, resultado em", SAIDA)
