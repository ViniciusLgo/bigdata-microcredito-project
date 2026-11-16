# Dicionário de dados

Tema 05: acesso a microcrédito e inclusão financeira regional.

Aqui estão os campos de cada etapa do pipeline: a origem (SCR.data e API SGS), o arquivo intermediário, os CSVs tratados e as tabelas do PostgreSQL. Os números de conferência foram apurados em 15/11/2026 nos CSVs do repositório (hashes em `data/manifesto-fontes.csv`). Eles descrevem os arquivos locais, e não uma consulta ao banco da Aiven.

## 1. Convenções

| Item | Valor |
|---|---|
| Separador do CSV de origem (SCR.data) | `;` |
| Separador dos CSVs tratados | `,` |
| Decimal na origem SCR.data | vírgula (`1.234,56`) |
| Decimal na origem SGS (JSON) | ponto (`123.45`) |
| Codificação de leitura dos CSVs do SCR | `utf-8-sig` |
| Data nos CSVs tratados | `AAAA-MM-DD` |

Cuidado com a palavra segmento. No arquivo original do SCR.data, `segmento` é o tipo da instituição financeira (banco, cooperativa, financeira, fintech). No nosso projeto, a coluna `segmento` dos CSVs tratados e do banco vem da coluna `cliente` do SCR e guarda PF ou PJ. O campo `segmento` do BCB não é usado em nenhuma etapa.

## 2. Origem

### 2.1 SCR.data versão 2

Fonte: Banco Central do Brasil, ZIPs anuais em `https://www.bcb.gov.br/pda/desig/scrdata_{ANO}.zip`, com um CSV por mês. Metodologia em `https://www.bcb.gov.br/pda/desig/metodologia_versao2.pdf`. Licença Open Data Commons ODbL. Atualização mensal, com cerca de 30 dias de atraso.

| Campo | Descrição | Usado |
|---|---|---|
| `data_base` | data de referência (fechamento do mês) | sim, vira `data_referencia` |
| `uf` | UF de residência (PF) ou da sede (PJ) | sim, filtro e chave |
| `segmento` | tipo da instituição financeira | não |
| `cliente` | `PF` ou `PJ` | sim, vira o `segmento` do projeto |
| `cnae_ocupacao` | seção do CNAE (PJ) ou natureza da ocupação (PF) | não |
| `porte` | porte do cliente | não |
| `modalidade` | Empréstimos, Financiamentos, Outros créditos | sim |
| `submodalidade` | é aqui que aparece `Microcrédito` | sim, filtro e parte do rótulo |
| `origem` | origem dos recursos | não |
| `indexador` | indexador da operação | não |
| `numero_de_operacoes` | número de operações de crédito | sim, somado |
| faixas `a_vencer_*` e `vencido_*` | créditos a vencer e vencidos por prazo | não |
| `carteira_ativa` | carteira a vencer mais carteira vencida | sim, somado |
| `carteira_inadimplencia` | operações com parcela vencida há mais de 90 dias | sim, só para calcular a taxa |
| `ativo_problematico` | operações classificadas como ativo problemático | não |

Três lacunas da origem, que declaramos em vez de inventar:

1. Unidade monetária. A metodologia não diz a unidade de `carteira_ativa` e `carteira_inadimplencia`. Pela ordem de grandeza, tratamos como reais. É uma inferência.
2. Valores negativos em `numero_de_operacoes`. São 1.085 linhas de 7.081 (15,3%), com mínimo de −32. A metodologia não descreve regra de supressão ou valor especial. Até confirmar com o BCB, o campo não vale como contagem (ver `DECISOES_TECNICAS.md`).
3. Piso de registro. O SCR só recebe operações acima de R$ 200 desde junho/2016. Como o recorte começa em 2021, operações menores que isso não estão na base.

### 2.2 API SGS, séries 20618 e 20712

Fonte: Banco Central, Sistema Gerenciador de Séries Temporais. Endereço: `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados?formato=json&dataInicial=01/01/2021`.

| Série | Nome oficial | Unidade | Periodicidade |
|---|---|---|---|
| 20618 | Saldo da carteira de crédito com recursos direcionados, pessoas físicas, microcrédito destinado a microempreendedores | milhões de reais | mensal |
| 20712 | Concessões de crédito com recursos direcionados, pessoas físicas, microcrédito total | milhões de reais | mensal |

O JSON é uma lista com `data` (texto `DD/MM/AAAA`, sempre dia 01) e `valor` (texto com ponto decimal, em milhões de reais).

### 2.3 IBGE, tabela SIDRA 10261

