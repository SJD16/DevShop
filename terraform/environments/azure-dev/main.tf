resource "azurerm_resource_group" "devshop" {
  name     = "rg-devshop-azure-dev"
  location = "East US"
}

resource "azurerm_virtual_network" "devshop" {
  name                = "vnet-devshop-azure-dev"
  location            = azurerm_resource_group.devshop.location
  resource_group_name = azurerm_resource_group.devshop.name
  address_space       = ["10.20.0.0/16"]
}

resource "azurerm_subnet" "devshop" {
  name                 = "snet-devshop"
  resource_group_name  = azurerm_resource_group.devshop.name
  virtual_network_name = azurerm_virtual_network.devshop.name
  address_prefixes     = ["10.20.1.0/24"]
}

resource "azurerm_network_security_group" "devshop" {
  name                = "nsg-devshop-azure-dev"
  location            = azurerm_resource_group.devshop.location
  resource_group_name = azurerm_resource_group.devshop.name
}

resource "azurerm_subnet_network_security_group_association" "devshop" {
  subnet_id                 = azurerm_subnet.devshop.id
  network_security_group_id = azurerm_network_security_group.devshop.id
}

resource "azurerm_network_security_rule" "allow_ssh" {
  name                       = "AllowSSH"
  priority                   = 100
  direction                  = "Inbound"
  access                     = "Allow"
  protocol                   = "Tcp"
  source_port_range          = "*"
  destination_port_range     = "22"
  source_address_prefix      = "*"
  destination_address_prefix = "*"

  resource_group_name         = azurerm_resource_group.devshop.name
  network_security_group_name = azurerm_network_security_group.devshop.name
}

resource "azurerm_network_security_rule" "allow_devshop" {
  name                       = "AllowDevShop"
  priority                   = 110
  direction                  = "Inbound"
  access                     = "Allow"
  protocol                   = "Tcp"
  source_port_range          = "*"
  destination_port_range     = "8000"
  source_address_prefix      = "*"
  destination_address_prefix = "*"

  resource_group_name         = azurerm_resource_group.devshop.name
  network_security_group_name = azurerm_network_security_group.devshop.name
}

resource "azurerm_public_ip" "devshop" {
  name                = "pip-devshop-azure-dev"
  location            = azurerm_resource_group.devshop.location
  resource_group_name = azurerm_resource_group.devshop.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_network_interface" "devshop" {
  name                = "nic-devshop-azure-dev"
  location            = azurerm_resource_group.devshop.location
  resource_group_name = azurerm_resource_group.devshop.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.devshop.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.devshop.id
  }
}

resource "azurerm_linux_virtual_machine" "devshop" {
  name                = "vm-devshop-azure-dev"
  resource_group_name = azurerm_resource_group.devshop.name
  location            = azurerm_resource_group.devshop.location
  size                = "Standard_D2as_v4"
  admin_username      = "azureuser"

  network_interface_ids = [
    azurerm_network_interface.devshop.id
  ]

  disable_password_authentication = true

  admin_ssh_key {
    username   = "azureuser"
    public_key = file("~/.ssh/id_ed25519.pub")
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  identity {
    type = "SystemAssigned"
  }
  custom_data = filebase64("${path.module}/../../../azure/vm/user-data.sh")

}
