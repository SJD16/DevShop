# AWS Deployment

## 1. Overview

This page describes the AWS EKS demonstration deployment represented by the current repository. Terraform provisions the AWS foundation, EKS add-ons, Jenkins, Argo CD, and Secrets Store CSI components. Argo CD then reconciles the application from `k8s/overlays/aws`. This is a functional learning environment, not production infrastructure.

The [Terraform infrastructure diagram](../../Diagrams/AWS/Terraform_infrastructure.md), [CI/CD + GitOps diagram](../../Diagrams/AWS/CD_+_GitOps_flow.md), and [traffic-focused diagram](../../Diagrams/AWS/Networking_traffic_focused.md) provide visual references.

## 2. Prerequisites

- AWS CLI authenticated to an account with permissions for the resources in `terraform/modules/`.
- Terraform `>= 1.6.0`, AWS CLI, and Git.
- Network access to AWS APIs, Terraform providers, Helm chart repositories, GitHub, and Docker Hub.
- Terraform input values for `devshop_jwt_secret_key` and `devshop_db_password`. Supply fresh values through a secure local mechanism such as environment variables or an untracked tfvars file. Never put secret values in Git or this document.
- For cluster operations after provisioning: `kubectl`; `helm` is used by Terraform through the Helm provider.

Confirm the AWS identity and region before any infrastructure operation. The checked-in default region is `us-east-1`; use the value configured for the intended environment.

## 3. Terraform Infrastructure

The working directory is `terraform/environments/dev/`. It is the environment root and composes the implementations under `terraform/modules/`:

```text
terraform/environments/dev/  → module wiring, provider setup, environment inputs, outputs
terraform/modules/           → component infrastructure implementation
```

The current environment calls the `vpc`, `eks`, `jenkins`, `argocd`, and `secrets-store` modules. The modules are project-specific; their current code is the source of truth for the resources they create.

Run the standard checks and review the plan before applying:

```sh
cd terraform/environments/dev
terraform fmt -check -recursive ../..
terraform init
terraform validate
terraform plan
```

Pass the required sensitive variables using your approved local secret mechanism, for example `TF_VAR_devshop_jwt_secret_key` and `TF_VAR_devshop_db_password` in the shell environment, or an untracked `*.tfvars` file. Do not display those values in terminal captures. Inspect the plan and confirm the AWS account/region before proceeding with `terraform apply`.

### VPC

The VPC module creates a VPC, Internet Gateway, two public subnets, two private subnets, route tables, and subnet associations. Only the public route table is connected to the Internet Gateway; there is no NAT gateway or private egress route in the module. The environment passes the public subnet IDs to EKS and Jenkins.

### EKS

The EKS module creates the cluster IAM role and EKS control plane. The environment currently sets the cluster name to `devshop-eks` and configures Kubernetes version `1.36`. Treat these as checked-in settings; verify supported versions and current AWS state before provisioning.

### Node Group

The managed node group uses `t3.medium` instances, a 20 GiB node disk, and size settings of desired 2, minimum 2, maximum 3. These nodes are placed in the environment's public subnet IDs. They are not live-instance guarantees.

### IAM / Pod Identity

The EKS module creates the Pod Identity Agent add-on, a dedicated EBS CSI role and association for `kube-system/ebs-csi-controller-sa`, and an application role associated with `devshop/devshop`. The latter role can read the configured Secrets Manager secret.

### EBS CSI

The EKS module declares the AWS EBS CSI add-on with its dedicated Pod Identity association and `AmazonEBSCSIDriverPolicy`. The AWS Kustomize overlay uses the EBS CSI provisioner for PostgreSQL's gp3 volume. Confirm the add-on and controller are healthy before relying on dynamically provisioned storage.

## 4. Kubernetes Platform

The Terraform root also installs the following Helm releases after the EKS module is available. Review the plan to see precisely what Terraform will manage in the target account and cluster.

### Kustomize

Shared resources are under `k8s/base/`. The AWS overlay at `k8s/overlays/aws/` adds the gp3 StorageClass, patches the PostgreSQL PVC, and pins the image tag. Render it before deployment with:

```sh
kubectl kustomize k8s/overlays/aws
```

### Argo CD

Terraform installs the Argo CD Helm chart in namespace `argocd`; its server Service is configured as `LoadBalancer` with an NLB annotation. The Git-managed Application in `k8s/argocd/devshop-application.yaml` watches `master` at `k8s/overlays/aws`, targets namespace `devshop`, and enables automated sync, prune, and self-heal.

### Secrets Store CSI

Terraform installs the Secrets Store CSI Driver with secret synchronization enabled and the AWS provider. `k8s/base/devshop-secretproviderclass.yaml` selects the `devshop/devshop` Secrets Manager object and maps its fields into `devshop-secret`. A Pod Identity association supplies AWS access for the workload service account. Do not copy secret values into Kubernetes manifests or logs.

