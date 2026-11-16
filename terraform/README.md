# Terraform do projeto

Aqui está o serviço PostgreSQL da Aiven descrito como código. O serviço já existia, então o Terraform só passa a conhecer ele (bloco `import` no `main.tf`) e não cria nada novo.

## O que precisa ter

- Terraform 1.6 ou mais novo (`terraform version`);
- um token da Aiven (painel da Aiven, em perfil e tokens);
- o nome do projeto e o nome do serviço, que aparecem no painel.

## Passo a passo

Tudo dentro da pasta `terraform/`. No PowerShell:

```powershell
# 1. o token fica so nessa janela do terminal, nunca em arquivo
$env:AIVEN_API_TOKEN = "COLE_O_TOKEN_AQUI"

# 2. copia o modelo e troca pelos valores reais (esse arquivo nao vai pro git)
Copy-Item terraform.tfvars.example terraform.tfvars
notepad terraform.tfvars

# 3. baixa o provider da aiven
terraform init

# 4. mostra o que vai acontecer, sem mudar nada
terraform plan
```

## O que esperar no plan

Como o serviço já existe, o resultado certo é aparecer `1 to import` e nenhuma criação. Se aparecer `1 to add`, tem algo errado no nome do projeto ou do serviço, e não é para aplicar.

Se o plan mostrar `to change` em algum campo, confira se o valor do `terraform.tfvars` bate com o que está no painel, antes de aplicar qualquer coisa.

Só depois de ler o plan, e com o grupo de acordo:

```powershell
terraform apply
```

O recurso tem `termination_protection` e `prevent_destroy`, então não dá para apagar o banco por engano com um `terraform destroy`.

## O que não vai para o Git

`terraform.tfvars`, `terraform.tfstate` e a pasta `.terraform/` ficam só na máquina de quem rodou (o `.gitignore` já bloqueia). Mais detalhes em [../docs/SEGURANCA.md](../docs/SEGURANCA.md).

## Arquivos

| Arquivo | O que tem |
|---|---|
| `main.tf` | versão do Terraform, provider, import e o recurso `aiven_pg` |
| `variables.tf` | projeto, nome do serviço e versão do PostgreSQL |
| `outputs.tf` | host, porta e nome do banco (sem usuário nem senha) |
| `terraform.tfvars.example` | modelo dos valores |
| `.terraform.lock.hcl` | trava a versão do provider |
