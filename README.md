# Projeto Big Data: microcrédito e inclusão financeira regional

Este é o nosso trabalho prático da disciplina de Big Data e Analytics (UCSal). O tema (Tema 05) é o acesso a microcrédito e a inclusão financeira regional, e a gente usa dados abertos do Banco Central do Brasil.

Integrantes: Vinicius Lago Cruz, Roberto Luis Jr., Guilherme Chaves e Maria Fernanda Prandi.

## Em que ponto estamos

A fase 2 está pronta: os scripts baixam e tratam os dados, os CSVs finais estão no repositório e o banco está modelado. A carga na Aiven já foi feita antes, mas ainda precisamos entrar de novo no banco e guardar uma conferência atual.

Na fase 3 já entraram a carga que pode rodar mais de uma vez, os testes dela, o Terraform e a análise territorial das ODS 5 e 18. Falta o guia de segurança das credenciais, a conferência final do banco e testar o README do zero com alguém que não escreveu ele. O que cada item do enunciado exige, e onde está a prova, fica em [docs/CHECKLIST_ENTREGA.md](docs/CHECKLIST_ENTREGA.md). O jeito de trabalhar com branches e revisão está no [CONTRIBUTING.md](CONTRIBUTING.md).

## O que o projeto faz

É um pipeline em Python que baixa, filtra, trata e carrega dados públicos de microcrédito num PostgreSQL na nuvem, para a gente analisar por estado (UF).

```
ZIPs anuais do SCR.data -> filtro em chunks -> CSV intermediário -> agregação -> fato regional   \
                                                                                                  -> PostgreSQL (Aiven)
API SGS (2 séries)      -> JSON bruto       -> conversão                      -> fato nacional   /
```

O recorte atual é de 27 UFs, só a submodalidade Microcrédito, de janeiro/2021 a julho/2026. A série nacional vai até agosto/2026, então os períodos das duas fontes não terminam no mesmo mês.

## De onde vêm os dados

| Fonte | O que traz | Endereço |
|---|---|---|
| SCR.data (BCB, versão 2) | Crédito agregado por UF, tipo de cliente, modalidade e mês. Vem em ZIPs anuais com um CSV por mês. | `https://www.bcb.gov.br/pda/desig/scrdata_{ANO}.zip` |
| API SGS (BCB) | Duas séries nacionais mensais, em milhões de reais: a 20618 (saldo da carteira de pessoa física, microcrédito a microempreendedores) e a 20712 (concessões de pessoa física, microcrédito total). | `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados?formato=json` |

A metodologia do SCR.data está em <https://www.bcb.gov.br/pda/desig/metodologia_versao2.pdf>. A licença dos dados é a Open Data Commons ODbL.

Em [data/manifesto-fontes.csv](data/manifesto-fontes.csv) está a lista de tudo o que usamos, com link, período, tamanho e hash SHA-256, para provar qual versão foi usada.

Os ZIPs do SCR.data não vão para o Git porque somam quase 1 GB. Para refazer o download, baixe um ZIP por ano (2021 a 2026) pelo endereço acima e coloque em `data/zip/`. Cada ZIP tem os CSVs mensais daquele ano, separados por ponto e vírgula.

Na versão que conferimos em 03/11/2026, o SCR ficou com 598.002 linhas depois do filtro e 7.080 linhas finais (3.618 de PF e 3.462 de PJ). A SGS ficou com 136 linhas finais.

## Estrutura do repositório

```
etl/
  extrair_sgs.py       baixa as séries 20618 e 20712 da API SGS
  filtrar_scr.py       filtra os ZIPs do SCR.data lendo os CSVs em chunks de 200.000 linhas
  tratar.py            converte tipos e agrega por UF, cliente (PF/PJ), modalidade e mês
  carregar.py          carrega no PostgreSQL (Aiven)
  verificar_banco.py   mostra tabelas, campos, relacionamentos e contagens
sql/
  schema.sql           cria as tabelas que faltam (não apaga nada)
  limpar.sql           apaga as tabelas, só usado com a flag --limpar
terraform/             infraestrutura como código (serviço PostgreSQL na Aiven)
tests/
  test_carga.py        testes da carga, rodam só em Postgres local
analise/
  ods_cruzamento.py    cruza o microcrédito com o IBGE para as ODS 5 e 18
  montar_ibge.py       monta a tabela do IBGE usada no cruzamento
data/
  manifesto-fontes.csv       origem, versão e hash de cada arquivo
  ibge_ocupacao_uf_2022.csv  base do IBGE por UF usada na análise das ODS
  zip/                       ZIPs originais do SCR.data (fora do Git)
  raw/                       JSONs da SGS e o CSV filtrado (o CSV fica fora do Git)
  processed/                 CSVs finais, prontos para a carga
  amostra/                   20 linhas antes e depois do tratamento
docs/
  DICIONARIO_DADOS.md   campos, tipos, chaves, origem e unidades
  DECISOES_TECNICAS.md  decisões de tratamento e modelagem, com as justificativas
  ODS_ANALISE.md        resultado do cruzamento com o IBGE
  CHECKLIST_ENTREGA.md  cada item do enunciado e o arquivo que comprova
  evidencias/           saídas das execuções, sem credenciais
```

