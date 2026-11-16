"""Gera data/ibge_ocupacao_uf_2022.csv a partir dos valores lidos da API do IBGE.

Fonte: IBGE, Censo Demografico 2022, Amostra - Trabalho e Rendimento.
Tabela SIDRA 10261, variavel 4090 (pessoas), periodo 2022, nivel N3 (UF).
Recorte: posicao na ocupacao 79377 (Empregador com pelo menos um empregado)
+ 79378 (Conta propria sem empregados).
Consulta feita em 05/11/2026 via
https://servicodados.ibge.gov.br/api/v3/agregados/10261/periodos/2022/variaveis/4090
"""
import csv
import os

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

# nome_uf: (total, homens, mulheres, branca, preta, amarela, parda, indigena)
DADOS = {
    "Acre": (83402, 58150, 25251, 17230, 9528, 235, 54668, 1740),
    "Alagoas": (306576, 199588, 106989, 89992, 34534, 682, 179522, 1810),
    "Amapá": (88123, 59429, 28694, 16650, 12778, 79, 57368, 1247),
    "Amazonas": (467806, 310364, 157441, 79378, 31454, 881, 326507, 29547),
    "Bahia": (1738847, 1135143, 603705, 355796, 415990, 2853, 951535, 12520),
    "Ceará": (1022319, 661163, 361157, 287919, 85340, 1653, 642758, 4375),
    "Distrito Federal": (330589, 196189, 134399, 131260, 39152, 1463, 157865, 735),
    "Espírito Santo": (567573, 356716, 210857, 252750, 58671, 898, 253546, 1662),
    "Goiás": (974436, 631287, 343149, 381757, 89272, 3230, 498516, 1472),
    "Maranhão": (777484, 520720, 256764, 159787, 122057, 956, 490328, 4251),
    "Mato Grosso": (471351, 319095, 152256, 181040, 46167, 2060, 239447, 2594),
    "Mato Grosso do Sul": (339600, 217340, 122260, 160018, 22329, 3359, 149013, 4848),
    "Minas Gerais": (2761007, 1800106, 960901, 1274611, 296656, 5859, 1180250, 3268),
    "Paraná": (1735074, 1112869, 622204, 1174027, 70778, 20443, 466599, 3134),
    "Paraíba": (421186, 281174, 140012, 151936, 38263, 620, 226904, 3445),
    "Pará": (1045614, 717042, 328572, 199177, 118943, 2034, 719064, 6141),
    "Pernambuco": (1076050, 684955, 391095, 369201, 119434, 2074, 575379, 9788),
    "Piauí": (362154, 240310, 121845, 83743, 50943, 480, 226344, 639),
    "Rio Grande do Norte": (375369, 246659, 128710, 146349, 40932, 685, 186021, 1369),
    "Rio Grande do Sul": (1660222, 1031096, 629126, 1373325, 78590, 1381, 203065, 3805),
    "Rio de Janeiro": (2088224, 1249680, 838545, 916187, 327258, 3634, 837486, 3302),
    "Rondônia": (221345, 153797, 67548, 70991, 21257, 851, 126515, 1709),
    "Roraima": (68306, 47243, 21063, 14342, 7126, 95, 41860, 4873),
    "Santa Catarina": (1195119, 740359, 454760, 967691, 37279, 2583, 185228, 2135),
    "Sergipe": (274453, 172536, 101917, 69972, 38518, 423, 164744, 715),
    "São Paulo": (5928294, 3636112, 2292182, 3579457, 462770, 93037, 1781194, 9997),
    "Tocantins": (173855, 118132, 55722, 46265, 24040, 568, 101877, 1064),
}

CAMPOS = [
    "uf", "nome_uf", "ocupados_empregador_contapropria", "homens", "mulheres",
    "branca", "preta", "amarela", "parda", "indigena",
    "part_mulheres", "part_preta_parda",
]

if __name__ == "__main__":
    linhas = []
    for nome, (total, h, m, br, pr, am, pa, ind) in sorted(DADOS.items()):
        soma_sexo = h + m
        soma_cor = br + pr + am + pa + ind
        linhas.append({
            "uf": SIGLA[nome], "nome_uf": nome,
            "ocupados_empregador_contapropria": total,
            "homens": h, "mulheres": m,
            "branca": br, "preta": pr, "amarela": am, "parda": pa, "indigena": ind,
            "part_mulheres": round(m / soma_sexo, 6),
            "part_preta_parda": round((pr + pa) / soma_cor, 6),
        })
    linhas.sort(key=lambda r: r["uf"])
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "ibge_ocupacao_uf_2022.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(linhas)
    print(f"data/ibge_ocupacao_uf_2022.csv: {len(linhas)} linhas")
