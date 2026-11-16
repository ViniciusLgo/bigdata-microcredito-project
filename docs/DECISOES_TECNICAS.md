# Decisões técnicas

Tema 05 — Acesso a Microcrédito e Inclusão Financeira Regional.

Registro das escolhas de tratamento e modelagem, com a justificativa de cada uma e o que
elas impedem de afirmar. Serve de referência para o dashboard e para a defesa do trabalho.

Última revisão: **05/11/2026**. Os números citados foram conferidos sobre os CSVs
versionados (`data/manifesto-fontes.csv` traz os hashes).

---

## 1. Recorte dos dados

### D-01 — Recorte temporal a partir de janeiro/2021

O projeto usa janeiro/2021 como início para as duas fontes.

- **SGS:** o recorte é imposto no código, no parâmetro `dataInicial=01/01/2021` de
  `etl/extrair_sgs.py`.
- **SCR.data:** o recorte **não** é imposto por código. `etl/filtrar_scr.py` processa
  todos os ZIPs que estiverem em `data/zip/`. O início em 2021 vem de quais arquivos foram
  baixados, não de um filtro. Quem colocar um ZIP de 2019 na pasta vai ampliar a base sem
  perceber.

Motivo do corte: o SCR.data cobre desde junho/2012, mas cinco anos e meio de dados já
atendem à análise regional e o plano gratuito do PostgreSQL na Aiven tem 1 GB.

### D-02 — Brasil inteiro (27 UFs), e não só o Nordeste

A primeira versão filtrava só o Nordeste. Foi ampliada para as 27 UFs porque o volume
agregado cabe com folga no limite de 1 GB e porque comparar o Nordeste com as demais
regiões é justamente o ponto da pergunta de inclusão financeira **regional**.

Consequência: existe um CSV intermediário antigo só do Nordeste. O pipeline atual **não o
usa**; a versão válida é a do Brasil.

### D-03 — Filtro por submodalidade, não por modalidade

No arquivo real do SCR.data não existe `modalidade = "Microcrédito"`. O microcrédito
aparece na coluna **`submodalidade`**, dentro das modalidades `Empréstimos` e
`Financiamentos`. Por isso o filtro é `submodalidade == "Microcrédito"` e o rótulo
guardado é a concatenação `modalidade + " - " + submodalidade`.

É uma decisão de escopo: o projeto analisa **a submodalidade Microcrédito do SCR**, que não
é a mesma coisa que o universo de políticas de microcrédito (PNMPO, por exemplo).

---

## 2. Processamento

### D-04 — Leitura em chunks de 200.000 linhas

Cada CSV mensal do SCR tem entre 85 e 90 MB e são 67 arquivos. `etl/filtrar_scr.py` usa
`pd.read_csv(..., chunksize=200_000, dtype=str)` e grava em modo *append*, filtrando
pedaço a pedaço. Assim o arquivo inteiro nunca fica na memória.

**Limitação honesta:** só a **filtragem** é feita em chunks. O `etl/tratar.py` abre o CSV
intermediário inteiro com `pd.read_csv`. O pipeline, portanto, **não** é processamento
distribuído nem streaming de ponta a ponta — é processamento em lote com leitura
particionada na etapa mais pesada. Isso deve ser descrito assim na apresentação.

### D-05 — Separar PF e PJ antes de agregar

A coluna `cliente` do SCR.data diz se a linha é pessoa física ou jurídica. Ela entra na
chave do `groupby`. Sem isso, PF e PJ seriam somados e o número perderia sentido: são
públicos e políticas diferentes.

**Armadilha de nome:** a coluna resultante foi batizada de `segmento` no projeto, mas no
SCR.data `segmento` é o **segmento da instituição financeira** (Banco, Cooperativa,
Fintech…). O campo original do BCB não é usado em lugar nenhum. Quem comparar nosso
resultado com o arquivo do BCB precisa saber disso. Está anotado também no
`docs/DICIONARIO_DADOS.md`.

### D-06 — Agregação por UF × cliente × modalidade × mês

