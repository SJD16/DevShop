output "namespace" {
  description = "Kubernetes namespace containing Argo CD"
  value       = helm_release.argocd.namespace
}

output "release_name" {
  description = "Argo CD Helm release name"
  value       = helm_release.argocd.name
}

output "chart_version" {
  description = "Installed Argo CD Helm chart version"
  value       = helm_release.argocd.version
}
