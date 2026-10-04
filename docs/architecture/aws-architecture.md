# AWS Architecture

DevShop uses a small FastAPI/PostgreSQL service as a reference workload for a hands-on DevOps/DevSecOps environment. The AWS implementation is a functional demonstration, not a production design. The application is intentionally modest; the platform and delivery workflow are the main project.

## System view

Terraform provisions the AWS foundation and selected Kubernetes add-ons. Kustomize defines the application resources. Jenkins tests and builds the container, publishes it, and changes the image tag in Git. Argo CD watches that Git path and reconciles Kubernetes from it.

```text
Developer change → GitHub → Jenkins → Docker Hub
                               │
                               └─ commits image tag → GitHub
                                                        │
                                                     Argo CD
                                                        │
                                                        ▼
                                                       EKS
```

The [CI/CD + GitOps diagram](../../Diagrams/AWS/CD_+_GitOps_flow.md) shows the delivery path; the [Terraform diagram](../../Diagrams/AWS/Terraform_infrastructure.md) shows the infrastructure relationships.

## AWS infrastructure and networking

The `dev` Terraform environment composes modules under `terraform/modules/`. The VPC module declares a `10.0.0.0/16` VPC, an Internet Gateway, two public and two private subnets across the configured Availability Zones, and route tables. The module routes public subnet traffic to the Internet Gateway. It creates private route tables and associations but no NAT gateway or private default route.

The environment passes the public subnet IDs to both the EKS cluster and managed node group. Jenkins is also configured in a public subnet with a public IP. Therefore, private subnets exist in Terraform but are not the current EKS node placement. Jenkins' security group allows inbound TCP 8080 from `0.0.0.0/0`; this is a demonstration configuration with a material exposure limitation.

See [networking flow](../../Diagrams/AWS/Networking_flow.md) and the [traffic-focused view](../../Diagrams/AWS/Networking_traffic_focused.md). Those diagrams are reference assets; consult the current Terraform and Kubernetes manifests for exact configuration.

## EKS and identity

The EKS module declares the cluster and a managed node group named by the `dev` environment. The checked-in environment currently specifies Kubernetes version `1.36`, `t3.medium` instances, 20 GiB node disks, and node group desired/min/max sizes of 2/2/3. These are repository configuration values, not a live-cluster inventory.

The module declares the EKS Pod Identity Agent add-on. The EBS CSI add-on uses Pod Identity association for `ebs-csi-controller-sa` and an IAM role attached to `AmazonEBSCSIDriverPolicy`. A separate application role is associated with the `devshop` service account in namespace `devshop`; its policy grants access to the project's Secrets Manager secret.

## Kubernetes workload and persistence

`k8s/base/` contains the `devshop` namespace, FastAPI Deployment and NodePort Service, PostgreSQL StatefulSet and headless Service, PVC, migration Job, service account, and SecretProviderClass. The `aws` overlay selects the AWS gp3 StorageClass and sets the application image tag. The Argo CD Application points at `k8s/overlays/aws` on `master` and enables automated sync, pruning, and self-healing.

The current application service is a Kubernetes NodePort; the repository does not configure an AWS load balancer or ingress for FastAPI. The Argo CD Helm module separately configures the Argo CD server Service as `LoadBalancer` with an NLB annotation. Do not conflate that Argo CD endpoint with application exposure.

PostgreSQL intentionally runs inside EKS for the project. Its single replica mounts a 5 GiB PVC on the AWS overlay, dynamically backed by EBS gp3 using `ebs.csi.aws.com`. The StorageClass uses `WaitForFirstConsumer`, allows expansion, and has `reclaimPolicy: Delete`. The recorded verification established that data survived deletion and recreation of the pod while the PVC remained. It does not establish survival of PVC or cluster deletion, backup recovery, or production availability. See [PostgreSQL persistence](../../Diagrams/AWS/PostgreSQL_persistence.md) and the [persistence test](../tests/persistence/postgres-pod-recreation.md).

## Secrets

Terraform creates the `devshop/devshop` Secrets Manager secret and populates its JSON fields from sensitive variables. The application Pod Identity role grants `GetSecretValue` and `DescribeSecret` for that secret. The Secrets Store CSI Driver and AWS provider are installed by the secrets-store Terraform module, with Kubernetes Secret synchronization enabled.

The `SecretProviderClass` maps the secret fields and syncs `devshop-secret`, which is consumed by the application, PostgreSQL, and migration Job. The intended flow is:

```text
AWS Secrets Manager → Secrets Store CSI → SecretProviderClass
                    → Kubernetes Secret → application / PostgreSQL / migration
```

Secret values are not part of the manifests or documentation.

## Jenkins, Docker, and GitOps ownership

Terraform's Jenkins module provisions an EC2 instance and bootstrap script that install Jenkins, Docker, AWS CLI, kubectl, and Trivy. The Jenkinsfile starts a CI PostgreSQL container, applies Alembic migrations to the test database, runs pytest, builds the image, scans it with Trivy, runs the image, publishes it to Docker Hub, edits the AWS Kustomize image tag, validates the rendered manifests, then commits and pushes that GitOps change.

Jenkins does not apply the application manifests to Kubernetes in the current pipeline. The Git change is the handoff; Argo CD owns reconciliation into the cluster. See the [CI/CD + GitOps diagram](../../Diagrams/AWS/CD_+_GitOps_flow.md).

The repository also has a separate OWASP ZAP in-cluster procedure under `security/zap/`. Its own documentation says it runs outside Jenkins. The current Jenkinsfile has no OWASP Dependency-Check stage, and no runnable Dependency-Check configuration was found in the repository.

## Terraform module relationship

`terraform/environments/dev/` is the root configuration: it selects provider settings, supplies environment values, composes modules, and exposes outputs. `terraform/modules/` contains the implementation for the VPC, EKS, Jenkins, Argo CD, and Secrets Store components. The environment passes VPC outputs into EKS and Jenkins, and declares dependencies so cluster and CSI prerequisites precede the Helm releases. These are project modules; the repository does not establish them as generic published modules.

For rebuild steps and current-value discovery, see [AWS deployment](../deployment/aws-deployment.md) and the [EKS rebuild runbook](../runbooks/rebuild-eks.md). The [destruction lesson](../../Diagrams/AWS/Destruction_problem.md) preserves an important resource-lifecycle troubleshooting context.
