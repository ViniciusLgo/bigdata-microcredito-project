# baixar_ibge.py
# Baixa do IBGE quantas pessoas trabalham por conta propria ou como empregador
# em cada UF, separado por sexo e por cor ou raca.
#
# fonte: Censo 2022 (amostra, trabalho e rendimento), tabela SIDRA 10261,
# variavel 4090 (pessoas de 14 anos ou mais ocupadas), nivel estadual.
#
# a api ja devolve sexo e raca cruzados, entao da pra saber quantas mulheres
# pretas e pardas tem em cada estado (e nao so o total de mulheres e o total
# de pretos e pardos separados). some as duas posicoes na ocupacao: empregador
# com pelo menos um empregado e conta propria sem empregados.
#
# gera data/ibge_sexo_raca_uf_2022.csv
# uso: python analise/baixar_ibge.py

import csv
import os
import requests

URL = "https://servicodados.ibge.gov.br/api/v3/agregados/10261/periodos/2022/variaveis/4090"

# 79377 empregador, 79378 conta propria
# 4 homens, 5 mulheres
# 2776 branca, 2777 preta, 2778 amarela, 2779 parda, 2780 indigena
CLASSIFICACAO = "11913[79377,79378]|2[4,5]|86[2776,2777,2778,2779,2780]"

SIGLA = {
    "Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM", "Bahia": "BA",
    "Ceará": "CE", "Distrito Federal": "DF", "Espírito Santo": "ES", "Goiás": "GO",
    "Maranhão": "MA", "Mato Grosso": "MT", "Mato Grosso do Sul": "MS",
    "Minas Gerais": "MG", "Paraná": "PR", "Paraíba": "PB", "Pará": "PA",
    "Pernambuco": "PE", "Piauí": "PI", "Rio Grande do Norte": "RN",
    "Rio Grande do Sul": "RS", "Rio de Janeiro": "RJ", "Rondônia": "RO",
    "Roraima": "RR", "Santa Catarina": "SC", "Sergipe": "SE", "São Paulo": "SP",
    "Tocantins": "TO",
}

DESTINO = os.path.join(os.path.dirname(__file__), "..", "data", "ibge_sexo_raca_uf_2022.csv")


def numero(texto):
    # o ibge manda "-" ou "X" quando o valor e zero ou esta protegido
    try:
        return int(texto)
    except (TypeError, ValueError):
        return 0


def baixar():
    # a api aceita colchete e barra vertical no endereco, por isso monto na mao
    url = f"{URL}?localidades=N3[all]&classificacao={CLASSIFICACAO}"
    resposta = requests.get(url, timeout=120)
    resposta.raise_for_status()
    return resposta.json()[0]["resultados"]


def somar(resultados):
    soma = {}
    for r in resultados:
        categorias = [list(c["categoria"].values())[0] for c in r["classificacoes"]]
        sexo, cor = categorias[1], categorias[2]
        for s in r["series"]:
            uf = SIGLA[s["localidade"]["nome"]]
            chave = (uf, sexo, cor)
            soma[chave] = soma.get(chave, 0) + numero(s["serie"]["2022"])
    return soma


if __name__ == "__main__":
    soma = somar(baixar())
    with open(DESTINO, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["uf", "ano", "sexo", "cor_raca", "ocupados"])
        for (uf, sexo, cor), n in sorted(soma.items()):
            w.writerow([uf, 2022, sexo, cor, n])
    print(f"{len(soma)} linhas em data/ibge_sexo_raca_uf_2022.csv")
