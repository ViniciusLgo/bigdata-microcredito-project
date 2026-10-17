# Projeto Big Data - Microcredito e Inclusao Financeira Regional

Trabalho da disciplina de Big Data e Analytics (UCSal). Tema 05: Acesso a Microcredito e Inclusao Financeira Regional, usando dados abertos do Banco Central.

Integrantes: Vinicius Lago Cruz, Roberto Luis Jr., Guilherme Chaves, Maria Fernanda Prandi.

## Fontes

- **API SGS** (Banco Central): series nacionais de microcredito, series 20618 e 20712.
- **SCR.data** (Banco Central): credito por UF, modalidade e tipo de cliente. Os ZIPs mensais (2021 a 2026) foram baixados do Portal de Dados Abertos do BCB e filtrados para as 27 UFs, so submodalidade Microcredito.

## Estrutura

```
etl/
  extrair_sgs.py      # baixa as series da API SGS
  filtrar_scr.py      # filtra os zips do SCR.data com pandas chunking
  tratar.py           # converte tipos e agrega por UF, segmento, modalidade e mes
  carregar.py         # cria o schema e carrega no Postgres (Aiven)
  verificar_banco.py  # mostra tabelas, campos, relacionamentos e contagens
sql/
  schema.sql          # estrutura do banco
data/
  zip/       # zips originais do SCR.data (nao vai pro git, muito grande)
  raw/       # json da SGS e csv filtrado (o csv nao vai pro git)
  processed/ # csv final, pronto pra carga
  amostra/   # 20 linhas antes e depois do tratamento
```

## Como rodar

```bash
pip install -r requirements.txt

python etl/extrair_sgs.py
python etl/filtrar_scr.py
python etl/tratar.py

export AIVEN_PG_URL="postgres://usuario:senha@host:porta/defaultdb?sslmode=require"
python etl/carregar.py
python etl/verificar_banco.py
```

## Banco de dados

Esquema estrela no PostgreSQL (Aiven, plano gratuito):

- `dim_uf` e `dim_modalidade` - dimensoes
- `fato_microcredito_nacional` - series nacionais da API SGS
- `fato_credito_regional` - dados do SCR.data, 27 UFs, PF e PJ, a partir de 2021
