variable "aiven_project_name" {
  description = "Existing Aiven project name."
  type        = string
  nullable    = false
}

variable "service_name" {
  description = "Existing PostgreSQL service name."
  type        = string
  nullable    = false
}

variable "postgresql_version" {
  description = "Existing PostgreSQL major version."
  type        = string
  nullable    = false
}
