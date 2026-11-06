# Projeto Big Data — Microcrédito e Inclusão Financeira Regional

Trabalho da disciplina de Big Data e Analytics (UCSal). Tema 05: Acesso a Microcrédito e
Inclusão Financeira Regional, usando dados abertos do Banco Central do Brasil.

Integrantes: Vinicius Lago Cruz, Roberto Luis Jr., Guilherme Chaves, Maria Fernanda Prandi.

---

## O que o projeto faz

Pipeline em Python que baixa, filtra, trata e carrega dados públicos de microcrédito num
PostgreSQL em nuvem, para análise regional por UF.

```
ZIPs anuais do SCR.data  ──filtro em chunks──►  CSV intermediário  ──agregação──►  fato regional  ─┐
                                                                                                   ├──►  PostgreSQL (Aiven)
API SGS (2 séries)       ──────────────────►  JSON bruto          ──conversão──►  fato nacional  ─┘
```

Recorte atual: **27 UFs, submodalidade Microcrédito, janeiro/2021 a julho/2026** (a série
nacional vai até agosto/2026).

---

## Fontes

| Fonte | Conteúdo | URL |
|---|---|---|
| **SCR.data** (BCB, versão 2) | Crédito agregado por UF, tipo de cliente, modalidade e mês. ZIPs anuais com os CSVs mensais. | `https://www.bcb.gov.br/pda/desig/scrdata_{ANO}.zip` |
| **API SGS** (BCB) | Séries nacionais mensais de microcrédito: **20618** (saldo da carteira PF — microcrédito a microempreendedores) e **20712** (concessões PF — microcrédito total), ambas em **milhões de reais**. | `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados?formato=json` |

Metodologia do SCR.data: <https://www.bcb.gov.br/pda/desig/metodologia_versao2.pdf>
Licença dos dados: Open Data Commons ODbL (SCR.data).

**Procedência completa — URLs, períodos, tamanhos, SHA-256 e datas — em
[`data/manifesto-fontes.csv`](data/manifesto-fontes.csv).**

Os ZIPs do SCR.data não vão para o Git (quase 1 GB no total). Para refazer o download,
baixe um ZIP por ano de 2021 a 2026 pela URL acima e coloque-os em `data/zip/`. Cada ZIP
contém os CSVs mensais daquele ano, separados por `;`.

---

## Estrutura

```
etl/
  extrair_sgs.py       # baixa as séries 20618 e 20712 da API SGS
  filtrar_scr.py       # filtra os ZIPs do SCR.data lendo os CSVs em chunks de 200.000 linhas
  tratar.py            # converte tipos e agrega por UF, cliente (PF/PJ), modalidade e mês
  carregar.py          # cria o schema e carrega no PostgreSQL (Aiven)
  verificar_banco.py   # mostra tabelas, campos, relacionamentos, contagens e tamanho
sql/
  schema.sql           # estrutura do banco
data/
  manifesto-fontes.csv       # procedência e versão de cada insumo
  ibge_ocupacao_uf_2022.csv  # base do IBGE por UF usada na análise das ODS
  zip/                       # ZIPs originais do SCR.data (fora do Git, muito grandes)
  raw/                       # JSONs da SGS e o CSV filtrado (o CSV fica fora do Git)
  processed/                 # CSVs finais, prontos para a carga
  amostra/                   # 20 linhas antes e depois do tratamento
analise/
  ods_cruzamento.py    # cruzamento territorial com o IBGE para as ODS 5 e 18
docs/
  DICIONARIO_DADOS.md  # campos, tipos, chaves, origem, unidades e o que a base não tem
  DECISOES_TECNICAS.md # decisões de tratamento e modelagem, limites e encaminhamento das ODS
  ODS_ANALISE.md       # resultado do cruzamento com o IBGE, com método e ressalvas
  CHECKLIST_ENTREGA.md # cada item do enunciado e o arquivo que o comprova
  evidencias/          # saídas datadas das execuções, sem credenciais
```

---

