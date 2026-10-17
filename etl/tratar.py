# tratar.py
# Pega o que o extrair_sgs.py e o filtrar_scr.py geraram e transforma na
# versao final que vai pro banco. Aqui que entram as conversoes de tipo que
# a gente mapeou na etapa 1 (string com virgula -> decimal, data em texto ->
# date, etc).

import os
import json
import pandas as pd
from datetime import datetime

PASTA_RAW = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
PASTA_PROC = os.path.join(os.path.dirname(__file__), "..", "data", "processed")

SERIES_SGS = {
    20618: "saldo carteira PF - microcredito a microempreendedores",
    20712: "concessoes PF - microcredito total",
}


def numero_br(valor):
    # o bcb manda valor monetario tipo "1.234,56", precisa trocar o separador
    if pd.isna(valor) or str(valor).strip() == "":
        return None
    return float(str(valor).replace(".", "").replace(",", "."))


def tratar_sgs():
    linhas = []
    for serie_id, nome in SERIES_SGS.items():
        caminho = os.path.join(PASTA_RAW, f"sgs_{serie_id}.json")
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
        for item in dados:
            linhas.append({
                "serie_id": serie_id,
                "descricao_serie": nome,
                "data_referencia": datetime.strptime(item["data"], "%d/%m/%Y").date(),
                "valor": numero_br(item["valor"]),
            })
    df = pd.DataFrame(linhas)
    destino = os.path.join(PASTA_PROC, "fato_microcredito_nacional.csv")
    df.to_csv(destino, index=False)
    print(f"fato_microcredito_nacional: {len(df)} linhas -> {destino}")
    return df


def tratar_scr():
    origem = os.path.join(PASTA_RAW, "scr_microcredito_brasil_raw.csv")
    if not os.path.exists(origem):
        print("faltou rodar o filtrar_scr.py antes, nao achei", origem)
        return None

    df = pd.read_csv(origem, sep=";", dtype=str)

    # so os campos numericos que a gente precisa mesmo, o resto (cnae, porte,
    # segmento etc) fica fora da agregacao final pra nao gerar milhares de
    # combinacoes desnecessarias (decisao que ja tinha sido tomada na etapa 1)
    for col in ["numero_de_operacoes", "carteira_ativa", "carteira_inadimplencia"]:
        df[col] = df[col].apply(numero_br)

    df["data_referencia"] = pd.to_datetime(df["data_base"].str.strip('"')).dt.date
    df["modalidade"] = df["modalidade"].str.strip('"') + " - " + df["submodalidade"].str.strip('"')
    df["uf"] = df["uf"].str.strip('"')
    # a coluna "cliente" do bcb diz se a linha e pessoa fisica (PF) ou juridica (PJ).
    # se nao separar aqui, o groupby soma PF com PJ e o numero perde o sentido
    df["segmento"] = df["cliente"].str.strip('"')

    agregado = (
        df.groupby(["uf", "segmento", "modalidade", "data_referencia"], as_index=False)
        .agg(
            valor_carteira_ativa=("carteira_ativa", "sum"),
            valor_inadimplencia=("carteira_inadimplencia", "sum"),
            quantidade_operacoes=("numero_de_operacoes", "sum"),
        )
    )

    # taxa de inadimplencia = inadimplencia / carteira ativa (nao vem pronta
    # no arquivo do bcb, a gente que calcula)
    agregado["taxa_inadimplencia"] = agregado.apply(
        lambda r: round(r["valor_inadimplencia"] / r["valor_carteira_ativa"], 4)
        if r["valor_carteira_ativa"] else None,
        axis=1,
    )
    agregado = agregado.drop(columns=["valor_inadimplencia"])

    destino = os.path.join(PASTA_PROC, "fato_credito_regional.csv")
    agregado.to_csv(destino, index=False)
    print(f"fato_credito_regional: {len(agregado)} linhas -> {destino}")
    return agregado


if __name__ == "__main__":
    os.makedirs(PASTA_PROC, exist_ok=True)
    tratar_sgs()
    tratar_scr()
