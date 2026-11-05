# Dicionário de dados

Tema 05 — Acesso a Microcrédito e Inclusão Financeira Regional.

Este documento descreve os campos de cada camada do pipeline: a origem (SCR.data e API SGS),
o arquivo intermediário, os CSVs tratados e as tabelas do PostgreSQL.

Os números de conferência citados aqui foram apurados em **05/11/2026** sobre os CSVs
versionados no repositório (hashes no `data/manifesto-fontes.csv`). Eles descrevem os
arquivos locais, **não** uma consulta ao banco da Aiven.

---

## 1. Convenções

| Convenção | Valor adotado |
|---|---|
| Separador do CSV de origem (SCR.data) | `;` |
| Separador dos CSVs tratados | `,` |
| Separador decimal na origem SCR.data | vírgula (`1.234,56`) |
| Separador decimal na origem SGS (JSON) | ponto (`123.45`) |
| Codificação de leitura dos CSVs do SCR | `utf-8-sig` |
| Formato de data nos CSVs tratados | `AAAA-MM-DD` (ISO) |
| Fuso / referência temporal | data-base de fechamento mensal |

> **Atenção à palavra "segmento".** No arquivo original do SCR.data, `segmento` é o
> **segmento da instituição financeira** (Banco, Cooperativa, Financeira, Fintech etc.).
> Neste projeto, a coluna chamada `segmento` nos CSVs tratados e no banco é outra coisa:
> ela vem da coluna **`cliente`** do SCR.data e guarda **PF ou PJ**. O campo `segmento`
> original do BCB **não é usado** em nenhuma etapa. Quem for comparar o nosso resultado com
> o arquivo do BCB precisa saber disso.

---

## 2. Camada de origem

### 2.1 SCR.data versão 2 — CSVs mensais dentro dos ZIPs anuais

Fonte: Banco Central do Brasil, conjunto *SCR.data*, versão 2.
URL dos arquivos: `https://www.bcb.gov.br/pda/desig/scrdata_{ANO}.zip`
Metodologia: `https://www.bcb.gov.br/pda/desig/metodologia_versao2.pdf`
Licença: Open Data Commons ODbL. Periodicidade mensal, divulgação cerca de 30 dias após o
fechamento do período.

Campos do arquivo, conforme a metodologia versão 2:

| Campo | Tipo lido | Descrição | Usado no projeto |
|---|---|---|---|
| `data_base` | texto `AAAA-MM-DD` | Data de referência (fechamento do mês) | Sim — vira `data_referencia` |
| `uf` | texto (2) | UF de residência (PF) ou da sede (PJ) | Sim — filtro e chave |
| `segmento` | texto | Segmento da **instituição financeira** | Não |
| `cliente` | texto | Tipo de cliente: `PF` ou `PJ` | Sim — vira a coluna `segmento` do projeto |
| `cnae_ocupacao` | texto | Seção do CNAE (PJ) ou natureza da ocupação (PF) | Não |
| `porte` | texto | Porte do cliente (faixas de salário mínimo para PF; Micro/Pequeno/Médio/Grande para PJ; Indisponível) | Não |
| `modalidade` | texto | Modalidade da operação (Empréstimos, Financiamentos, Outros créditos…) | Sim |
| `submodalidade` | texto | Submodalidade da operação — é aqui que aparece `Microcrédito` | Sim — filtro e parte do rótulo |
| `origem` | texto | Origem dos recursos (com ou sem destinação específica) | Não |
| `indexador` | texto | Indexador da operação | Não |
| `numero_de_operacoes` | numérico | Número de operações de crédito no recorte | Sim — somado |
| `a_vencer_ate_90_dias` … `a_vencer_acima_de_5400_dias` | numérico | Faixas de créditos a vencer | Não |
| `carteira_a_vencer` | numérico | Soma das faixas a vencer | Não |
| `vencido_de_15_ate_90_dias`, `vencido_acima_de_90_dias` | numérico | Faixas de créditos vencidos | Não |
| `carteira_vencida` | numérico | Soma das faixas vencidas | Não |
| `carteira_ativa` | numérico | `carteira_a_vencer` + `carteira_vencida` | Sim — somado |
| `carteira_inadimplencia` | numérico | Operações a vencer e vencidas com alguma parcela vencida há mais de 90 dias | Sim — usado só para calcular a taxa |
| `ativo_problematico` | numérico | Operações classificadas como ativo problemático | Não |

