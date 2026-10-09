output "resource_group_name" {
  description = "AKS resource group"
  value       = azurerm_resource_group.devshop.name
}

output "vnet_name" {
  description = "AKS VNet"
  value       = azurerm_virtual_network.devshop.name
}

output "vnet_address_space" {
  description = "AKS VNet address space"
  value       = azurerm_virtual_network.devshop.address_space
}

output "aks_subnet_name" {
  description = "AKS subnet"
  value       = azurerm_subnet.aks.name
}

output "aks_subnet_address_prefixes" {
  description = "AKS subnet address prefixes"
  value       = azurerm_subnet.aks.address_prefixes
}

output "aks_cluster_name" {
  description = "AKS cluster name"
  value       = module.aks.cluster_name
}

output "aks_cluster_id" {
  description = "AKS cluster ID"
  value       = module.aks.cluster_id
}

output "aks_cluster_fqdn" {
  description = "AKS API server FQDN"
  value       = module.aks.cluster_fqdn
}

output "aks_node_resource_group" {
  description = "AKS-managed node resource group"
  value       = module.aks.node_resource_group
}