`etl/tratar.py` agrupa por `uf`, `segmento` (PF/PJ), `modalidade` e `data_referencia`, e
soma `carteira_ativa`, `carteira_inadimplencia` e `numero_de_operacoes`.

Dimensões presentes na origem que são **somadas fora** nessa agregação: segmento da
instituição financeira, `cnae_ocupacao`, `porte`, `origem` dos recursos e `indexador`.
Elas foram descartadas para não multiplicar as combinações e estourar o plano gratuito.

Consequências que precisam estar claras:

- Duas linhas idênticas nas colunas finais **não são** duplicatas: podem ser recortes
  legítimos diferentes na origem (CNAEs diferentes, portes diferentes, indexadores
  diferentes). Por isso **não se remove duplicata por semelhança de colunas finais**;
  a detecção de carga repetida tem de ser por arquivo/manifesto.
- Não dá para responder nada sobre porte, setor de atividade ou tipo de instituição.

### D-07 — Quantidade de operações negativa fica como está, e documentada

Nos dados tratados há **1.084 linhas de 7.080 (15,3%) com `quantidade_operacoes`
negativa**, mínimo **−32**.

A metodologia versão 2 do SCR.data **não documenta** regra de supressão, mascaramento ou
valor sentinela para `numero_de_operacoes`; o campo é definido apenas como "o número de
operações de crédito para um dado recorte de dados".

Decisão: **não transformar em zero, não descartar a linha e não inventar interpretação.**
O valor é mantido como veio, marcado no dicionário como *não interpretável como contagem*,
e qualquer indicador que use contagem de operações deve excluir essas linhas
explicitamente, informando quantas foram excluídas.

Encaminhamento em aberto: confirmar o critério com o BCB (Fala.BR / Lei de Acesso à
Informação) ou manter como lacuna declarada na entrega. **Até lá, o trabalho não usa
quantidade de operações como indicador principal.** O indicador principal é
`valor_carteira_ativa`.

### D-08 — Conversão numérica: SCR e SGS são diferentes

| Fonte | Formato do número | Conversão correta |
|---|---|---|
| SCR.data (CSV) | `1.234,56` — ponto como separador de milhar, vírgula decimal | remover `.`, trocar `,` por `.` |
| SGS (JSON) | `123.45` — ponto decimal | converter direto |

Hoje `etl/tratar.py` usa a mesma função `numero_br()` para as duas fontes. Para o SCR ela
está certa. Para o SGS ela é **perigosa**: se um valor vier como `"123.45"`, a função
remove o ponto e o resultado vira `12345`. Nos JSONs atuais os valores são inteiros sem
ponto, então não houve divergência — mas é coincidência, não garantia.

Decisão: separar as duas conversões. A correção é do Guilherme
(`tests/test_tratamento.py`, commit `fix: separa conversao dos numeros do scr e sgs`).
Esta é uma **pendência conhecida**, não um problema já resolvido.

### D-09 — Taxa de inadimplência é calculada pelo projeto

O arquivo do BCB não traz a taxa pronta. O projeto calcula:

```
taxa_inadimplencia = carteira_inadimplencia / carteira_ativa
```

arredondada em 4 casas, e **descarta** a coluna `valor_inadimplencia` depois. Quando
`carteira_ativa` é zero, a taxa fica nula em vez de gerar divisão por zero.

Regras de uso:

- A taxa é uma **fração**: `0,05` significa **5%**.
- Para agregar UFs ou meses, **não se tira média simples das taxas**. É preciso somar
  numerador e denominador e dividir de novo (média ponderada pela carteira). Como o
  `valor_inadimplencia` foi descartado do CSV final, a reconstituição é
  `taxa × carteira_ativa` linha a linha antes de somar.
- Todos os valores observados ficam entre 0 e 1. Há **39 linhas com taxa igual a 1,0**
  (carteira inteiramente inadimplida) — são válidas, mas distorcem média simples.

---

## 3. Modelagem

### D-10 — Modelo dimensional simplificado, com duas fatos independentes

`sql/schema.sql` monta duas dimensões (`dim_uf`, `dim_modalidade`) e duas fatos.

