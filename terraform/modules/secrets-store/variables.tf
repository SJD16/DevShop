variable "namespace" {
  description = "Kubernetes namespace for the Secrets Store CSI Driver"
  type        = string
  default     = "kube-system"
}