## Tratamento dos dados

O SCR.data vem muito grande, então a filtragem lê os CSVs aos poucos (chunks de 200.000 linhas) e guarda só as 27 UFs e a submodalidade Microcrédito. Depois o `tratar.py` converte os tipos (datas, números com vírgula, percentuais), separa pessoa física e jurídica a partir da coluna `cliente` e agrega por UF, segmento, modalidade e mês. As séries da SGS só são convertidas e empilhadas num formato único.

Cada decisão e o motivo dela estão em [docs/DECISOES_TECNICAS.md](docs/DECISOES_TECNICAS.md). Para ver o antes e o depois, olhe os arquivos de `data/amostra/`.

## Modelagem do banco

Usamos um esquema estrela simplificado no PostgreSQL (Aiven, plano gratuito), com duas dimensões e duas tabelas fato. Escolhemos assim porque os dados já chegam agregados e o dashboard vai filtrar por ano, UF e modalidade, então um modelo todo normalizado seria exagero.

| Tabela | Cada linha é | Linhas esperadas |
|---|---|---|
| `dim_uf` | uma UF | 27 |
| `dim_modalidade` | uma modalidade por segmento (PF ou PJ) | 4 |
| `fato_credito_regional` | UF, segmento, modalidade e mês | 7.080 |
| `fato_microcredito_nacional` | série e mês | 136 |
| total | | 7.247 |

A `fato_credito_regional` se liga às duas dimensões por chave estrangeira. A `fato_microcredito_nacional` não se liga a nenhuma, porque é a série nacional da SGS, com outra fonte e outra granularidade. Não há dado de pessoa nem identificação de quem tomou o crédito. Os campos e tipos estão em [docs/DICIONARIO_DADOS.md](docs/DICIONARIO_DADOS.md) e o SQL está em [sql/schema.sql](sql/schema.sql).

## Infraestrutura (Terraform)

O banco é um serviço PostgreSQL da Aiven, plano `free-1-1gb`. A pasta [terraform/](terraform/) descreve esse serviço como código:

| Arquivo | Para que serve |
|---|---|
| `main.tf` | versão do Terraform, provider da Aiven e o recurso `aiven_pg` (com proteção contra apagar) |
| `variables.tf` | projeto, nome do serviço e versão do PostgreSQL |
| `outputs.tf` | host, porta e nome do banco, nunca usuário nem senha |
| `terraform.tfvars.example` | modelo dos valores, com dados de exemplo |
| `.terraform.lock.hcl` | trava a versão exata do provider |

O serviço já existia, então o Terraform só passa a descrevê-lo. O `terraform.tfvars` com os valores reais fica fora do Git. Como o recurso tem `prevent_destroy`, um `terraform destroy` por engano é bloqueado.

## Segurança das credenciais

Nenhuma senha, token ou URL de conexão vai para o repositório. Na prática:

- a URL do banco fica só na variável de ambiente `AIVEN_PG_URL`, definida no terminal de quem vai rodar;
- o token da Aiven usado pelo Terraform também fica fora do código, em variável de ambiente;
- o `.gitignore` bloqueia `.env`, `*.tfstate`, `*.tfvars`, `.terraform/` e logs do Terraform, e deixa passar só os modelos (`*.tfvars.example`) e o `.terraform.lock.hcl`;
- os outputs do Terraform mostram só host, porta e nome do banco;
- as evidências em `docs/evidencias/` não podem ter URL completa, usuário nem senha.

Falta escrever o guia completo dessa parte em `docs/SEGURANCA.md`.

## Como rodar

Tudo a partir da raiz do projeto. No PowerShell, primeiro criamos um ambiente isolado:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Para repetir o tratamento com a mesma versão dos dados, usamos os JSONs que já estão no repositório e colocamos os ZIPs anuais em `data/zip/`, porque eles não vêm no clone. Se rodarmos a extração da SGS de novo, ela busca até o último dado disponível e o recorte pode mudar.

```bash
python etl/extrair_sgs.py        # gera data/raw/sgs_20618.json e sgs_20712.json
python etl/filtrar_scr.py        # gera data/raw/scr_microcredito_brasil_raw.csv
python etl/tratar.py             # gera os dois CSVs em data/processed/
```

Depois vem a carga. A URL de conexão fica só em variável de ambiente:

```bash
export AIVEN_PG_URL="postgres://usuario:senha@host:porta/defaultdb?sslmode=require"
python etl/carregar.py --criar-schema   # primeira vez, cria as tabelas que faltam
# python etl/carregar.py                # nas outras vezes, só carrega os dados
python etl/verificar_banco.py
```

Sobre a carga, cada flag faz uma coisa:

- `python etl/carregar.py` só carrega. Se as tabelas não existirem, para e avisa, sem escrever nada;
- `python etl/carregar.py --criar-schema` cria só as tabelas que faltam e depois carrega;
- `python etl/carregar.py --limpar` é a única que apaga as tabelas, pede para digitar APAGAR e não carrega nada.