- `fato_credito_regional` se liga às duas dimensões por chave estrangeira.
- `fato_microcredito_nacional` **não se liga a nada**. Ela não tem UF nem modalidade: é a
  série nacional do SGS, com outro grão e outra fonte.

Isso é deliberado. **Não se inventou chave estrangeira nem granularidade compartilhada**
entre as duas fatos só para "fechar" o desenho de estrela. Descrever o modelo como
"esquema estrela clássico" seria impreciso; o termo adotado é **modelo dimensional
simplificado com duas tabelas fato independentes**.

Por que não normalizar mais: os dados já chegam agregados, as consultas do dashboard são
filtros por ano, UF e modalidade, e o plano gratuito favorece menos junções.

### D-11 — Alinhamento temporal entre as duas fontes

| Fonte | Convenção de data | Período coberto |
|---|---|---|
| SCR.data (regional) | **último dia** do mês (31/01, 28/02…) | 31/01/2021 a 31/07/2026 |
| SGS (nacional) | **dia 01** do mês | 01/01/2021 a 01/08/2026 |

As duas tabelas foram mantidas com a data de origem, sem normalizar.

Para comparar as séries é obrigatório **alinhar competência** (truncar os dois lados no
mês, por exemplo `date_trunc('month', data_referencia)`) e **restringir ao período comum**
(janeiro/2021 a julho/2026). Sem isso, agosto/2026 aparece só no nacional e dá a impressão
falsa de queda no regional.

### D-12 — Semântica: o que cada número é e o que ele não é

Estas confusões são as mais fáceis de cometer na análise e na apresentação:

| O número | O que é | O que **não** é |
|---|---|---|
| `quantidade_operacoes` | contagem de operações de crédito | contagem de clientes ou tomadores — uma pessoa pode ter várias operações |
| `valor_carteira_ativa` | **saldo** em aberto no fim do mês (a vencer + vencido) | valor concedido no mês |
| soma de `valor_carteira_ativa` ao longo de 12 meses | nada de útil — é soma de estoques | total concedido no ano |
| `taxa_inadimplencia` | fração entre 0 e 1 | percentual já multiplicado por 100 |
| série 20712 (nacional) | concessões mensais, **em milhões de reais** | valor em reais, nem comparável direto com a carteira regional |
| série 20618 (nacional) | saldo PF de microcrédito a microempreendedores, **em milhões de reais** | mesmo universo do recorte regional do SCR |

Antes de qualquer comparação entre SGS e SCR, conferir unidade e abrangência nos metadados
do BCB: a série nacional é só PF e só crédito direcionado, enquanto o recorte regional
inclui PF e PJ.

---

## 4. Carga e reprodutibilidade

### D-13 — A carga atual é destrutiva (pendência aberta)

`etl/carregar.py` executa `sql/schema.sql` em toda execução, e o schema começa com
`DROP TABLE ... CASCADE`. Ou seja: **rodar o carregador apaga e recria tudo**.

Enquanto isso não for corrigido:

- **ninguém roda `etl/carregar.py` contra o banco compartilhado do grupo**;
- testes de carga são feitos em banco descartável.

A correção (separar criação de tabelas da carga, deixar a limpeza total explícita e
opcional) é do Vinicius, branch `fix/carga-banco`.

O `ON CONFLICT ... DO NOTHING` também não é retomada de carga: ele pula o que já existe,
mas mantém o valor antigo se o dado tiver sido revisado na origem. O SCR.data **é
retificado** quando a instituição reenvia documentos, então "pular o que já existe" pode
congelar um número desatualizado.

### D-14 — Reprodutibilidade: o que ainda não é garantido

1. `etl/extrair_sgs.py` não fixa `dataFinal`. Cada execução traz os meses novos, então o
   JSON muda sozinho com o tempo. Para reproduzir exatamente a versão analisada é preciso
   usar os JSONs versionados no repositório (hashes no manifesto).
