terraform {
  required_version = "= 1.17.1"

  required_providers {
    aiven = {
      source  = "aiven/aiven"
      version = "= 4.65.1"
    }
  }
}

provider "aiven" {}

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
