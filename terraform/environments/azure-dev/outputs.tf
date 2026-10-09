output "resource_group_name" {
  value = azurerm_resource_group.devshop.name
}

output "vnet_name" {
  value = azurerm_virtual_network.devshop.name
}

output "vnet_address_space" {
  value = azurerm_virtual_network.devshop.address_space
}

output "subnet_name" {
  value = azurerm_subnet.devshop.name
}

output "subnet_address_prefixes" {
  value = azurerm_subnet.devshop.address_prefixes
}

output "network_security_group_name" {
  value = azurerm_network_security_group.devshop.name
}

output "vm_name" {
  value = azurerm_linux_virtual_machine.devshop.name
}

output "vm_private_ip" {
  value = azurerm_network_interface.devshop.private_ip_address
}

output "vm_public_ip" {
  value = azurerm_public_ip.devshop.ip_address
}
