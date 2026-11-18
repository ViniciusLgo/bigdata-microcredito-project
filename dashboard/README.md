# Dashboard

Painel em Streamlit que mostra o microcrédito por região, UF, segmento (PF e PJ) e modalidade, e cruza com o perfil de sexo e raça do IBGE para as ODS 5 e 18.

## O que tem

Uma página só, de cima para baixo. Cada seção é uma pergunta, com um gráfico e uma frase dizendo o que está sendo comparado:

1. Os números principais: saldo, mudança em 12 meses, inadimplência e a parte do Nordeste;
2. Como o saldo mudou desde 2021, no Brasil todo ou por região;
3. Em quais estados está o microcrédito, no total ou por pessoa que trabalha por conta própria, com um detalhe por estado;
4. Gênero e raça: compara os estados com mais e com menos mulheres, pessoas pretas e pardas entre os ocupados, com e sem o Nordeste, e explica a ressalva de que a comparação é entre estados e não entre pessoas.

Os filtros ficam no topo: ano, região, tipo de cliente (PF e PJ) e, em "Mais filtros", modalidade e estados.

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
