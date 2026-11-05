# Como a gente trabalha no projeto

Somos em quatro no grupo: Vinicius, Roberto, Guilherme e Maria Fernanda. Combinamos que cada um pega uma parte, faz na sua própria branch, testa e só junta depois que outra pessoa revisou. Assim ninguém sobrescreve o trabalho do outro e a gente consegue explicar tudo na apresentação.

A divisão das tarefas da fase 3 está no PDF que o Vinicius mandou. Quem ainda não recebeu pede pra ele. A pasta `docs/` do repositório fica vazia por enquanto, então os documentos de apoio não vêm junto com o clone.

## Preparando o ambiente

Depois de clonar, eu abro o PowerShell na pasta do projeto e rodo:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Depois uso o Python desse ambiente (`.\.venv\Scripts\python.exe`) para rodar os scripts. Os CSVs finais, os JSONs da SGS e as amostras já estão no Git. Os ZIPs e o CSV filtrado do SCR não estão, porque são muito grandes. Mesmo sem eles dá para estudar o código e escrever testes usando as amostras.

**Não rodar o `etl/carregar.py` no banco do grupo por enquanto.** A versão atual roda o `DROP TABLE ... CASCADE` do `sql/schema.sql` e apaga as quatro tabelas antes de carregar. A correção disso é a parte do Vinicius. Enquanto isso, para olhar o que tem no banco, a gente usa só o `etl/verificar_banco.py`, que apenas lê.

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

Os nomes que combinamos são `fix/carga-banco` (Vinicius), `feat/infra-terraform` (Roberto), `fix/tratamento-seguranca` (Guilherme) e `docs/entrega-fase3` (Maria Fernanda). Se eu tiver mudanças soltas, resolvo isso antes de trocar de branch. Se o `git pull` falhar, eu não forço nada: pergunto no grupo o que aconteceu. Se a branch já existe no meu computador, só volto para ela com `git switch nome-da-branch`.

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

Não colocamos "Co-authored-by" nas mensagens. Cada commit fica no nome de quem fez.

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
- O conteúdo da pasta `docs/` e os arquivos de apoio de cada um ficam só na nossa máquina e não vão para o Git.
- Cada um precisa conseguir explicar a parte que fez. Uma tarefa só está pronta quando o resultado foi conferido, e não só porque existe um arquivo com o nome certo.
