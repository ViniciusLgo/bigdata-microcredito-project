variable "aiven_project_name" {
  description = "Nome do projeto na Aiven onde o servico vai ser criado."
  type        = string
  nullable    = false
}

variable "service_name" {
  description = "Nome que o servico PostgreSQL vai ter."
  type        = string
  nullable    = false
}

variable "postgresql_version" {
  description = "Versao principal do PostgreSQL."
  type        = string
  nullable    = false
}

variable "cloud_name" {
  description = "Regiao da nuvem (ex.: a que aparece no painel da Aiven). Se ficar vazio, a Aiven escolhe."
  type        = string
  default     = null
}

variable "proteger_contra_apagar" {
  description = "Liga a protecao da Aiven contra apagar o servico por engano."
  type        = bool
  default     = true
}