**Pendências de metadado da origem (declarar na entrega, não inventar):**

1. **Unidade monetária.** A metodologia versão 2 **não declara** a unidade de
   `carteira_ativa` e `carteira_inadimplencia`. Pela ordem de grandeza dos valores
   observados, o projeto trata os campos como **reais**. Isso é uma inferência, não um
   metadado oficial.
2. **Valores negativos em `numero_de_operacoes`.** Nos dados tratados há **1.084 linhas
   (15,3% de 7.080) com quantidade de operações negativa**, mínimo **−32**. A metodologia
   versão 2 não descreve regra de supressão, mascaramento ou valor sentinela para esse
   campo. Enquanto o critério não for confirmado junto ao BCB, a leitura do projeto é:
   *valor não interpretável como contagem*. Ver `docs/DECISOES_TECNICAS.md`, decisão D-07.
3. **Escopo de registro.** O SCR só recebe operações acima de R$ 1.000 até maio/2016 e
   acima de R$ 200 a partir de junho/2016. Como o recorte começa em 2021, vale o piso de
   R$ 200 — operações menores que isso não estão na base.

### 2.2 API SGS — séries 20618 e 20712

Fonte: Banco Central do Brasil, Sistema Gerenciador de Séries Temporais (SGS).
Endpoint: `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados?formato=json&dataInicial=01/01/2021`

| Série | Nome oficial | Unidade | Periodicidade | Início da série |
|---|---|---|---|---|
| 20618 | Saldo da carteira de crédito com recursos direcionados — Pessoas físicas — Microcrédito destinado a microempreendedores | Milhões de reais | Mensal | 03/2011 |
| 20712 | Concessões de crédito com recursos direcionados — Pessoas físicas — Microcrédito total | Milhões de reais | Mensal | 03/2011 |

Formato do JSON: lista de objetos com `data` (`DD/MM/AAAA`) e `valor` (texto, ponto decimal).

| Campo do JSON | Tipo | Descrição |
|---|---|---|
| `data` | texto `DD/MM/AAAA` | Mês de referência, sempre no **dia 01** |
| `valor` | texto | Valor da série em milhões de reais |

---

## 3. Camada intermediária

### 3.1 `data/raw/scr_microcredito_brasil_raw.csv`

Gerado por `etl/filtrar_scr.py`. Não vai para o Git (tamanho). Mantém **todas** as colunas
originais do SCR.data; só as linhas são filtradas (27 UFs e `submodalidade == "Microcrédito"`).
Separador `;`, todas as colunas lidas como texto.

Conferência da fase 2: 598.002 linhas, 67 datas-base, de 31/01/2021 a 31/07/2026.

---

## 4. CSVs tratados (`data/processed/`)

### 4.1 `fato_credito_regional.csv` — 7.080 linhas + cabeçalho

Grão: **uma linha por UF × segmento (PF/PJ) × modalidade × mês**.

