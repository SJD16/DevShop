resource "helm_release" "secrets_store_csi_driver" {
  name             = "secrets-store-csi-driver"
  namespace        = var.namespace
  create_namespace = false

  repository = "https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts"
  chart      = "secrets-store-csi-driver"
  version    = "1.6.1"

  wait    = true
  timeout = 600

  values = [
    yamlencode({
      syncSecret = {
        enabled = true
      }

      tokenRequests = [
        {
          audience = "sts.amazonaws.com"
        },
        {
          audience = "pods.eks.amazonaws.com"
        }
      ]
    })
  ]
}

resource "helm_release" "secrets_store_csi_driver_provider_aws" {
  name             = "secrets-store-csi-driver-provider-aws"
  namespace        = var.namespace
  create_namespace = false

  repository = "https://aws.github.io/secrets-store-csi-driver-provider-aws"
  chart      = "secrets-store-csi-driver-provider-aws"
  version    = "3.1.4"

  wait    = true
  timeout = 600

  values = [
    yamlencode({
      "secrets-store-csi-driver" = {
        install = false
      }
    })
  ]

  depends_on = [
    helm_release.secrets_store_csi_driver
  ]
}
