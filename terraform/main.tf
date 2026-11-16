terraform {
  required_version = ">= 1.6.0, < 2.0.0"

  required_providers {
    aiven = {
      source  = "aiven/aiven"
      version = "= 4.65.1"
    }
  }
}

# o token da aiven vem da variavel de ambiente AIVEN_TOKEN, nunca do codigo
provider "aiven" {}

# o banco do projeto: um postgresql no plano gratis da aiven (1 GB).
# o terraform cria o servico. quem cria as tabelas e carrega os dados depois
# e o python (sql/schema.sql e etl/carregar.py)
resource "aiven_pg" "microcredit" {
  project                = var.aiven_project_name
  service_name           = var.service_name
  plan                   = "free-1-1gb"
  cloud_name             = var.cloud_name
  termination_protection = var.proteger_contra_apagar

  pg_user_config {
    pg_version = var.postgresql_version
  }

  # esse bloco nao aceita variavel. se um dia precisar apagar o servico de
  # proposito, tira essa linha, roda o apply e so depois o destroy
  lifecycle {
    prevent_destroy = true
  }
}
