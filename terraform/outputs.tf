output "host" {
  description = "PostgreSQL hostname without credentials."
  value       = aiven_pg.microcredit.service_host
}

output "port" {
  description = "PostgreSQL connection port."
  value       = aiven_pg.microcredit.service_port
}

output "database_name" {
  description = "Default PostgreSQL database name."
  value       = "defaultdb"
}
