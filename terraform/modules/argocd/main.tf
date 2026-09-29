resource "helm_release" "argocd" {
  name             = var.release_name
  namespace        = var.namespace
  create_namespace = true

  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-cd"
  version    = var.chart_version

  wait          = true
  wait_for_jobs = true
  timeout       = 600

  values = [
    yamlencode({
      server = {
        service = {
          type = "LoadBalancer"

          annotations = {
            "service.beta.kubernetes.io/aws-load-balancer-type" = "nlb"
          }
        }
      }
    })
  ]
}
