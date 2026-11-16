# Terraform do projeto

Aqui o serviço PostgreSQL da Aiven é criado como código. O Terraform cria só o serviço (a infraestrutura). As tabelas e os dados vêm depois, do `sql/schema.sql` e do `etl/carregar.py`.

## O que precisa ter

- Terraform 1.6 ou mais novo (`terraform version`);
- um token da Aiven (painel da Aiven, em perfil e tokens);
- o nome do projeto da Aiven e o nome que o serviço vai ter;
- opcional: a região da nuvem (`cloud_name`). Se ficar vazia, a Aiven escolhe.

## Passo a passo

Tudo dentro da pasta `terraform/`. No PowerShell:

```powershell
# 1. o token fica so nessa janela do terminal, nunca em arquivo
$env:AIVEN_TOKEN = "COLE_O_TOKEN_AQUI"

# 2. copia o modelo e troca pelos valores reais (esse arquivo nao vai pro git)
Copy-Item terraform.tfvars.example terraform.tfvars
notepad terraform.tfvars

# 3. baixa o provider da aiven
terraform init

# 4. mostra o que vai acontecer, sem mudar nada
terraform plan

# 5. cria o servico (pede para digitar yes e leva alguns minutos)
terraform apply
```

No `plan`, o certo é aparecer `Plan: 1 to add, 0 to change, 0 to destroy`. Leia o que vai ser criado antes de digitar `yes`.

Quando o `apply` terminar, o serviço existe mas está vazio. Para pegar a URL de conexão, criar as tabelas e carregar os dados (da raiz do projeto):

```powershell
cd ..
$env:AIVEN_PG_URL = terraform -chdir=terraform output -raw service_uri
python etl/carregar.py --criar-schema
python etl/verificar_banco.py
```

Se o dashboard já estiver publicado, troque a `AIVEN_PG_URL` nos segredos dele pela URL nova.

## Se já existe um serviço gratuito na conta

O plano gratuito da Aiven, pelo que sabemos, permite só um serviço PostgreSQL gratuito por conta. Se o painel já mostra um serviço do projeto, o `apply` pode dar erro. Confira no painel antes. Há dois caminhos:

1. **Trocar o serviço antigo pelo novo.** Os dados não se perdem de verdade, porque todos os CSVs estão no repositório e a carga recria tudo. No painel da Aiven, desligue a proteção contra apagar do serviço antigo e apague ele. Depois siga o passo a passo acima e recarregue os dados.
2. **Manter o serviço antigo e só trazer ele para o Terraform.** No lugar do `apply`, rode `terraform import aiven_pg.microcredit PROJETO/SERVICO` com o nome do projeto e do serviço reais, e depois `terraform plan`. O certo é aparecer nenhuma mudança. Nesse caso o serviço não foi criado pelo Terraform, só passou a ser descrito por ele.

## Cuidados

- O recurso tem `termination_protection` e `prevent_destroy`, então não dá para apagar o banco por engano com um `terraform destroy`. Para apagar de propósito, tire o `prevent_destroy` do `main.tf` primeiro.
- A saída `service_uri` tem usuário e senha. Ela fica escondida na tela (`sensitive`), mas a senha entra no `terraform.tfstate`. Por isso `terraform.tfvars`, `terraform.tfstate` e a pasta `.terraform/` ficam só na máquina de quem rodou, e o `.gitignore` já bloqueia. Mais detalhes em [../docs/SEGURANCA.md](../docs/SEGURANCA.md).
- Só uma pessoa roda o `apply` por vez, porque o estado fica no computador dela.

## Arquivos

| Arquivo | O que tem |
|---|---|
| `main.tf` | versão do Terraform, provider e o recurso `aiven_pg` que cria o serviço |
| `variables.tf` | projeto, nome do serviço, versão do PostgreSQL, região e a proteção contra apagar |
| `outputs.tf` | host, porta, nome do banco e a URL de conexão (escondida) |
| `terraform.tfvars.example` | modelo dos valores |
| `.terraform.lock.hcl` | trava a versão do provider |
