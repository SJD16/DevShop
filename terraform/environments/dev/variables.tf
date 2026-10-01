variable "aws_region" {
  description = "AWS region for the DevShop environment"
  type        = string
  default     = "us-east-1"
}
variable "devshop_jwt_secret_key" {
  type      = string
  sensitive = true
}

variable "devshop_db_password" {
  type      = string
  sensitive = true
}