| Campo | Tipo | Unidade | Origem | Nulos | Observações |
|---|---|---|---|---|---|
| `uf` | texto (2) | — | `uf` do SCR.data | 0 | 27 valores distintos |
| `segmento` | texto (2) | — | **`cliente`** do SCR.data | 0 | `PF` (3.618 linhas) e `PJ` (3.462) |
| `modalidade` | texto | — | `modalidade` + `" - "` + `submodalidade` | 0 | `Empréstimos - Microcrédito` (3.618) e `Financiamentos - Microcrédito` (3.462) |
| `data_referencia` | data ISO | — | `data_base` | 0 | 67 datas, 31/01/2021 a 31/07/2026, sempre **último dia do mês** |
| `valor_carteira_ativa` | decimal | reais (inferido) | soma de `carteira_ativa` | 0 | mínimo R$ 505,88; máximo R$ 2,295 bi; nenhum valor ≤ 0 |
| `quantidade_operacoes` | decimal com parte fracionária zero | operações | soma de `numero_de_operacoes` | 0 | mínimo **−32**; máximo 1.140.446; 1.084 linhas negativas |
| `taxa_inadimplencia` | decimal 0–1 | fração | `carteira_inadimplencia / carteira_ativa`, arredondada em 4 casas | 0 | todos entre 0 e 1; 39 linhas com taxa igual a 1,0 (carteira 100% inadimplida) |

Cruzamento modalidade × segmento observado:

| modalidade | PF | PJ |
|---|---|---|
| Empréstimos - Microcrédito | 1.809 | 1.809 |
| Financiamentos - Microcrédito | 1.809 | 1.653 |

Cobertura: as 54 combinações UF × segmento têm as 67 datas-base. A combinação
`Financiamentos - Microcrédito` × PJ é a única incompleta (1.653 em vez de 1.809), ou seja,
há UFs/meses sem operações dessa modalidade para PJ. **Ausência de linha significa ausência
de registro na origem, não zero.**

Chave de negócio (`uf`, `segmento`, `modalidade`, `data_referencia`): **sem duplicatas**.

> O campo `valor_carteira_ativa` é gravado no CSV com a precisão do ponto flutuante
> (ex.: `1050230.3699999999`). No banco a coluna é `DECIMAL(15,2)`, então o valor é
> arredondado na carga. Comparações CSV × banco devem usar tolerância, não igualdade exata.

### 4.2 `fato_microcredito_nacional.csv` — 136 linhas + cabeçalho

Grão: **uma linha por série × mês**.

| Campo | Tipo | Unidade | Origem | Nulos | Observações |
|---|---|---|---|---|---|
| `serie_id` | inteiro | — | chave do dicionário no script | 0 | `20618` (68 linhas) e `20712` (68 linhas) |
| `descricao_serie` | texto | — | rótulo escrito no próprio script | 0 | texto do projeto, **não** é o nome oficial da série — o nome oficial está na seção 2.2 |
| `data_referencia` | data ISO | — | `data` do JSON | 0 | 01/01/2021 a 01/08/2026, sempre **dia 01** |
| `valor` | decimal | **milhões de reais** | `valor` do JSON | 0 | 20618: 6.237 a 11.093; 20712: 1.041 a 1.879 |

---

## 5. Banco de dados (PostgreSQL / Aiven) — `sql/schema.sql`

Modelo dimensional simplificado: duas dimensões e duas fatos. A fato regional se liga às
dimensões; a fato nacional é **independente** (não compartilha grão nem chave com a regional).

### 5.1 `dim_uf`

| Campo | Tipo | Chave | Nulo | Origem | Descrição |
|---|---|---|---|---|---|
| `uf_id` | SERIAL | PK | não | gerado | Identificador da UF |
| `sigla_uf` | VARCHAR(2) | UNIQUE | não | lista fixa em `etl/carregar.py` | Sigla (AC…TO) |
| `nome_uf` | VARCHAR(40) | — | não | lista fixa em `etl/carregar.py` | Nome por extenso |
| `regiao` | VARCHAR(20) | — | não | lista fixa em `etl/carregar.py` | Norte, Nordeste, Centro-Oeste, Sudeste, Sul |

27 linhas. A dimensão é carregada da lista do script, não dos dados, então ela existe
mesmo para UFs sem fato no período.

### 5.2 `dim_modalidade`

