output "vpc_id" {
  description = "DevShop VPC ID"
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "DevShop public subnet IDs"
  value       = module.vpc.public_subnet_ids
}