## Como rodar

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python etl/extrair_sgs.py        # gera data/raw/sgs_20618.json e sgs_20712.json
# coloque os ZIPs anuais em data/zip/ antes do passo seguinte
python etl/filtrar_scr.py        # gera data/raw/scr_microcredito_brasil_raw.csv
python etl/tratar.py             # gera os dois CSVs em data/processed/
```

Carga e conferência do banco (a URL de conexão fica **só** em variável de ambiente, nunca
no código nem no Git):

```bash
export AIVEN_PG_URL="postgres://usuario:senha@host:porta/defaultdb?sslmode=require"
python etl/carregar.py
python etl/verificar_banco.py
```

> ⚠️ **Não rode `etl/carregar.py` contra o banco compartilhado do grupo.** Hoje ele executa
> `sql/schema.sql` em toda execução, e o schema começa com `DROP TABLE ... CASCADE`: a
> carga apaga e recria as tabelas. A separação entre criação e carga é uma correção em
> andamento. Até lá, use um banco descartável para testar.

Análise das ODS 5 e 18 (não precisa de banco, só dos CSVs versionados):

```bash
pip install scipy matplotlib
python analise/ods_cruzamento.py
```

Conferência rápida dos CSVs versionados, sem precisar de banco:

```bash
sha256sum data/processed/*.csv data/raw/*.json   # compare com data/manifesto-fontes.csv
```

---

## Banco de dados

Modelo dimensional simplificado no PostgreSQL (Aiven, plano gratuito), com duas dimensões
e **duas tabelas fato independentes**:

| Tabela | Grão | Linhas esperadas |
|---|---|---|
| `dim_uf` | UF | 27 |
| `dim_modalidade` | modalidade × segmento (PF/PJ) | 4 |
| `fato_credito_regional` | UF × segmento × modalidade × mês | 7.080 |
| `fato_microcredito_nacional` | série × mês | 136 |
| | **total** | **7.247** |

`fato_credito_regional` se liga às duas dimensões por chave estrangeira.
`fato_microcredito_nacional` não se liga a nenhuma: é a série nacional do SGS, com outro
grão e outra fonte. Não há junção entre pessoas nem identificação de tomadores.

Detalhe de cada campo em [`docs/DICIONARIO_DADOS.md`](docs/DICIONARIO_DADOS.md).

---

## Como ler os números (antes de analisar)

| O número | O que é | O que **não** é |
|---|---|---|
| `quantidade_operacoes` | operações de crédito | clientes ou tomadores |
| `valor_carteira_ativa` | saldo no fim do mês | valor concedido no mês |
| `taxa_inadimplencia` | fração de 0 a 1 — **0,05 = 5%** | percentual já multiplicado por 100 |
| séries 20618 / 20712 | valores em **milhões de reais**, só PF, só crédito direcionado | mesma unidade e abrangência do recorte regional |
| `segmento` (nosso) | PF ou PJ — vem da coluna `cliente` do SCR.data | o campo `segmento` do SCR.data, que é o segmento da instituição financeira |

Datas: o regional usa o **último dia** do mês; o nacional usa o **dia 01**. Para comparar
as duas séries, alinhe a competência e restrinja ao período comum (jan/2021 a jul/2026).

---

## O que a análise territorial mostrou

Resumo de [`docs/ODS_ANALISE.md`](docs/ODS_ANALISE.md), referente a 2022:

- **O microcrédito do país é concentrado:** as 9 UFs do Nordeste respondem por **62,1%** da
  carteira nacional, com mediana de R$ 1.236 por ocupado por conta própria ou empregador,
  contra R$ 167 a R$ 240 nas demais regiões.
- **ODS 18:** UFs com maior participação de pessoas pretas e pardas têm mais microcrédito
  por ocupado (Spearman ρ = 0,455, p = 0,017) — mas a relação perde significância ao
  excluir o Nordeste (ρ = 0,358, p = 0,145). A correlação reflete **onde a oferta está**,
  não acesso por grupo racial.
- **ODS 5:** não há associação detectável com a participação de mulheres (ρ = −0,227,
  p = 0,255). A base não tem sexo, então o que se mede é o território, e nele nada aparece.
- **Achado mais forte, fora dos ODS:** quanto maior a densidade de microcrédito, menor a
  inadimplência (ρ = −0,871, p < 0,0001) — Piauí tem R$ 2.297 por ocupado e 5,9% de
  inadimplência; Rio de Janeiro, R$ 113 e 22,4%.

---

## Limitações conhecidas

- A base **não contém sexo, gênero, cor ou raça**. Nenhuma afirmação sobre desigualdade de
  acesso por esses grupos pode ser sustentada só com estes dados. A saída adotada foi uma
  análise **territorial** cruzando a carteira por UF com o Censo 2022 do IBGE — ver
  [`docs/ODS_ANALISE.md`](docs/ODS_ANALISE.md). Ela descreve territórios, não o perfil de
  quem tomou crédito; concluir sobre indivíduos a partir de médias por UF é falácia
  ecológica.
- **1.084 das 7.080 linhas (15,3%) têm `quantidade_operacoes` negativa** (mínimo −32). A
  metodologia do BCB não publica regra de supressão para esse campo. Os valores foram
  mantidos como vieram e o indicador principal do trabalho é a carteira ativa, não a
  contagem de operações.
- A metodologia do SCR.data **não declara** a unidade monetária de `carteira_ativa`; o
  projeto a trata como reais por inferência de ordem de grandeza.
- Só a filtragem usa chunks. O tratamento abre o CSV intermediário inteiro, então o
  pipeline é lote com leitura particionada, **não** processamento distribuído.
- `etl/extrair_sgs.py` não fixa `dataFinal`: cada execução traz meses novos. Para
  reproduzir exatamente a versão analisada, use os JSONs versionados no repositório.
- Camada não relacional (OpenSearch) não implementada — é opcional no guia.

---

## Documentação

| Arquivo | Para quê |
|---|---|
| [`data/manifesto-fontes.csv`](data/manifesto-fontes.csv) | de onde veio cada arquivo, qual versão e com qual hash |
| [`docs/DICIONARIO_DADOS.md`](docs/DICIONARIO_DADOS.md) | o que é cada campo, em cada camada |
| [`docs/DECISOES_TECNICAS.md`](docs/DECISOES_TECNICAS.md) | por que o tratamento é assim e o que ele impede de afirmar |
| [`docs/ODS_ANALISE.md`](docs/ODS_ANALISE.md) | cruzamento com o IBGE para as ODS 5 e 18: método, resultados e limites |
| [`docs/CHECKLIST_ENTREGA.md`](docs/CHECKLIST_ENTREGA.md) | item do enunciado × arquivo que comprova |

Infraestrutura como código (Terraform) e o guia de credenciais entram neste README quando
as branches correspondentes forem revisadas.