| Campo | Tipo | Chave | Nulo | Origem | Descrição |
|---|---|---|---|---|---|
| `modalidade_id` | SERIAL | PK | não | gerado | Identificador |
| `nome_modalidade` | VARCHAR(150) | UNIQUE (com `segmento`) | não | `modalidade` do CSV tratado | Ex.: `Empréstimos - Microcrédito` |
| `segmento` | VARCHAR(2) | UNIQUE (com `nome_modalidade`) | não | `segmento` do CSV tratado | `PF` ou `PJ` (coluna `cliente` do SCR.data) |

Carregada a partir das combinações distintas presentes no CSV: **4 linhas** na versão atual.

### 5.3 `fato_credito_regional`

| Campo | Tipo | Chave | Nulo | Origem | Descrição |
|---|---|---|---|---|---|
| `id` | SERIAL | PK | não | gerado | — |
| `uf_id` | INTEGER | FK → `dim_uf.uf_id` | não | `uf` resolvida na dimensão | — |
| `modalidade_id` | INTEGER | FK → `dim_modalidade.modalidade_id` | não | (`modalidade`, `segmento`) resolvidos na dimensão | — |
| `data_referencia` | DATE | UNIQUE (com as duas FKs) | não | CSV tratado | Último dia do mês |
| `valor_carteira_ativa` | DECIMAL(15,2) | — | sim | CSV tratado | Reais (inferido) |
| `taxa_inadimplencia` | DECIMAL(6,4) | — | sim | CSV tratado | Fração de 0 a 1 — **0,05 significa 5%**, não 0,05% |
| `quantidade_operacoes` | INTEGER | — | sim | CSV tratado | O CSV traz decimal; o PostgreSQL arredonda na carga |

Índices: `data_referencia`, `uf_id`. Restrição de unicidade:
(`uf_id`, `modalidade_id`, `data_referencia`).

### 5.4 `fato_microcredito_nacional`

| Campo | Tipo | Chave | Nulo | Origem | Descrição |
|---|---|---|---|---|---|
| `id` | SERIAL | PK | não | gerado | — |
| `serie_id` | INTEGER | UNIQUE (com a data) | não | CSV tratado | 20618 ou 20712 |
| `descricao_serie` | VARCHAR(200) | — | não | CSV tratado | Rótulo do projeto |
| `data_referencia` | DATE | UNIQUE (com `serie_id`) | não | CSV tratado | Primeiro dia do mês |
| `valor` | DECIMAL(15,2) | — | **não** | CSV tratado | **Milhões de reais** |

Índice: `data_referencia`.

> `valor` é `NOT NULL`, mas a função `numero_br()` devolve `None` para valor vazio. Hoje
> não há vazios nas duas séries; se a API passar a devolver um mês sem valor, a carga vai
> falhar nessa linha. Está registrado como risco.

### 5.5 Totais esperados

| Tabela | Linhas esperadas |
|---|---|
| `dim_uf` | 27 |
| `dim_modalidade` | 4 |
| `fato_credito_regional` | 7.080 |
| `fato_microcredito_nacional` | 136 |
| **Total** | **7.247** |

---

## 6. O que a base **não** tem

Importante para não extrapolar nas análises e no dashboard:

- **Não tem pessoas.** O grão mínimo é um agregado de UF × tipo de cliente × modalidade × mês.
- **Não tem quantidade de clientes**, só **quantidade de operações**. Uma pessoa pode ter
  várias operações; somar operações não é contar tomadores.
- **Não tem sexo/gênero nem cor/raça.** Ver `docs/DECISOES_TECNICAS.md`, seção ODS.
- **Não tem concessão por UF.** `carteira_ativa` é **saldo** (estoque no fim do mês), não
  valor concedido no mês. A única série de concessão é nacional (SGS 20712).
- **Não tem identificação de instituição financeira.**
- **Não tem renda, idade, escolaridade ou porte do tomador** no recorte agregado do projeto
  (os campos `porte` e `cnae_ocupacao` existem na origem, mas são somados fora na agregação).

---

## 7. Como conferir estes números

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
