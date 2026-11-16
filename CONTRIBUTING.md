# Preparando o ambiente

Depois de clonar, eu abro o PowerShell na pasta do projeto e rodo:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Depois uso o Python desse ambiente (`.\.venv\Scripts\python.exe`) para rodar os scripts. Os CSVs finais, os JSONs da SGS e as amostras já estão no Git. Os ZIPs e o CSV filtrado do SCR não estão, porque são muito grandes. Mesmo sem eles dá para estudar o código e escrever testes usando as amostras.

Sobre o `etl/carregar.py` no banco do grupo: ele não apaga mais as tabelas sozinho. O `DROP` saiu do `sql/schema.sql` e foi para o `sql/limpar.sql`, que só roda com `--limpar` e depois de digitar APAGAR. A carga também pode rodar mais de uma vez: registro novo entra, registro que mudou é atualizado e registro igual fica como está. Mesmo assim, antes de mexer no banco do grupo a gente testa em um Postgres descartável (o passo a passo está no README). Para só olhar o que tem no banco, usamos o `etl/verificar_banco.py`, que apenas lê.

Os ZIPs do SCR ficam em `data/zip/`. O `scrdata_2025.zip` que a professora mandou é uma versão atualizada (só o mês de setembro/2025 mudou), então é essa que usamos. Quem for rodar o tratamento precisa dela, e o hash certo está no `data/manifesto-fontes.csv`.

Esse script lê a conexão da variável de ambiente `AIVEN_PG_URL`. O código ainda não lê o `.env` sozinho, então eu defino a variável no terminal, só naquela sessão:

```powershell
$env:AIVEN_PG_URL = "postgres://USUARIO:SENHA@HOST:PORTA/defaultdb?sslmode=require"
```

Troco USUARIO, SENHA, HOST e PORTA pelos valores do painel da Aiven, sem colar a senha em lugar nenhum além do meu terminal.

## Uma branch para cada parte

Antes de começar uma tarefa eu confiro se não tenho nada pendente, atualizo a `main` e crio minha branch a partir dela:

```powershell
git status --short
git switch main
git pull --ff-only
git switch -c nome-da-minha-branch
```

Os nomes que combinamos são `fix/carga-banco` (Vinicius), `feat/infra-terraform` (Roberto), `fix/tratamento-seguranca` (Guilherme) e `docs/entrega-fase3` (Maria Fernanda). As duas primeiras e a de documentos já entraram na `main`. Para o que falta (dashboard, conversão dos números), cada um cria uma branch nova a partir da `main` atualizada.

Cada um configura o próprio nome e e-mail no seu clone, o mesmo e-mail da conta do GitHub:

```powershell
git config user.name "Meu nome"
git config user.email "meu-email@exemplo.com"
```

Isso vale para os commits novos. Os antigos continuam como estão.

## Commits

Eu faço um commit quando termino uma mudança que faz sentido sozinha, e não um por linha alterada nem só para aumentar a conta. Por exemplo: corrigir a conversão dos números e incluir o teste que prova a correção vão juntos no mesmo commit. Já o guia do Terraform vai em outro commit, separado da configuração.

Antes de adicionar qualquer coisa eu olho o que mudou:

```powershell
git status --short
git diff
git diff --check
```

Arquivos novos não aparecem no `git diff`, então abro e leio eles também. Eu adiciono só os arquivos da minha mudança, nunca com `git add .`. Exemplo da tarefa de conversão dos números:

```powershell
git add etl/tratar.py tests/test_tratamento.py
git diff --cached
git diff --cached --check
git commit -m "fix: separa conversao dos numeros do scr e sgs"
```

## Mandando para revisão

Quando minha parte está pronta, eu envio a branch:

```powershell
git push -u origin nome-da-minha-branch
```

Depois abro um Pull Request para a `main` no GitHub e peço a revisão da pessoa combinada. Nunca envio direto para a `main`. No PR eu escrevo, de forma curta:

- o que mudei e por quê;
- como testei e qual foi o resultado;
- o que ainda falta ou depende de outra pessoa.

Quem revisa olha o diff, roda os comandos ou testes e confere se a documentação bate com o que foi feito. Se faltar alguma verificação, quem fez deixa isso escrito no PR. Só juntamos depois da revisão.

## Para não darmos dor de cabeça uns aos outros

- O Vinicius mexe na carga (`etl/carregar.py`), o Guilherme no tratamento (`etl/tratar.py`), o Roberto no Terraform e a Maria Fernanda nos documentos e no README. Se alguém precisar mexer no arquivo do outro, avisa antes no grupo.
- Só uma pessoa mexe no estado do Terraform por vez. Os outros só revisam os arquivos.
- Nunca vai para o Git: senha, token, string de conexão de verdade, `.env`, estado ou plano do Terraform. Isso vale também para prints e mensagens de erro que a gente cola em PR e no grupo.
- Não mudamos o período dos dados no meio da conferência sem atualizar junto a lista de fontes e os resultados.
- A pasta `docs/` vai para o Git, menos `docs/interno/` (planos e resumos do grupo) e `docs/entrega/` (os documentos que mandamos para a professora). Essas duas ficam só na nossa máquina e o `.gitignore` já cuida disso.
- Antes de salvar uma evidência nova em `docs/evidencias/`, confiro se não tem `postgres://`, senha ou token no texto.
- Cada um precisa conseguir explicar a parte que fez. Uma tarefa só está pronta quando o resultado foi conferido, e não só porque existe um arquivo com o nome certo.
