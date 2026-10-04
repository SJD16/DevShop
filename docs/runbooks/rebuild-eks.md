# Rebuild the DevShop EKS Environment

This runbook follows the current Terraform module structure in `terraform/environments/dev/`. It is for the disposable AWS demonstration environment. It does not use the older `eksctl` recipe in `aws/eks/cluster.yaml`.

## Prerequisites

- AWS CLI authenticated to the intended account, Terraform `>= 1.6.0`, Git, and `kubectl`.
- Permissions for the resources declared in the environment and its modules.
- Network access to AWS, Terraform provider registries, Helm repositories, GitHub, and Docker Hub.
- Fresh sensitive input values for `devshop_jwt_secret_key` and `devshop_db_password`. Supply them outside Git, such as through `TF_VAR_devshop_jwt_secret_key` and `TF_VAR_devshop_db_password`, or a local untracked tfvars file. Do not echo or commit them.
- Verify the current AWS region, account, EKS version support, and Jenkins AMI suitability before creating resources. The repository currently declares region default `us-east-1`, cluster version `1.36`, and a fixed AMI ID; these are configuration, not guaranteed current account values.

## Terraform working directory

From the repository root:

```sh
cd terraform/environments/dev
export AWS_REGION="${AWS_REGION:-us-east-1}"
export TF_VAR_aws_region="$AWS_REGION"
aws sts get-caller-identity
```

The Terraform default is `us-east-1`; if using another region, set `AWS_REGION` first so the AWS CLI and Terraform target the same region. Use the intended AWS profile explicitly when needed. Confirm this is the correct account and region before continuing.

## Validation

```sh
terraform fmt -check -recursive ../..
terraform init
terraform validate
```

The environment root composes the VPC, EKS, Jenkins, Argo CD, and Secrets Store modules. Review `main.tf`, provider configuration, variables, and current module code if any of these files have changed since the last run.

## Terraform plan

```sh
terraform plan
```

Ensure the required secret inputs are available in your shell or local tfvars file before planning. Review the full plan for the target account, region, cluster version, node group, Jenkins host, IAM/Pod Identity, Secrets Manager, and Helm resources. Stop if Terraform proposes unexpected replacement or deletion. Do not copy old resource IDs from previous runs into this runbook.

## Terraform apply

After reviewing the plan and confirming the target, apply the reviewed configuration:

```sh
terraform apply
```

Terraform creates or updates the AWS network and EKS resources, managed node group, IAM roles and associations, Secrets Manager secret/version, Jenkins EC2 resources, and the Argo CD and Secrets Store Helm releases as defined by the environment. The `depends_on` relationships ensure the EKS cluster precedes the platform add-ons. Terraform is responsible for those declared resources; Kubernetes-created AWS resources may have separate lifecycles.

## Kubeconfig configuration

Read the cluster name from Terraform output and use the same region configured for this run:

```sh
export CLUSTER_NAME="$(terraform output -raw eks_cluster_name)"
aws eks update-kubeconfig --name "$CLUSTER_NAME" --region "$AWS_REGION"
kubectl config current-context
```

Do not reuse a context from a previous cluster without checking it.

## Node verification

```sh
kubectl get nodes -o wide
kubectl get nodes -L workload
```

Confirm nodes are `Ready` and the managed node group is present. Instance addresses and IDs change across rebuilds; discover them from the current cluster rather than copying old values.

## System component verification

Check the Pod Identity Agent and EBS CSI add-on:

```sh
kubectl get pods -n kube-system
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --addon-name eks-pod-identity-agent --region "$AWS_REGION"
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --addon-name aws-ebs-csi-driver --region "$AWS_REGION"
aws eks list-pod-identity-associations --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
```

Confirm the CSI controller and node pods are ready and that the EBS association references `kube-system/ebs-csi-controller-sa`. Confirm the application association references `devshop/devshop` after Terraform creates it.

Check the platform Helm releases and Argo CD:

```sh
helm list -A
kubectl get pods -n argocd
kubectl get svc -n argocd
kubectl get pods -n kube-system
```

The Argo CD server Service is configured as `LoadBalancer`; any assigned hostname/IP is dynamic. Obtain it from the current Service output. The FastAPI application uses NodePort and is a separate Service.

## Kubernetes application verification

Argo CD owns the application synchronization from the Git repository. Check the Application and resources:

```sh
kubectl get applications -n argocd
kubectl get pods,svc,pvc,statefulset,deployments,jobs -n devshop
kubectl get events -n devshop --sort-by=.lastTimestamp
kubectl kustomize k8s/overlays/aws
```

Confirm the PostgreSQL StatefulSet is ready and its PVC is bound. The PVC should use `devshop-gp3`; the current overlay requests 5 GiB and the StorageClass reclaim policy is `Delete`.

Confirm the migration Job completed and the DevShop Deployment is ready. If the SecretProviderClass or synced Secret is not present, inspect pod events and the Secrets Store CSI provider/controller before retrying. Do not print Secret contents while troubleshooting.

The application Service is a NodePort. Discover its assigned port each time:

```sh
kubectl get svc devshop -n devshop -o wide
kubectl get svc devshop -n devshop -o jsonpath='{.spec.ports[0].nodePort}{"\n"}'
```

If testing external access, also obtain the current node addresses and security groups from `kubectl get nodes -o wide` and the AWS EC2 APIs. Any client public IP and security-group IDs are ephemeral. The AWS overlay does not declare an application load balancer or ingress. Follow the [PostgreSQL pod recreation test](../tests/persistence/postgres-pod-recreation.md) for storage verification.

## Important dependencies

1. The VPC and EKS cluster must exist before cluster-level providers and Helm releases work.
2. The Pod Identity Agent precedes EBS CSI and application identity associations.
3. The EBS CSI controller needs its own Pod Identity permissions to provision and attach volumes.
4. The Secrets Store CSI Driver and AWS provider must be working before workload pods can mount the SecretProviderClass and synchronize the Kubernetes Secret.
5. PostgreSQL must be reachable before the migration Job can complete; the Job waits for TCP availability before running Alembic.
6. Argo CD reads the Git revision and reconciles manifests; Jenkins changes the image tag in Git and does not directly deploy the application.

## Cleanup considerations

Before any teardown, inspect the current Terraform plan/state and the Kubernetes resources that create AWS resources. PostgreSQL's StorageClass uses `reclaimPolicy: Delete`, so removing the PVC can delete its EBS volume. Argo CD's `LoadBalancer` Service can create an AWS NLB and related network interfaces that may outlive EKS teardown if Kubernetes cannot clean them up. The [destruction problem diagram](../../Diagrams/AWS/Destruction_problem.md) records this dependency lesson. Decide how database data and externally managed resources should be handled before cleanup; do not assume that cluster deletion preserves them.
