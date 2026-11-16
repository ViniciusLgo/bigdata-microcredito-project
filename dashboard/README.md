# Dashboard

Painel em Streamlit que mostra o microcrédito por região, UF, segmento (PF e PJ) e modalidade, e cruza com o perfil de sexo e raça do IBGE para as ODS 5 e 18.

## O que tem

- 6 indicadores no topo. Quatro gerais: carteira ativa do último mês (com a variação de 12 meses), inadimplência, carteira por ocupado e quanto da carteira está nas 3 maiores UFs. Dois de gênero e raça: a participação do grupo escolhido na lateral (por exemplo, mulheres pretas e pardas) entre os ocupados das UFs filtradas, e quantas vezes a carteira por ocupado é maior nas UFs com mais desse grupo do que nas demais;
- filtros na lateral: período, região, UF, segmento, modalidade e o perfil da UF (sexo, cor ou raça e participação mínima do grupo);
- um seletor de métrica (carteira ativa, inadimplência, operações ou carteira por ocupado) que muda todos os gráficos;
- aba Evolução: linhas no tempo, agrupadas por região, UF, segmento ou modalidade, e as séries nacionais da SGS;
- aba Ranking e detalhe: barras por região, e dali dá para abrir as UFs da região e depois uma UF por modalidade e segmento (drill-down);
- aba ODS 5 e 18: dispersão entre a participação do grupo escolhido e o microcrédito por ocupado, com a correlação, a checagem sem o Nordeste e a ressalva da falácia ecológica;
- aba Dados: a tabela filtrada, com botão para baixar em CSV.

## Rodar no seu computador

Da raiz do projeto, no PowerShell:

```powershell
python -m pip install -r dashboard/requirements.txt
python -m streamlit run dashboard/app.py
```

Se você criou o ambiente `.venv` (passo do README principal), ative ele antes ou troque `python` por `.\.venv\Scripts\python.exe`.

Sem a variável `AIVEN_PG_URL`, o painel lê os CSVs do repositório (`data/processed/` e `data/ibge_sexo_raca_uf_2022.csv`). Para ler do banco da Aiven, defina a variável só naquela janela do terminal antes de rodar:

```powershell
$env:AIVEN_PG_URL = "postgres://USUARIO:SENHA@HOST:PORTA/defaultdb?sslmode=require"
```

Na lateral aparece de onde vieram os dados (banco ou CSV). Se o banco não responder, o painel avisa e usa os CSVs.

## Publicar no Streamlit Cloud

1. Entrar em share.streamlit.io com a conta do GitHub e criar um app novo apontando para este repositório, branch `main`, arquivo `dashboard/app.py`.
2. Em Advanced settings, na parte de Secrets, colocar (esse texto fica só na plataforma, nunca no Git):

```toml
AIVEN_PG_URL = "postgres://USUARIO:SENHA@HOST:PORTA/defaultdb?sslmode=require"
```

3. Depois de publicar, abrir o link e conferir se a lateral diz "banco PostgreSQL (Aiven)".

Uma ideia mais segura é criar na Aiven um usuário só de leitura para o painel e usar a URL dele nos secrets, em vez do usuário administrador.

## Como os números são calculados

- Carteira ativa é um saldo no fim do mês. Nos gráficos de ranking e nos indicadores, vale o último mês do período escolhido.
- A inadimplência é ponderada pela carteira: soma do valor inadimplente dividida pela soma da carteira, e não a média das taxas.
- As linhas com número de operações negativo ficam de fora da soma de operações, porque o BCB não explica esse valor.
- Carteira por ocupado divide a carteira pelas pessoas ocupadas por conta própria ou como empregador na UF (Censo 2022), e só existe por região ou UF.