2. Os ZIPs do SCR.data não estão no Git (quase 1 GB). O
   **`data/manifesto-fontes.csv`** registra as URLs oficiais e o padrão
   `https://www.bcb.gov.br/pda/desig/scrdata_{ANO}.zip`; os hashes dos ZIPs ficaram como
   "não disponível" porque os arquivos não estão neste clone. Quem tiver os ZIPs originais
   deve rodar `sha256sum data/zip/*.zip` e preencher o manifesto.
3. O ZIP do ano corrente é atualizado mensalmente pelo BCB. Baixar de novo em 2027 traz
   mais meses e muda as contagens. Por isso o manifesto registra o período efetivamente
   usado: **2021-01 a 2026-07**.

### D-15 — Camada não relacional

O guia do trabalho cita OpenSearch como **opcional**. O projeto **não** implementou camada
não relacional: a base está só no PostgreSQL da Aiven.

Decisão do grupo: manter assim e **declarar explicitamente** na entrega — "camada não
relacional não implementada, por ser opcional no guia" — em vez de omitir o item. Omitir
pareceria esquecimento; declarar é uma escolha de escopo.

---

## 5. ODS — recorte de análise e limites

### D-16 — A base não sustenta afirmação sobre gênero nem sobre raça/cor

**Fato:** nenhuma coluna do recorte atual contém sexo, gênero, cor ou raça. O SCR.data
versão 2 não publica esses atributos. Diferença entre UFs, por si só, **não comprova**
desigualdade de acesso por gênero ou por raça.

Por isso, qualquer frase do tipo "mulheres acessam menos microcrédito no Nordeste" **não
pode ser sustentada pelos nossos dados**. Seria extrapolação.

#### O que dá para fazer, sem inventar atributo

A saída é uma **análise territorial de associação**: cruzar o indicador de microcrédito por
UF (que temos) com um indicador sociodemográfico **público e oficial** por UF (que o IBGE
tem), e falar de **território**, nunca do perfil de quem tomou o crédito.

**Fonte pública escolhida: IBGE.**

| Uso | Pesquisa | Tabela SIDRA | Conteúdo | Nível |
|---|---|---|---|---|
| ODS 5 e ODS 18 | Censo Demográfico 2022 (Amostra — Trabalho e Rendimento) | **10261** | Pessoas de 14 anos ou mais ocupadas por **posição na ocupação** (inclui conta própria e empregador), **sexo** e **cor ou raça** | Brasil, Grande Região, **UF**, Município |
| Alternativa com série temporal (só sexo) | PNAD Contínua anual | **7233** | Pessoas ocupadas como **empregador ou conta própria** por **sexo** e registro do empreendimento no CNPJ — 2012 a 2019 e 2022 a 2025 | Brasil, Grande Região, **UF** |
| Complemento | PNAD Contínua trimestral | **6403** | População por **cor ou raça** | Brasil, Grande Região, **UF** |

Sobre o ODS 18: é o objetivo de **Igualdade Étnico-Racial**, proposto voluntariamente pelo
Brasil em setembro de 2023 na 78ª Assembleia Geral da ONU, formalizado pela Comissão
Nacional para os ODS (Decreto 11.704/2023, Resolução nº 2/CNODS de 20/12/2023) e lançado
publicamente em novembro de 2024, sob coordenação do Ministério da Igualdade Racial. Não é
um dos 17 ODS globais da Agenda 2030 — é um acréscimo brasileiro, e isso precisa estar
escrito na entrega.

#### Análise executada

Esta decisão **saiu do papel**: o cruzamento foi feito em 05/11/2026.

- Script: `analise/ods_cruzamento.py`
- Base do IBGE: `data/ibge_ocupacao_uf_2022.csv` (tabela SIDRA 10261)
- Resultado por UF: `docs/evidencias/ods_cruzamento_uf.csv`
- Gráfico: `docs/evidencias/ods_cruzamento.png`
- **Leitura completa: [`ODS_ANALISE.md`](ODS_ANALISE.md)**

