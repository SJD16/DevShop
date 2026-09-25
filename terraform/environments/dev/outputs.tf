output "vpc_id" {
  description = "DevShop VPC ID"
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "DevShop public subnet IDs"
  value       = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = module.vpc.private_subnet_ids
}

output "eks_cluster_name" {
  description = "DevShop EKS cluster name"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "DevShop EKS cluster API endpoint"
  value       = module.eks.cluster_endpoint
}

output "eks_node_group_name" {
  description = "DevShop EKS managed node group name"
  value       = module.eks.node_group_name
}