Os CSVs são conferidos antes de abrir a conexão (arquivo, colunas, UF, PF/PJ, campos da chave vazios e chave repetida). A carga pode rodar mais de uma vez: registro novo é inserido, registro que mudou é atualizado e registro igual fica como está. No final o script mostra quantos foram de cada tipo. Se a conexão cair no meio, o que já foi salvo continua no banco e é só rodar de novo.

Os testes da carga precisam de um Postgres descartável, porque apagam e recriam as tabelas. Eles só rodam se a variável `TESTE_PG_URL` apontar para `localhost`, então nunca encostam na Aiven:

```powershell
docker run -d --name pg-teste -e POSTGRES_PASSWORD=teste -p 55432:5432 postgres:17
$env:TESTE_PG_URL = "postgres://postgres:teste@localhost:55432/postgres?sslmode=disable"
python -m unittest discover -s tests -v
```

A análise das ODS não precisa de banco, só dos CSVs versionados:

```bash
python analise/ods_cruzamento.py
```

Para conferir se os CSVs do repositório são os mesmos que usamos, compare os hashes com o manifesto:

```bash
sha256sum data/processed/*.csv data/raw/*.json
```

## Como ler os números

| Campo | O que é | O que não é |
|---|---|---|
| `quantidade_operacoes` | número de operações de crédito | número de clientes |
| `valor_carteira_ativa` | saldo no fim do mês | valor concedido no mês |
| `taxa_inadimplencia` | fração de 0 a 1, então 0,05 é 5% | percentual já multiplicado por 100 |
| séries 20618 e 20712 | milhões de reais, só PF, só crédito direcionado | mesma unidade e abrangência do recorte regional |
| `segmento` (nosso) | PF ou PJ, vindo da coluna `cliente` do SCR.data | o campo `segmento` do SCR.data, que é o segmento da instituição financeira |

As datas do regional usam o último dia do mês, e as do nacional usam o dia 01. Para comparar as duas, alinhe o mês e use só o período comum (jan/2021 a jul/2026).

## O que a análise territorial mostrou

Resumo de [docs/ODS_ANALISE.md](docs/ODS_ANALISE.md), com dados de 2022:

- O microcrédito é concentrado. As 9 UFs do Nordeste ficam com 62,1% da carteira nacional, com mediana de R$ 1.236 por ocupado (conta própria ou empregador), contra R$ 167 a R$ 240 nas outras regiões.
- ODS 18: UFs com mais pessoas pretas e pardas têm mais microcrédito por ocupado (Spearman 0,455, p = 0,017). Sem o Nordeste, a relação perde força (0,358, p = 0,145). O que aparece é onde a oferta está, e não o acesso de cada grupo racial.
- ODS 5: não achamos associação com a participação de mulheres (Spearman −0,227, p = 0,255). A nossa base não tem sexo, então só dá para olhar o território.
- Fora das ODS, o achado mais forte foi que onde há mais microcrédito por ocupado a inadimplência é menor (Spearman −0,871, p < 0,0001). O Piauí tem R$ 2.297 por ocupado e 5,9% de inadimplência, e o Rio de Janeiro tem R$ 113 e 22,4%.

## Limitações

- A base não tem sexo, gênero, cor ou raça. Por isso a análise das ODS é territorial: cruza a carteira por UF com o Censo 2022 do IBGE. Ela descreve estados, não quem pegou o crédito, e concluir sobre pessoas a partir de médias por UF seria falácia ecológica.
- 1.084 das 7.080 linhas (15,3%) têm `quantidade_operacoes` negativa (mínimo −32). A metodologia do BCB não explica essa regra. Mantivemos os valores como vieram e usamos a carteira ativa como indicador principal.
- A metodologia do SCR.data não diz a unidade de `carteira_ativa`. Tratamos como reais pela ordem de grandeza.
- Só a filtragem usa chunks. O tratamento abre o CSV intermediário inteiro, então o pipeline é em lote com leitura em partes, e não processamento distribuído.
- O `extrair_sgs.py` não fixa a data final, então cada execução pode trazer meses novos. Para reproduzir a versão analisada, use os JSONs do repositório.
- A camada não relacional (OpenSearch) não foi feita, porque é opcional no guia.

## Documentação

| Arquivo | Para que serve |
|---|---|
| [data/manifesto-fontes.csv](data/manifesto-fontes.csv) | de onde veio cada arquivo, qual versão e com qual hash |
| [docs/DICIONARIO_DADOS.md](docs/DICIONARIO_DADOS.md) | o que é cada campo em cada camada |
| [docs/DECISOES_TECNICAS.md](docs/DECISOES_TECNICAS.md) | por que o tratamento é assim e o que ele não permite afirmar |
| [docs/ODS_ANALISE.md](docs/ODS_ANALISE.md) | cruzamento com o IBGE para as ODS 5 e 18, com método e limites |
| [docs/CHECKLIST_ENTREGA.md](docs/CHECKLIST_ENTREGA.md) | item do enunciado e o arquivo que comprova |
| [CONTRIBUTING.md](CONTRIBUTING.md) | como o grupo trabalha com branches e revisão |