Em resumo: há associação territorial positiva entre a participação de pessoas pretas e
pardas e a carteira de microcrédito por ocupado (Spearman ρ = 0,455, p = 0,017), mas ela
perde significância ao excluir o Nordeste (ρ = 0,358, p = 0,145) — e o Nordeste sozinho
concentra 62,1% da carteira nacional. O que a correlação capta é onde a oferta está
concentrada, não acesso por grupo racial. Para gênero não há associação detectável
(ρ = −0,227, p = 0,255). A relação mais forte da análise não é sobre nenhum dos dois ODS:
é entre densidade de microcrédito e inadimplência (ρ = −0,871, p < 0,0001).

#### Pergunta de pesquisa

> **UFs com maior participação de mulheres e de pessoas pretas e pardas entre os
> trabalhadores por conta própria e empregadores apresentam maior ou menor volume de
> carteira ativa de microcrédito per capita ocupada, e maior ou menor taxa de
> inadimplência, no período de 2021 a 2026?**

Desenho:

- **Unidade de análise:** a UF. São 27 observações — poucas, então a leitura é descritiva e
  exploratória, não inferência causal.
- **Variáveis do nosso banco:** `valor_carteira_ativa` e `taxa_inadimplencia` agregadas por
  UF (taxa ponderada pela carteira, conforme D-09).
- **Variáveis do IBGE:** participação de mulheres e participação de pessoas pretas e pardas
  entre conta própria + empregadores, por UF.
- **Normalização:** usar a carteira por pessoa ocupada por conta própria/empregadora da UF,
  para não medir só o tamanho da economia estadual.
- **Produto:** mapa/dispersão por UF e um texto curto, sempre com a ressalva abaixo.

#### Ressalva obrigatória, a repetir no relatório e no dashboard

> Os dados de microcrédito do SCR.data são agregados por UF e não contêm sexo, gênero, cor
> ou raça. O cruzamento com os indicadores do IBGE descreve **o território**, não o perfil
> de quem tomou o crédito. Concluir algo sobre indivíduos a partir de médias territoriais é
> **falácia ecológica**. Nenhum atributo demográfico foi imputado a nenhuma operação.

#### O que **não** vamos fazer

- Estimar sexo ou raça do tomador a partir de UF, CNAE ou qualquer proxy.
- Juntar as bases linha a linha. O IBGE entra como **tabela separada no nível de UF**.
- Afirmar causalidade ("o microcrédito reduziu a desigualdade de gênero em X").

#### Decisão do grupo, sem consulta prévia à professora

O grupo seguiu com a análise territorial de associação por ser a única leitura que os dados
sustentam: a alternativa seria atribuir sexo ou raça a operações que não os têm. O recorte,
o método e os limites estão escritos em `docs/ODS_ANALISE.md` para que a escolha possa ser
avaliada. Se a professora exigir fonte com o atributo no nível do indivíduo, a base atual
não atende e isso precisaria de outra fonte — não de outro tratamento desta.

O ODS 18 é usado nomeando-se expressamente sua condição: acréscimo voluntário brasileiro,
fora dos 17 ODS globais da Agenda 2030.

Fica em aberto apenas o prazo da fase 3: a cópia do enunciado da fase 2 mostra 17/out/2027
e a da fase 3 mostra 31/out sem ano. Conferir no Classroom.

---

## 6. Resumo das pendências abertas

| # | Pendência | Responsável | Status |
|---|---|---|---|
| 1 | Separar conversão numérica SCR (vírgula) e SGS (ponto) | Guilherme | aberta |
| 2 | Carga destrutiva: separar criação de tabelas e carga | Vinicius | aberta |
| 3 | Critério dos valores negativos em `numero_de_operacoes` | grupo / BCB | aberta — declarada como lacuna |
| 4 | Hashes SHA-256 dos ZIPs do SCR.data | quem tiver os arquivos | aberta |
| 5 | Unidade monetária oficial de `carteira_ativa` | grupo / BCB | inferida como reais |
| 6 | Camada não relacional (OpenSearch) | grupo | **fechada** — não implementada, declarada como opcional |
| 7 | Recorte das ODS 5 e 18 | grupo | **fechada** — análise territorial executada, ver `ODS_ANALISE.md` |
| 8 | Prazo oficial da fase 3 | grupo | aberta — conferir no Classroom |
