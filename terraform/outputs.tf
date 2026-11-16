output "host" {
  description = "Hostname do PostgreSQL, sem usuario nem senha."
  value       = aiven_pg.microcredit.service_host
}

output "port" {
  description = "Porta de conexao do PostgreSQL."
  value       = aiven_pg.microcredit.service_port
}

output "database_name" {
  description = "Nome do banco padrao."
  value       = "defaultdb"
}

# essa URL tem usuario e senha. por isso e sensitive: o terraform nao mostra
# na tela, so com o comando terraform output -raw service_uri, no terminal de
# quem vai usar. ela tambem fica no terraform.tfstate, que o .gitignore bloqueia
output "service_uri" {
  description = "URL de conexao completa (com senha). Usar so no terminal local."
  value       = aiven_pg.microcredit.service_uri
  sensitive   = true
}
