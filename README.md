# DevShop

## Overview

DevShop is a small FastAPI and PostgreSQL application used as the reference workload for a hands-on DevOps/DevSecOps platform. The primary focus is the delivery and infrastructure around the application: infrastructure automation, containers, CI/CD, Kubernetes, GitOps, cloud identity, persistent storage, secrets management, and security validation.

This is a functional demonstration environment, not a production system.

## Project Goals

- Build repeatable cloud infrastructure with Terraform.
- Package and validate an application using Docker and Jenkins.
- Deploy to Kubernetes with Kustomize and Argo CD.
- Practice AWS workload identity, managed secrets, and persistent block storage.
- Record operational verification and lessons from troubleshooting.

## Architecture

The AWS phase runs FastAPI and PostgreSQL on Amazon EKS. PostgreSQL is a single-replica StatefulSet using a PVC backed by EBS gp3. Jenkins builds and scans the image, publishes it to Docker Hub, and commits its image tag to Git; Argo CD synchronizes that Git state to Kubernetes.

See the [AWS architecture](docs/architecture/aws-architecture.md) and its [network flow](Diagrams/AWS/Networking_flow.md).

## Technology Stack

FastAPI, SQLAlchemy, Alembic, PostgreSQL, pytest, Docker, Jenkins, Trivy, Kubernetes, Kustomize, Argo CD, Terraform, Amazon EKS, AWS Secrets Manager, EKS Pod Identity, and Secrets Store CSI Driver.

## AWS Infrastructure

Terraform composes VPC, EKS, Jenkins, Argo CD, and secrets-store modules through the `dev` environment. The EKS node group uses public subnets in the current configuration. The VPC module also declares private subnets, but does not configure private egress. See [AWS deployment](docs/deployment/aws-deployment.md) and the [Terraform infrastructure diagram](Diagrams/AWS/Terraform_infrastructure.md).

## CI/CD + GitOps

Jenkins runs the Python checks against PostgreSQL, builds and validates a Docker image, scans it with Trivy, publishes it to Docker Hub, then commits the new image tag to the repository. Argo CD watches the configured Git path and synchronizes the Kubernetes manifests. See the [CI/CD + GitOps flow](Diagrams/AWS/CD_+_GitOps_flow.md).

## Security

The Jenkinsfile includes Trivy image scanning. The repository also contains a separate OWASP ZAP procedure for in-cluster dynamic scanning. The current Jenkinsfile does not contain an OWASP Dependency-Check stage; the ZAP notes mention Dependency-Check as a project control, but a runnable configuration was not found in the repository. The Trivy stage records a table report but does not set an explicit vulnerability threshold or failing exit code.

## Persistence

The AWS Kustomize overlay configures PostgreSQL storage through the EBS CSI driver and gp3 StorageClass. The recorded pod recreation test passed: the StatefulSet recreated the PostgreSQL pod while the bound PVC and test records remained. This verifies pod recreation only; the StorageClass reclaim policy is `Delete`. See the [repeatable test](docs/tests/persistence/postgres-pod-recreation.md) and [incident record](docs/incidents/INC-011-postgresql-persistence-test.md).

## Validation

The repository records application CI stages, Kubernetes manifest rendering, runtime checks, and the PostgreSQL pod recreation result. This documentation change validates repository references and Markdown links; it does not re-run the AWS deployment or application pipeline.

## Repository Structure

```text
Diagrams/AWS/       Architecture and operational diagrams
docs/               AWS, local development, runbooks, and test records
k8s/base/           Shared Kubernetes resources
k8s/overlays/aws/   AWS EKS configuration
k8s/overlays/dev/   Local development configuration
terraform/          dev environment and infrastructure modules
security/zap/       Separate OWASP ZAP procedure
```

## Current Status

The AWS phase reached a functional DevOps/DevSecOps baseline and is intentionally stopped while the project moves to an Azure-focused phase. Production hardening is deferred; AWS is not presented as production-ready.

## Known Limitations

- PostgreSQL is a single-replica in-cluster workload on EBS, intended for demonstration.
- The application is exposed through a Kubernetes NodePort. Argo CD separately uses a Terraform-configured AWS Network Load Balancer.
- The Jenkins security group currently allows port 8080 from `0.0.0.0/0`.
- The Terraform VPC module creates private subnets without NAT or another egress route, while EKS and Jenkins are configured in public subnets.
- The current repository does not define an OWASP Dependency-Check pipeline stage or configuration.

## Documentation

- [AWS architecture](docs/architecture/aws-architecture.md)
- [AWS deployment](docs/deployment/aws-deployment.md)
- [Local development](docs/deployment/local-development.md)
- [Rebuild EKS runbook](docs/runbooks/rebuild-eks.md)
- [PostgreSQL pod recreation test](docs/tests/persistence/postgres-pod-recreation.md)
- [PostgreSQL persistence incident record](docs/incidents/INC-011-postgresql-persistence-test.md)
- [AWS final state](docs/context/aws-final-state.md)

## Local Development

Start with the [local development guide](docs/deployment/local-development.md). It covers Python setup, environment variables, PostgreSQL, Alembic, the FastAPI server, tests, and Docker.
