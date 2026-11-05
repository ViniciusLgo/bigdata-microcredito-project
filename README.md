# Projeto Big Data: Microcrédito e Inclusão Financeira Regional

Este é o nosso trabalho prático da disciplina de Big Data. O tema (Tema 05) é o acesso a microcrédito e a inclusão financeira regional, e a gente usa dados abertos do Banco Central do Brasil.

Integrantes: Vinicius Lago Cruz, Roberto Luis Jr., Guilherme Chaves e Maria Fernanda Prandi.

## Em que ponto estamos (05/11/2026)

A fase 2 está feita: já temos os scripts que baixam e tratam os dados, os CSVs finais e o modelo do banco. Conferimos os arquivos locais, e o que a gente fez antes registra que a carga na Aiven deu certo. Ainda precisamos entrar no banco de novo e guardar uma conferência atual.

Agora estamos na fase 3. Falta colocar a infraestrutura no Terraform, cuidar melhor das credenciais e explicar como rodar o projeto do começo ao fim. Cada um pegou uma parte, e o jeito de trabalhar com branches e revisão está no [CONTRIBUTING.md](CONTRIBUTING.md).

## De onde vêm os dados

- **API SGS** (Banco Central): séries nacionais de microcrédito, a 20618 e a 20712.
- **SCR.data** (Banco Central): crédito por UF, modalidade e tipo de cliente. Os ZIPs anuais (2021 a 2026) trazem CSVs mensais, e nós filtramos para as 27 UFs e para a submodalidade Microcrédito.

Na versão dos dados que conferimos em 03/11/2026, o SCR vai de janeiro/2021 a julho/2026, com 598.002 linhas depois do filtro e 7.080 linhas finais (3.618 de PF e 3.462 de PJ). A SGS vai de janeiro/2021 a agosto/2026 e ficou com 136 linhas finais. Repare que os períodos finais das duas fontes são diferentes.

