# Segurança das informações

Aqui explicamos como o grupo cuida das senhas e dos dados do projeto. A regra é uma só: nenhuma senha, token ou URL de conexão pode ir para o repositório, que é público.

## O que é segredo e onde fica

| Segredo | Para que serve | Onde fica |
|---|---|---|
| `AIVEN_PG_URL` | conexão com o banco (traz usuário e senha) | variável de ambiente no terminal de quem vai rodar |
| Token da Aiven | o Terraform usar a conta da Aiven | variável de ambiente `AIVEN_API_TOKEN`, também só no terminal |
| `terraform.tfvars` | nome do projeto e do serviço na Aiven | arquivo local, ignorado pelo Git |
| `terraform.tfstate` | estado do Terraform, que pode guardar dados do serviço | arquivo local, ignorado pelo Git |

No repositório entra só o `terraform.tfvars.example`, com valores de exemplo, para quem clonar saber o formato.

No PowerShell, a variável vale só para aquela janela e some quando ela fecha:

```powershell
$env:AIVEN_PG_URL = "postgres://USUARIO:SENHA@HOST:PORTA/defaultdb?sslmode=require"
```

## O que o `.gitignore` bloqueia

- `.env` e variações, menos o `.env.example`;
- `*.tfstate`, `*.tfvars` e `*.tfplan`, menos o `*.tfvars.example`;
- a pasta `.terraform/` e os logs do Terraform;
- os ZIPs e o CSV filtrado do SCR, que são grandes demais (não é segurança, mas evita erro);
- a pasta `docs/interno/`, com os papéis de organização do grupo.

O `.terraform.lock.hcl` pode ir para o Git, porque só trava a versão do provider e não tem segredo.

## Cuidados no Terraform

- O `outputs.tf` mostra só host, porta e nome do banco. Usuário e senha não saem em nenhum output.
- O recurso do banco tem `termination_protection` e `prevent_destroy`, então um `terraform destroy` por engano é bloqueado.
- O Terraform só descreve o serviço que já existia na Aiven. Ele não cria um banco novo nem mexe nos dados.

## Cuidados com o banco

- A conexão usa `sslmode=require`.
- A carga nunca apaga tabelas sozinha. Só a flag `--limpar` faz isso, e ela pede para digitar APAGAR.
- Os testes só rodam se a URL apontar para `localhost`, então não encostam no banco da Aiven.

## Cuidados com as evidências

Os arquivos em `docs/evidencias/` mostram contagens e estruturas, nunca a URL de conexão, o usuário ou a senha. Antes de salvar uma saída nova, conferir se não aparece `postgres://`, `password` ou `token`.

## LGPD

Os dados são abertos e já vêm agregados pelo Banco Central e pelo IBGE. Não há nome, CPF, endereço ou qualquer dado que identifique uma pessoa. O menor nível dos nossos dados é a soma por UF, tipo de cliente, modalidade e mês, então não existe como reidentificar alguém. Como não temos dados sensíveis individuais, não foi preciso anonimizar nada.

## Se uma senha vazar

1. Trocar a senha ou o token no painel da Aiven na hora.
2. Avisar o grupo.
3. Apagar o segredo do histórico do Git, porque só apagar o arquivo não adianta: ele continua nos commits antigos.
