# Decisões técnicas

Tema 05: acesso a microcrédito e inclusão financeira regional.

Aqui o grupo registra as escolhas que fez no tratamento e na modelagem, o motivo de cada uma e o que ela não deixa a gente afirmar. Os números foram conferidos nos CSVs do repositório (os hashes estão em `data/manifesto-fontes.csv`). Última revisão: 15/11/2026.

## 1. Recorte dos dados

### Janeiro/2021 em diante

As duas fontes começam em janeiro/2021. Na SGS isso está no código (`dataInicial=01/01/2021` em `etl/extrair_sgs.py`). No SCR.data não está: o `etl/filtrar_scr.py` lê todos os ZIPs que estiverem em `data/zip/`, então o início em 2021 depende de quais arquivos foram baixados. Quem colocar um ZIP de 2019 na pasta aumenta a base sem perceber.

Escolhemos 2021 porque cinco anos e meio de dados já respondem à análise regional, e o plano gratuito da Aiven tem 1 GB.

### Brasil inteiro, 27 UFs

A primeira versão só filtrava o Nordeste. Ampliamos para o país todo porque o volume agregado cabe com folga no banco e porque comparar o Nordeste com as outras regiões é justamente a pergunta de inclusão financeira regional. O CSV antigo só do Nordeste ainda existe em `data/raw/`, mas o pipeline atual não usa.

### Filtro pela submodalidade

No arquivo real do BCB não existe `modalidade = Microcrédito`. O microcrédito aparece na coluna `submodalidade`, dentro de `Empréstimos` e `Financiamentos`. Por isso o filtro é `submodalidade == "Microcrédito"`, e o rótulo guardado junta as duas colunas (por exemplo, `Empréstimos - Microcrédito`).

Isso é uma decisão de escopo: analisamos a submodalidade Microcrédito do SCR, que não é o mesmo que o universo das políticas de microcrédito.

## 2. Tratamento

### Leitura em chunks

Cada CSV mensal do SCR tem uns 100 MB e são 67 arquivos. O `filtrar_scr.py` lê em pedaços de 200.000 linhas e já descarta o que não interessa, então o arquivo inteiro nunca fica na memória.

Só a filtragem usa chunks. O `tratar.py` abre o CSV filtrado inteiro. Por isso o pipeline é em lote com leitura em partes na etapa mais pesada, e não processamento distribuído. Vamos dizer isso assim na apresentação.

### PF e PJ separados

A coluna `cliente` do SCR diz se a linha é pessoa física ou jurídica, e ela entra na agregação. Sem isso o número somaria públicos diferentes. Cuidado com o nome: no nosso banco essa coluna virou `segmento`, mas no SCR.data `segmento` é o tipo de instituição financeira (banco, cooperativa, fintech). O campo original do BCB não é usado.

### Agregação por UF, cliente, modalidade e mês

O `tratar.py` soma carteira ativa, carteira inadimplente e número de operações nesse nível. Ficam de fora, somadas, as colunas de tipo de instituição, CNAE da ocupação, porte, origem dos recursos e indexador. Cortamos para não multiplicar as combinações e estourar o plano gratuito.

Consequências:

- duas linhas iguais nos campos finais não são duplicata, porque podem vir de CNAEs ou portes diferentes na origem. Por isso não removemos duplicata por semelhança;
- a base não responde nada sobre porte, setor ou tipo de instituição.

### Quantidade de operações negativa

Em 1.085 das 7.081 linhas (15,3%) o `quantidade_operacoes` é negativo, com mínimo de −32. A metodologia do BCB não explica essa regra (se é supressão, ajuste ou outra coisa).

Decidimos manter os valores como vieram, sem virar zero e sem apagar a linha, e anotar no dicionário que o campo não vale como contagem. Qualquer indicador de operações precisa excluir essas linhas e dizer quantas foram. O indicador principal do trabalho é a carteira ativa. Falta confirmar o critério com o BCB, então fica declarado como lacuna.

### Conversão dos números

| Fonte | Como vem | Conversão |
|---|---|---|
| SCR.data (CSV) | `1.234,56`, com ponto de milhar e vírgula decimal | tirar o ponto e trocar a vírgula por ponto |
| SGS (JSON) | `123.45`, com ponto decimal | converter direto |

Antes o `tratar.py` usava a mesma função para as duas, e isso era um risco: se a SGS mandasse `"123.45"`, o ponto sumia e o valor virava `12345`. Nos JSONs que temos os valores são inteiros, então nada saiu errado, mas foi sorte. Agora são duas funções separadas (`numero_scr` e `numero_sgs`), com testes em `tests/test_tratamento.py`. Rodamos o tratamento de novo e os CSVs finais ficaram idênticos, com o mesmo hash.

### Taxa de inadimplência

O BCB não entrega a taxa. Nós calculamos `carteira_inadimplente / carteira_ativa`, arredondada em 4 casas, e deixamos nula quando a carteira é zero. É uma fração: 0,05 quer dizer 5%.

Para juntar UFs ou meses não se faz média simples das taxas. Soma-se o valor inadimplente e a carteira e divide-se de novo (média ponderada pela carteira). Há 39 linhas com taxa igual a 1, que são válidas mas distorcem a média simples.

## 3. Modelagem

### Duas dimensões, duas fatos e uma tabela de perfil

O `sql/schema.sql` tem `dim_uf`, `dim_modalidade`, `fato_credito_regional` e `fato_microcredito_nacional`.

