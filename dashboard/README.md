# Microcrédito no Brasil

Painel em Streamlit para apresentar a evolução da carteira de microcrédito, as diferenças entre estados e o contexto territorial das ODS 5 e 18. Utiliza o SCR.data e as séries SGS do Banco Central, além do perfil dos ocupados do Censo 2022 do IBGE.

Publicado em: [microcredito-bigdata.streamlit.app](https://microcredito-bigdata.streamlit.app/).

## Organização do painel

| Seção | Conteúdo |
| --- | --- |
| Panorama | Carteira ativa, variação em 12 meses quando comparável, inadimplência ponderada, carteira por ocupado e concentração nas três maiores UFs. Ranking dos estados e distribuição regional. |
| Evolução e estados | Séries mensais de carteira, inadimplência e carteira por ocupado. Comparação por região ou UF, com agrupamento por cliente/modalidade quando adequado. Detalhamento de região, UF e modalidade. Séries nacionais SGS em gráficos separados. |
| Contexto ODS | Perfil territorial por sexo e cor ou raça. Comparação da carteira média de 2022 por ocupado com o Censo do mesmo ano, correlação de Spearman e análise de sensibilidade sem o Nordeste. |
| Fontes e dados | Origem efetivamente carregada, cobertura, limites de interpretação, registros filtrados e downloads CSV. |

O visual usa fundo claro, tipografia simples e cores consistentes por região. As opções de tema ficam em `.streamlit/config.toml`, na raiz do projeto.

## Filtros e referências temporais

- O intervalo mensal inclui os meses inicial e final selecionados, mesmo quando uma fonte registra o primeiro dia e outra o último dia do mês.
- Região, UF, tipo de cliente (PF/PJ) e modalidade definem o recorte regional. Uma seleção vazia inclui todas as opções.
- Os indicadores do Panorama e o ranking mostram o último mês disponível no recorte. Carteira ativa é **saldo**, portanto não se somam saldos de diferentes meses para apresentar um total anual.
- A variação em 12 meses só aparece quando o mesmo conjunto de UF, segmento e modalidade está disponível nos dois meses e a carteira anterior é positiva. Caso contrário, o painel informa a indisponibilidade.
- As séries nacionais SGS usam o mesmo período mensal. Região, UF, cliente e modalidade não se aplicam a elas: representam somente PF e recursos direcionados, em universo diferente do SCR regional. Saldo e concessões são apresentados separadamente, em milhões de reais.
- A seção ODS usa **2022 fixo**, independentemente do intervalo mensal escolhido. Preserva os filtros de território, cliente e modalidade. Sexo, cor ou raça e participação mínima do grupo são controles locais dessa seção.
- No cruzamento ODS, primeiro são somados os saldos das modalidades de cada UF em cada mês; depois é calculada a média dos 12 saldos mensais. UFs sem os 12 meses são excluídas da comparação anual.

## Cuidados com os indicadores

O SCR regional não identifica sexo, gênero, cor ou raça dos tomadores de crédito. O perfil do IBGE descreve o território: pessoas com 14 anos ou mais ocupadas por conta própria ou como empregadoras. O painel não demonstra quanto crédito mulheres ou pessoas de determinada raça receberam, nem permite filtros por idade. Associação entre estados não implica causalidade ou conclusão individual.

A carteira por ocupado usa um denominador fixo do Censo 2022; fora da seção ODS, o numerador pode ser de outro ano. Esse indicador não é um valor recebido por pessoa. No cruzamento ODS, a carteira pode incluir PF e PJ, enquanto o denominador é de pessoas ocupadas.

A inadimplência é ponderada pela carteira, e não a média simples das taxas. O resultado é aproximado porque o ETL já arredonda as taxas. A unidade monetária do SCR é tratada como reais por inferência documentada no projeto; a unidade SGS é milhões de reais.

Quantidade de operações contém valores negativos cujo significado não foi confirmado. Por isso, **não aparece como KPI nem como métrica dos gráficos**. O campo original permanece disponível na tabela e no CSV do recorte. Ausência de informação não é preenchida com zero; correlações sem variação ou observações suficientes são apresentadas como indisponíveis.

## Executar localmente

Execute os comandos a partir da raiz do repositório. No macOS ou Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r dashboard/requirements.txt
python -m streamlit run dashboard/app.py
```

No Windows, PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r dashboard/requirements.txt
.\.venv\Scripts\python.exe -m streamlit run dashboard/app.py
```

Se o ambiente já existir, reutilize-o. O arquivo `requirements.txt` da raiz contém dependências do ETL e da análise; para executar o painel, use também `dashboard/requirements.txt`.

Sem `AIVEN_PG_URL`, o aplicativo lê os três CSVs versionados:

- `data/processed/fato_credito_regional.csv`
- `data/processed/fato_microcredito_nacional.csv`
- `data/ibge_sexo_raca_uf_2022.csv`

Para usar Aiven, forneça `AIVEN_PG_URL` pelo ambiente do processo ou pelos secrets do Streamlit. Exemplo de formato, com valores fictícios:

```toml
AIVEN_PG_URL = "postgres://USUARIO:SENHA@HOST:PORTA/defaultdb?sslmode=require"
```

O arquivo `.env` não é carregado automaticamente. Não inclua uma URL real no código, Git, capturas ou logs. Prefira uma credencial de leitura; o aplicativo também configura a sessão PostgreSQL como somente leitura.

O banco só é usado quando **as três bases estão disponíveis e passam pela validação**. Se a conexão, alguma consulta ou a validação falhar, todo o conjunto volta aos CSVs e um aviso aparece. O painel não mistura silenciosamente crédito do banco com perfil do CSV. Se os próprios CSVs forem inválidos, a tela informa o problema em vez de apresentar dados parciais.

A origem carregada aparece na lateral e em Fontes e dados. A leitura tem cache de uma hora; **Atualizar leitura** limpa esse cache e tenta carregar novamente. Isso não executa o ETL nem altera o banco.

## Verificação

Os testes de cálculos e carregamento não precisam abrir Streamlit nem acessar Aiven:

```bash
python -m unittest discover -s tests -p 'test_dashboard*.py' -v
```

Antes de apresentar, abra o painel com os CSVs e confira: troca de mês, filtros de UF e modalidade, comparação com 12 meses antes, seção ODS fixa em 2022 e downloads. Para demonstrar a conexão Aiven, confira que a origem exibida é o banco; um fallback CSV não comprova a conexão.

## Publicação no Streamlit Community Cloud

1. Envie a alteração em uma branch e abra PR conforme `CONTRIBUTING.md`. Use a branch revisada na implantação.
2. Na plataforma Streamlit, selecione o repositório, a branch que contém o painel e `dashboard/app.py` como arquivo de entrada.
3. Confira que as dependências de `dashboard/requirements.txt` foram instaladas e que os CSVs versionados estão acessíveis.
4. Para usar Aiven, configure `AIVEN_PG_URL` nos secrets da aplicação. Para demonstração com CSVs, esse secret é dispensável.
5. Abra a aplicação publicada e repita a verificação dos filtros, fontes e downloads. Confirme a origem carregada antes de gravar o vídeo.

## Roteiro de demonstração de um minuto

| Tempo | Demonstração e fala sugerida |
| --- | --- |
| 0–15 s | No Panorama: “Este painel mostra os saldos de microcrédito por estado. Estes indicadores são do último mês disponível, e a inadimplência é ponderada pela carteira.” |
| 15–30 s | Em Evolução e estados, selecione uma região e abra uma UF: “Podemos acompanhar a evolução mensal e comparar estados, clientes e modalidades.” |
| 30–50 s | Em Contexto ODS, mantenha mulheres pretas e pardas: “Aqui comparamos a carteira média de 2022 com o perfil territorial do Censo. A análise descreve os estados; não identifica quem recebeu crédito.” |
| 50–60 s | Em Fontes e dados, mostre a origem e o download: “As fontes e limitações estão explícitas, e o recorte pode ser exportado para conferência.” |

Referências do projeto: `docs/DICIONARIO_DADOS.md`, `docs/DECISOES_TECNICAS.md` e `docs/ODS_ANALISE.md`.
