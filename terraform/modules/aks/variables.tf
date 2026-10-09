variable "cluster_name" {
  description = "Name of the AKS cluster"
  type        = string
}

variable "location" {
  description = "Azure region where AKS will be created"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group containing the AKS cluster"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID for the AKS nodes"
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes version for AKS"
  type        = string
  default     = null
}

variable "node_vm_size" {
  description = "VM size for the AKS system node pool"
  type        = string
  default     = "Standard_D2as_v4"
}

variable "node_count" {
  description = "Initial number of AKS system nodes"
  type        = number
  default     = 1
}

variable "tags" {
  description = "Tags applied to AKS resources"
  type        = map(string)
  default     = {}
}