A regional se liga às duas dimensões por chave estrangeira. A nacional não se liga a nada, porque é a série da SGS, sem UF nem modalidade, com outra fonte e outra granularidade. Não inventamos chave só para fechar um desenho de estrela. Por isso chamamos de modelo dimensional simplificado com duas tabelas fato independentes.

A `perfil_ocupados_uf` guarda o perfil do IBGE (sexo e cor ou raça por UF) no próprio banco, para o dashboard filtrar sem depender de arquivo solto. Ela se liga só à `dim_uf`, porque vem de outra fonte e de outro ano, e não se junta ao crédito linha a linha.

Não normalizamos mais porque os dados já chegam agregados, o dashboard vai filtrar por ano, UF e modalidade, e menos junções é melhor no plano gratuito.

### Datas das duas fontes

O regional usa o último dia do mês e o nacional usa o dia 01. Mantivemos as datas de origem. Para comparar, é preciso alinhar o mês (por exemplo, `date_trunc('month', data_referencia)`) e usar só o período comum, de janeiro/2021 a julho/2026. Sem isso, agosto/2026 aparece só no nacional e parece uma queda no regional.

### O que cada número significa

Está na tabela "Como ler os números" do README. As confusões mais fáceis são tratar a carteira (um saldo) como valor concedido no mês, somar 12 meses de carteira como se fosse total do ano, e achar que as séries da SGS (em milhões de reais, só pessoa física) têm a mesma abrangência do recorte regional.

## 4. Carga e reprodução

### Carga que pode rodar mais de uma vez

O `etl/carregar.py` não apaga mais nada sozinho. Criar tabelas, carregar e apagar são três ações separadas por flag (`--criar-schema`, sem flag e `--limpar`). Antes de abrir a conexão, ele confere os CSVs (arquivo, colunas, UF, PF/PJ, campos da chave vazios e chave repetida). Na carga, registro novo é inserido, registro mudado é atualizado e registro igual fica quieto, e o script mostra quantos foram de cada tipo.

Escolhemos atualizar em vez de pular o que já existe porque o BCB corrige dados antigos. O ZIP de 2025 que a professora mandou é um exemplo: setembro/2025 foi republicado com valores diferentes.

### Versão dos dados usada

A professora enviou uma versão atualizada do `scrdata_2025.zip` (arquivo de 14/11/2026). Só o CSV de setembro/2025 mudou: 125 linhas a mais no arquivo original, 84 linhas com valor diferente no resultado final e 1 linha nova (SE, PJ, Financiamentos). A carteira nacional do mês subiu R$ 29 mil, de R$ 9,87 bilhões. O grupo passou a usar essa versão, e o hash dela está no manifesto. A base final foi de 7.080 para 7.081 linhas regionais.

Outros cuidados de reprodução:

- o `extrair_sgs.py` não fixa a data final, então cada execução pode trazer meses novos. Para repetir a versão analisada, use os JSONs do repositório;
- os ZIPs do SCR não vão para o Git (quase 1 GB). O manifesto tem o endereço de cada um, o tamanho e o hash;
- o ZIP do ano corrente é atualizado todo mês pelo BCB, por isso registramos o período usado (2021-01 a 2026-07).

### Camada não relacional

O guia cita OpenSearch como opcional. Não implementamos. Todos os dados estão no PostgreSQL da Aiven, que já atende o que o dashboard precisa (filtros e somas por UF, ano e modalidade). Vamos declarar isso na entrega, em vez de deixar o item de fora.

## 5. ODS 5 e 18

### O que a base não permite

Nenhuma coluna do SCR tem sexo, gênero, cor ou raça. Então frases como "mulheres acessam menos microcrédito no Nordeste" não dá para sustentar com os nossos dados.

### O que fizemos no lugar

Uma análise territorial: cruzamos a carteira de microcrédito por UF com o perfil de quem trabalha por conta própria ou como empregador naquela UF, vindo do Censo 2022 do IBGE (tabela SIDRA 10261). A unidade é o estado, não a pessoa. Nenhum atributo foi atribuído a nenhuma operação de crédito, e as bases não são juntadas linha a linha.

A tabela do IBGE tem sexo e cor ou raça cruzados, então também calculamos a participação de mulheres pretas e pardas por UF, para olhar as duas ODS juntas. Método, resultados e limites estão em [ODS_ANALISE.md](ODS_ANALISE.md).

### A ressalva que vai em todo lugar

> Os dados de microcrédito do SCR.data são agregados por UF e não têm sexo, gênero, cor ou raça. O cruzamento com o IBGE descreve o território, não o perfil de quem pegou o crédito. Concluir algo sobre pessoas a partir de médias por estado é falácia ecológica.

Ela precisa aparecer no relatório e no dashboard.

### Sobre o ODS 18

É a meta de igualdade étnico-racial, proposta pelo Brasil na ONU em 2023 e coordenada pelo Ministério da Igualdade Racial. Não faz parte dos 17 ODS globais da Agenda 2030, e vamos dizer isso na apresentação.

### Escolha feita sem consultar a professora

O grupo seguiu com a análise territorial porque é a única leitura que os dados sustentam. Se a professora quiser sexo e raça por pessoa, a base atual não serve e seria preciso outra fonte.

## 6. Pendências

| Pendência | Quem | Situação |
|---|---|---|
| Critério dos valores negativos em `numero_de_operacoes` | grupo e BCB | declarada como lacuna |
| Unidade monetária de `carteira_ativa` | grupo e BCB | tratada como reais, por inferência |
| Conferir o banco da Aiven com a versão nova dos dados | Vinicius | aberta |
| Fonte com sexo e raça no microcrédito | grupo e professora | aberta |
| Prazo oficial da fase 3 | grupo | conferir no Classroom |