Fonte: Censo Demográfico 2022, amostra de trabalho e rendimento. Pessoas de 14 anos ou mais ocupadas por posição na ocupação, sexo e cor ou raça, por UF. Usada só na análise das ODS (ver `ODS_ANALISE.md`).

Arquivo `data/ibge_sexo_raca_uf_2022.csv` (270 linhas, feito por `analise/baixar_ibge.py`):

| Campo | Descrição |
|---|---|
| `uf` | sigla da UF |
| `ano` | 2022 |
| `sexo` | Homens ou Mulheres |
| `cor_raca` | Branca, Preta, Amarela, Parda ou Indígena |
| `ocupados` | pessoas ocupadas como empregador ou conta própria |

## 3. Arquivo intermediário

`data/raw/scr_microcredito_brasil_raw.csv`, gerado por `etl/filtrar_scr.py`. Não vai para o Git por causa do tamanho. Mantém todas as colunas do SCR e só filtra as linhas (27 UFs e `submodalidade == "Microcrédito"`). Separador `;`, tudo lido como texto. Tem 598.000 linhas e 67 datas-base, de 31/01/2021 a 31/07/2026.

## 4. CSVs tratados (`data/processed/`)

### 4.1 `fato_credito_regional.csv`, 7.081 linhas

Cada linha é uma UF, um segmento (PF ou PJ), uma modalidade e um mês.

| Campo | Tipo | Origem | Observações |
|---|---|---|---|
| `uf` | texto (2) | `uf` | 27 valores |
| `segmento` | texto (2) | `cliente` | PF (3.618 linhas) e PJ (3.463) |
| `modalidade` | texto | `modalidade` + " - " + `submodalidade` | Empréstimos (3.618) e Financiamentos (3.463) |
| `data_referencia` | data | `data_base` | 67 datas, sempre o último dia do mês |
| `valor_carteira_ativa` | decimal | soma de `carteira_ativa` | reais (inferido); de R$ 488,12 a R$ 2,295 bi; nenhum valor menor ou igual a zero |
| `quantidade_operacoes` | decimal sem parte fracionária | soma de `numero_de_operacoes` | de −32 a 1.140.446; 1.085 linhas negativas |
| `taxa_inadimplencia` | decimal de 0 a 1 | `carteira_inadimplencia / carteira_ativa`, 4 casas | 39 linhas com taxa 1,0 |

Nenhum campo tem valor vazio e a chave (UF, segmento, modalidade, data) não tem duplicata.

Cruzamento modalidade por segmento:

| Modalidade | PF | PJ |
|---|---|---|
| Empréstimos, Microcrédito | 1.809 | 1.809 |
| Financiamentos, Microcrédito | 1.809 | 1.654 |

As 54 combinações de UF e segmento têm as 67 datas. Só Financiamentos para PJ é incompleta, porque há UFs e meses sem operação dessa modalidade. Linha ausente quer dizer que não houve registro na origem, e não que o valor é zero.

O `valor_carteira_ativa` sai no CSV com a precisão do ponto flutuante (por exemplo, `1050230.3699999999`), e no banco é arredondado para 2 casas. Ao comparar CSV com banco, use tolerância.

### 4.2 `fato_microcredito_nacional.csv`, 136 linhas

Cada linha é uma série e um mês.

| Campo | Tipo | Origem | Observações |
|---|---|---|---|
| `serie_id` | inteiro | chave no script | 20618 (68 linhas) e 20712 (68 linhas) |
| `descricao_serie` | texto | rótulo do script | texto nosso, o nome oficial está na seção 2.2 |
| `data_referencia` | data | `data` do JSON | de 01/01/2021 a 01/08/2026, sempre dia 01 |
| `valor` | decimal | `valor` do JSON | milhões de reais; 20618 vai de 6.237 a 11.093 e 20712 de 1.041 a 1.879 |

## 5. Banco de dados (`sql/schema.sql`)

Modelo dimensional simplificado, com duas dimensões, duas fatos e uma tabela de perfil. A fato regional se liga às dimensões. A nacional é independente, sem grão nem chave em comum. A tabela de perfil vem do IBGE e se liga só à `dim_uf`.

### `dim_uf`

| Campo | Tipo | Chave | Descrição |
|---|---|---|---|
| `uf_id` | SERIAL | PK | identificador |
| `sigla_uf` | VARCHAR(2) | único | AC a TO |
| `nome_uf` | VARCHAR(40) | | nome por extenso |
| `regiao` | VARCHAR(20) | | Norte, Nordeste, Centro-Oeste, Sudeste ou Sul |

27 linhas, carregadas de uma lista fixa em `etl/carregar.py`, e não dos dados.

