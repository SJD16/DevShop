resource "azurerm_resource_group" "devshop" {
  name     = "rg-devshop-aks-dev"
  location = var.location

  tags = {
    Project     = "DevShop"
    Environment = "dev"
    ManagedBy   = "Terraform"
  }
}

resource "azurerm_virtual_network" "devshop" {
  name                = "vnet-devshop-aks-dev"
  location            = azurerm_resource_group.devshop.location
  resource_group_name = azurerm_resource_group.devshop.name

  address_space = [
    "10.30.0.0/16"
  ]

  tags = {
    Project     = "DevShop"
    Environment = "dev"
    ManagedBy   = "Terraform"
  }
}

resource "azurerm_subnet" "aks" {
  name                 = "snet-aks"
  resource_group_name  = azurerm_resource_group.devshop.name
  virtual_network_name = azurerm_virtual_network.devshop.name

  address_prefixes = [
    "10.30.1.0/24"
  ]
}

module "aks" {
  source = "../../modules/aks"

  cluster_name        = var.cluster_name
  location            = azurerm_resource_group.devshop.location
  resource_group_name = azurerm_resource_group.devshop.name
  subnet_id           = azurerm_subnet.aks.id

  node_vm_size = "Standard_D2as_v4"
  node_count   = 1

  tags = {
    Project     = "DevShop"
    Environment = "dev"
    ManagedBy   = "Terraform"
  }

  depends_on = [
    azurerm_subnet.aks
  ]
}

module "argocd" {
  source = "../../modules/argocd-azure"

  namespace     = "argocd"
  release_name  = "argocd"
  chart_version = "9.1.0"

  depends_on = [
    module.aks
  ]
}