Páginas oficiais: [SCR.data](https://dadosabertos.bcb.gov.br/dataset/scr_data), [SGS 20618](https://dadosabertos.bcb.gov.br/dataset/20618-saldo-da-carteira-de-credito-com-recursos-direcionados---pessoas-fisicas---microcredito-desti/resource/2c5b733e-6cfb-4474-b4c0-d1d956465c49) e [SGS 20712](https://dadosabertos.bcb.gov.br/en_GB/dataset/20712-concessoes-de-credito-com-recursos-direcionados---pessoas-fisicas---microcredito-total). Ainda falta montar uma lista dos arquivos que baixamos, com link, data de download e hash, para provar qual versão a gente usou.

Temos uma pendência com as ODS 5 e 18: nossos dados não têm gênero nem raça/cor. Vamos combinar com a professora como incluir esse recorte com uma fonte pública adequada, porque só comparar os estados não responde essa parte.

## Estrutura do projeto

```
etl/
  extrair_sgs.py      # baixa as séries da API SGS
  filtrar_scr.py      # filtra os zips do SCR.data com pandas chunking
  tratar.py           # converte tipos e agrega por UF, segmento, modalidade e mês
  carregar.py         # cria o schema e carrega no Postgres (Aiven)
  verificar_banco.py  # mostra tabelas, campos, relacionamentos e contagens
sql/
  schema.sql          # estrutura do banco
data/
  zip/       # zips originais do SCR.data (não vão pro git, são muito grandes)
  raw/       # json da SGS e csv filtrado (o csv não vai pro git)
  processed/ # csv final, pronto pra carga
  amostra/   # 20 linhas antes e depois do tratamento
```

## Como rodar

Tudo a partir da raiz do projeto. No PowerShell, primeiro criamos um ambiente isolado:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Para repetir o tratamento com a mesma versão dos dados, usamos os JSONs que já estão no repositório e colocamos os mesmos ZIPs anuais em `data/zip/` (eles não vêm no clone). O download dos ZIPs é manual, e por isso a lista de fontes acima ainda faz falta. Se a gente rodar a extração da SGS de novo, ela busca até o último dado disponível e o recorte pode mudar.

**Sobre a carga:** antes o `etl/carregar.py` apagava e recriava as quatro tabelas toda vez que rodava. Eu separei isso em flags, e agora cada coisa é explícita:

- `python etl/carregar.py` só carrega os dados. Se as tabelas não existirem, ele para e avisa, sem escrever nada;
- `python etl/carregar.py --criar-schema` cria só as tabelas que faltam (o `sql/schema.sql` não apaga nada) e depois carrega;
- `python etl/carregar.py --limpar` é a única que apaga as tabelas (o `sql/limpar.sql`), pede para digitar APAGAR e não carrega nada.

Os CSVs também são conferidos antes de abrir a conexão (arquivo, colunas, UF, PF/PJ e campos da chave vazios). Ainda falta tratar o caso de registro repetido (hoje ele só pula o que já existe) e contar o que entrou de verdade.

```bash
pip install -r requirements.txt

python etl/extrair_sgs.py
python etl/filtrar_scr.py
python etl/tratar.py

export AIVEN_PG_URL="postgres://usuario:senha@host:porta/defaultdb?sslmode=require"
python etl/carregar.py --criar-schema   # primeira vez, cria as tabelas que faltam
# python etl/carregar.py                # depois, só carrega os dados
python etl/verificar_banco.py
```

O exemplo acima é em Bash. No PowerShell, a conexão se define assim, trocando os campos pelos valores reais só no nosso terminal:

```powershell
$env:AIVEN_PG_URL = "postgres://USUARIO:SENHA@HOST:PORTA/defaultdb?sslmode=require"
```

A conexão nunca vai para o repositório. A variável precisa estar no ambiente do processo, porque o código ainda não lê o `.env` sozinho. Se o ambiente virtual não estiver ativado, rodamos os scripts com o Python dele.

## Como tratamos os dados

O `filtrar_scr.py` lê os CSVs de dentro dos ZIPs em pedaços (chunks) de 200 mil linhas, para não estourar a memória. Já o `tratar.py` abre inteiro o CSV filtrado, converte números e datas e agrega por UF, PF/PJ, modalidade e mês. CNAE, porte e as outras colunas não entram na granularidade final. As operações são somadas, e elas não representam clientes únicos.

A taxa de inadimplência é a carteira inadimplente somada dividida pela carteira ativa somada, com quatro casas decimais. Se a carteira for zero, a taxa fica nula. Ela é uma fração (0,05 quer dizer 5%), e não um percentual pronto. Ao juntar grupos não dá para tirar a média simples das taxas.

Na conferência local não encontramos chaves duplicadas nem campos vazios nos CSVs finais. Os dados agregados do SCR bateram com o arquivo intermediário e os valores da SGS bateram com os JSONs. Ainda faltam regras e testes para arquivo inválido, nulos e entrada duplicada. Também precisamos separar a conversão dos números da SGS (que pode vir com ponto decimal) da conversão brasileira do SCR.

## Banco de dados

Usamos um esquema estrela no PostgreSQL da Aiven, no plano gratuito:

- `dim_uf` e `dim_modalidade`: as dimensões;
- `fato_microcredito_nacional`: as séries nacionais da API SGS;
- `fato_credito_regional`: os dados do SCR.data, com 27 UFs, PF e PJ, a partir de 2021.

Escolhemos esse modelo porque deixa as consultas por estado, mês e modalidade mais simples. O volume diminui antes, na agregação. A fato regional tem granularidade UF × modalidade/segmento × mês e liga com as duas dimensões por chave estrangeira. A fato nacional tem granularidade série × mês e fica separada. Os tipos, as restrições e os índices estão no [sql/schema.sql](sql/schema.sql).

```mermaid
erDiagram
    dim_uf ||--o{ fato_credito_regional : uf_id
    dim_modalidade ||--o{ fato_credito_regional : modalidade_id
    fato_microcredito_nacional {
        integer serie_id
        date data_referencia
        decimal valor
    }
```

## Infraestrutura e segurança

O banco fica no PostgreSQL da Aiven, que no plano gratuito tem limite de 1 GB, como diz a [documentação oficial](https://aiven.io/docs/products/postgresql/concepts/pg-free-tier). Ainda precisamos consultar o serviço atual e o tamanho dele: os registros antigos falam em 7.247 linhas e 9,8 MB, mas ainda não confirmamos isso de novo no banco.

O Terraform está planejado, mas ainda não existe a pasta `terraform/`. Na fase 3 vamos descrever o serviço que já existe, de preferência adotando ele em vez de criar outro, e registrar a execução, porque só ter os arquivos não comprova nada.

A conexão vem da variável `AIVEN_PG_URL`, e o `.env` está no `.gitignore`. Falta ainda proteger no `.gitignore` o estado, os planos e as variáveis privadas do Terraform, e escrever como cuidar das credenciais. Nada com senha, token ou dados reais de conexão pode aparecer em documentação, evidência ou print.