## 5. Application Deployment

Once Terraform has provisioned the cluster and add-ons, use the current cluster name and AWS region to configure local kubeconfig. The application deployment is owned by Argo CD through GitOps.

### PostgreSQL

PostgreSQL is a single-replica StatefulSet (`devshop-postgres`) in namespace `devshop`, with a headless Service. The AWS overlay selects the gp3 StorageClass. The current configuration is for a demonstration workload.

### Persistent Storage

The AWS StorageClass is `devshop-gp3`, provisioned by `ebs.csi.aws.com`, with `WaitForFirstConsumer`, expansion enabled, and `reclaimPolicy: Delete`. The PVC requests 5 GiB. The reclaim policy means removing storage resources can delete the EBS volume; the recorded test covers pod recreation only.

### Migration Job

The `devshop-migration` Job runs as an Argo CD sync hook. It waits for the PostgreSQL service to accept TCP connections, then runs `alembic upgrade head` using `DATABASE_URL` from the synced Kubernetes Secret.

### DevShop

The FastAPI Deployment uses the image selected by `k8s/overlays/aws/kustomization.yaml`; Jenkins updates that tag to the build's short Git SHA. The Service is `NodePort`, not a LoadBalancer or Ingress. Obtain the current assigned NodePort and current node/security-group details from Kubernetes and AWS when needed; do not rely on historical values in old notes.

## 6. CI/CD

### Jenkins

The Terraform Jenkins module provisions an EC2 host and bootstrap script. Its security group currently permits TCP 8080 from `0.0.0.0/0`, so restrict access before any broader or persistent use. Jenkins credentials are expected for Docker Hub and GitHub push access; the repository does not contain their values.

### Docker

The Jenkinsfile creates a local image tagged from the short source commit SHA, runs the container against its CI PostgreSQL container, and checks the root endpoint. The Dockerfile installs `requirements.txt`, copies the application and Alembic files, and runs Uvicorn on port 8000.

### Docker Hub

The pipeline logs in using Jenkins credentials and pushes the image to Docker Hub. The current repository names `sjd16/devshop` in its Kustomize overlay and validation stage. Verify the actual credential account and repository agree before running the pipeline; Jenkins currently tags/pushes using the credential username but the Kustomize validation expects the checked-in `sjd16/devshop` name.

### GitOps commit

Jenkins changes only the AWS overlay image tag, renders the Kustomize output, commits that image update, checks that `origin/master` still matches the build's source commit, and pushes the GitOps commit. Argo CD detects the Git update and applies the resources. Jenkins does not directly deploy application manifests with `kubectl apply`.

## 7. Verification

After Terraform and kubeconfig are current, verify components using fresh cluster values:

```sh
kubectl get nodes -o wide
kubectl get pods -n kube-system
kubectl get pods,svc,pvc,statefulset,deployments,jobs -n devshop
kubectl get applications -n argocd
kubectl kustomize k8s/overlays/aws
```

For database persistence, follow the [PostgreSQL pod recreation test](../tests/persistence/postgres-pod-recreation.md). The repository's incident record reports a passing pod deletion/recreation check with the PVC still bound and existing records present. This is a recorded result; this documentation update did not connect to a live AWS cluster to repeat it.

## 8. Known Limitations

- This is a functional demonstration baseline, not production-ready infrastructure.
- PostgreSQL runs in EKS as one replica on one EBS-backed volume; backup/restore, high availability, and destructive volume lifecycle are not verified.
- EBS StorageClass reclaim policy is `Delete`.
- The FastAPI Service is exposed through NodePort. Historical node, NodePort, public-IP, or security-group values can change.
- The Jenkins security group allows public access to TCP 8080 in the checked-in module.
- The Terraform VPC creates private subnets without NAT/egress routing, while current EKS and Jenkins configuration uses public subnets.
- The repository contains an OWASP ZAP procedure and Trivy pipeline stage. Its Jenkinsfile does not currently run OWASP Dependency-Check.
- Terraform state and plans are ignored locally by `.gitignore`; do not commit them or treat local generated copies as shared state.

## 9. Cleanup

Before any environment teardown, inspect current Terraform state and the planned changes, and identify AWS resources whose lifecycle is not fully represented by the Terraform graph. In particular, review EBS volumes/PVC reclaim behavior and load balancers created by Kubernetes. The repository's [destruction lesson](../../Diagrams/AWS/Destruction_problem.md) describes why external Kubernetes-created resources can outlive EKS teardown. Do not assume a PVC or cluster deletion preserves database data. No cleanup action is performed by this guide.
