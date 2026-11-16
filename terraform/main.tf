terraform {
  # precisa do 1.6 ou mais por causa do bloco import abaixo
  required_version = ">= 1.6.0, < 2.0.0"

  required_providers {
    aiven = {
      source  = "aiven/aiven"
      version = "= 4.65.1"
    }
  }
}

provider "aiven" {}

# o servico ja existe na aiven, entao aqui a gente so traz ele pro estado do
# terraform (nao cria nada). sem isso o plan de quem clonar o repo ia propor
# criar um servico novo
import {
  to = aiven_pg.microcredit
  id = "${var.aiven_project_name}/${var.service_name}"
}

resource "aiven_pg" "microcredit" {
  project                = var.aiven_project_name
  service_name           = var.service_name
  plan                   = "free-1-1gb"
  termination_protection = true

  pg_user_config {
    pg_version = var.postgresql_version
  }

  lifecycle {
    prevent_destroy = true
  }
}
