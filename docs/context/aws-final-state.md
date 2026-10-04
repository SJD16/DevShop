# AWS Phase — Final State

## Purpose and stopping point

DevShop is a small FastAPI/PostgreSQL application used as a reference workload for a hands-on DevOps/DevSecOps platform. The AWS phase reached a functional baseline for infrastructure automation, CI/CD, Kubernetes delivery, cloud identity, secrets, persistent storage, and security validation. It is intentionally stopped here while the project moves to an Azure-focused phase. No Azure implementation is present in the current repository snapshot.

This is a project state record, not a production-readiness claim. Production hardening is deliberately deferred.

## What is represented in the repository

### AWS architecture and Terraform

`terraform/environments/dev/` is the environment root. It composes project modules under `terraform/modules/` for VPC, EKS, Jenkins, Argo CD, and Secrets Store. The environment wires VPC outputs into EKS/Jenkins and passes sensitive JWT/database inputs into the EKS module. The EKS module declares a managed node group, Pod Identity Agent, EBS CSI add-on and identity, Secrets Manager secret, and application Pod Identity role.

The VPC module declares public and private subnets across two configured Availability Zones. It routes the public subnets to the Internet Gateway, but does not configure a NAT gateway or private egress route. The current dev environment passes public subnet IDs to EKS and Jenkins. Jenkins is configured with a public IP; its security group allows port 8080 from `0.0.0.0/0`.

The checked-in environment currently specifies `us-east-1`, EKS version `1.36`, an EKS node group size of 2/2/3 using `t3.medium` instances and 20 GiB node disks, and a fixed Jenkins AMI ID. These are repository inputs, not a verified live AWS inventory. Verify current compatibility and values before rebuilding.

### Kubernetes and persistence

Shared Kubernetes resources are under `k8s/base/`. The `aws` overlay selects the EBS CSI gp3 StorageClass and sets the image tag. It deploys a single-replica PostgreSQL StatefulSet with a 5 GiB PVC, a migration Job that runs Alembic, and the FastAPI Deployment. The app Service is NodePort. Argo CD's own server Service is separately configured as LoadBalancer/NLB by Terraform.

PostgreSQL intentionally runs inside EKS as a demonstration choice. The EBS-backed PVC is retained across PostgreSQL pod recreation; the AWS StorageClass has `reclaimPolicy: Delete`, so the test does not establish data survival across PVC or cluster deletion.

### Secrets and workload identity

Terraform creates the `devshop/devshop` Secrets Manager object and grants access through an EKS Pod Identity role associated with `devshop/devshop`. The SecretProviderClass consumes it through Secrets Store CSI and syncs a namespace-scoped Kubernetes Secret for the application, PostgreSQL, and migration Job. Secret values are not recorded here.

### Jenkins, Docker, and Argo CD

The Jenkins module provisions an EC2 host; its bootstrap installs Jenkins, Docker, AWS CLI, kubectl, and Trivy. Jenkins runs PostgreSQL-backed migrations and pytest, builds and validates a container, scans the image with Trivy, publishes to Docker Hub, changes the AWS Kustomize image tag, validates rendered resources, and pushes a GitOps commit. Argo CD watches `master` at `k8s/overlays/aws` with automated sync, prune, and self-heal. Jenkins hands off through Git; it does not directly apply application manifests.

The repository contains a separate procedure for running OWASP ZAP in a temporary in-cluster pod. The current Jenkinsfile does not run OWASP Dependency-Check, despite that tool being named in the ZAP notes. No Dependency-Check pipeline stage or runnable configuration was found in this snapshot. Trivy writes a table report but does not set an explicit vulnerability threshold or failing exit code.

## What was verified

- The checked-in Jenkinsfile defines migration, pytest, container build/run, Trivy scanning, Docker Hub push, Kustomize render validation, and a GitOps commit/push path. This documents pipeline behavior; this documentation update did not run Jenkins.
- The persistence record reports that `devshop-postgres-0` was deleted and recreated, its PVC remained bound, and the recorded administrator and product remained queryable. See [INC-011](../incidents/INC-011-postgresql-persistence-test.md) and the [repeatable test](../tests/persistence/postgres-pod-recreation.md).
- The current Kubernetes and Terraform files establish declared configuration. No live AWS account/cluster verification was performed as part of this update.

## Architecture decisions

- PostgreSQL runs in EKS for this learning environment; this does not imply it is the preferred production database architecture.
- EBS CSI provides the AWS overlay's persistent block storage. Pod recovery was tested; backup, restore, and PVC/cluster destruction were not.
- The FastAPI app uses NodePort. The NLB belongs to the Argo CD server Service.
- Jenkins communicates desired application changes through Git. Argo CD owns Kubernetes reconciliation.
- Runtime secrets are fetched from Secrets Manager via Secrets Store CSI and Pod Identity; values are not committed to manifests.

## Lessons preserved

- EBS CSI previously encountered an `ec2:DescribeAvailabilityZones` authorization issue; the current EKS module declares a dedicated CSI Pod Identity role/association.
- Secrets Store CSI synchronization and Kubernetes Secret namespace scope are dependencies for workload startup. A missing synced Secret was a troubleshooting symptom in the previous rebuild notes.
- PostgreSQL data directories should use a subdirectory such as the configured `PGDATA` when a mounted filesystem contains `lost+found`.
- A Kubernetes Service of type LoadBalancer can create an NLB and network interfaces outside the direct EKS Terraform resource graph. If the Kubernetes controller becomes unavailable during cluster teardown, those resources may remain and block VPC cleanup. See [Destruction problem](../../Diagrams/AWS/Destruction_problem.md).
- The current StorageClass reclaim policy is `Delete`; a passing pod-recreation check is not evidence of safe PVC destruction.

The tracked repository does not provide enough evidence to attribute a specific historical Terraform state drift or Helm/Terraform ownership conflict, so neither is stated here as a verified event.

## Deferred production improvements

Production-grade database availability and recovery, safer storage retention, restricted administrative access, private network egress/placement design, and broader operational monitoring are outside this demonstration baseline. These items are intentionally deferred rather than treated as a blocker to the learning milestone.

## Current stopping point

The AWS phase has a documented functional DevOps/DevSecOps baseline. The current work stops before an Azure-focused phase; further production-hardening is intentionally deferred. For the repository's current rebuild path, see [AWS deployment](../deployment/aws-deployment.md) and [Rebuild EKS](../runbooks/rebuild-eks.md).