### `dim_modalidade`

| Campo | Tipo | Chave | Descrição |
|---|---|---|---|
| `modalidade_id` | SERIAL | PK | identificador |
| `nome_modalidade` | VARCHAR(150) | único com `segmento` | por exemplo, `Empréstimos - Microcrédito` |
| `segmento` | VARCHAR(2) | único com `nome_modalidade` | PF ou PJ |

4 linhas, tiradas das combinações que aparecem no CSV.

### `fato_credito_regional`

| Campo | Tipo | Chave | Descrição |
|---|---|---|---|
| `id` | SERIAL | PK | |
| `uf_id` | INTEGER | FK para `dim_uf` | |
| `modalidade_id` | INTEGER | FK para `dim_modalidade` | |
| `data_referencia` | DATE | único com as duas chaves | último dia do mês |
| `valor_carteira_ativa` | DECIMAL(15,2) | | reais (inferido) |
| `taxa_inadimplencia` | DECIMAL(6,4) | | fração de 0 a 1: 0,05 é 5% |
| `quantidade_operacoes` | INTEGER | | o CSV traz decimal e o banco arredonda |

Índices em `data_referencia` e `uf_id`.

### `fato_microcredito_nacional`

| Campo | Tipo | Chave | Descrição |
|---|---|---|---|
| `id` | SERIAL | PK | |
| `serie_id` | INTEGER | único com a data | 20618 ou 20712 |
| `descricao_serie` | VARCHAR(200) | | rótulo do projeto |
| `data_referencia` | DATE | único com `serie_id` | primeiro dia do mês |
| `valor` | DECIMAL(15,2) | | milhões de reais, não aceita vazio |

Índice em `data_referencia`. O `valor` não aceita vazio, mas a função `numero_sgs()` devolve `None` para valor vazio. Hoje as duas séries não têm vazios. Se a API devolver um mês sem valor, a carga falha naquela linha.

### `perfil_ocupados_uf`

| Campo | Tipo | Chave | Descrição |
|---|---|---|---|
| `id` | SERIAL | PK | |
| `uf_id` | INTEGER | FK para `dim_uf` | |
| `ano` | INTEGER | único com UF, sexo e raça | 2022 (ano do Censo) |
| `sexo` | VARCHAR(10) | | Homens ou Mulheres |
| `cor_raca` | VARCHAR(10) | | Branca, Preta, Amarela, Parda ou Indígena |
| `ocupados` | INTEGER | | pessoas de 14 anos ou mais ocupadas como empregador ou conta própria |

270 linhas (27 UFs, 2 sexos e 5 cores ou raças). Vem do `data/ibge_sexo_raca_uf_2022.csv`. Os valores cruzados vêm arredondados pelo IBGE, então a soma pode diferir em até 0,1% dos totais por sexo ou por raça.

### Totais esperados

| Tabela | Linhas |
|---|---|
| `dim_uf` | 27 |
| `dim_modalidade` | 4 |
| `fato_credito_regional` | 7.081 |
| `fato_microcredito_nacional` | 136 |
| `perfil_ocupados_uf` | 270 |
| Total | 7.518 |

## 6. O que a base não tem

Para não extrapolar na análise nem no dashboard:

- Não tem pessoas. O menor nível é uma soma por UF, tipo de cliente, modalidade e mês.
- Não tem quantidade de clientes, só de operações. Uma pessoa pode ter várias.
- Não tem sexo, gênero, cor ou raça (ver a seção de ODS em `DECISOES_TECNICAS.md`).
- Não tem concessão por UF. `carteira_ativa` é saldo no fim do mês. A única série de concessão é nacional (SGS 20712).
- Não tem identificação da instituição financeira.
- Não tem renda, idade, escolaridade ou porte do tomador. `porte` e `cnae_ocupacao` existem na origem, mas são somados fora na agregação.

## 7. Como conferir

```bash
python - <<'PY'
import pandas as pd
r = pd.read_csv("data/processed/fato_credito_regional.csv")
print(r.shape, r.uf.nunique(), r.segmento.value_counts().to_dict())
print(r.data_referencia.min(), r.data_referencia.max(), r.data_referencia.nunique())
print("negativos:", (r.quantidade_operacoes < 0).sum())
print("duplicatas:", r.duplicated(["uf","segmento","modalidade","data_referencia"]).sum())
n = pd.read_csv("data/processed/fato_microcredito_nacional.csv")
print(n.shape, n.groupby("serie_id").valor.agg(["size","min","max"]).to_dict())
PY

sha256sum data/processed/*.csv data/raw/*.json
```
