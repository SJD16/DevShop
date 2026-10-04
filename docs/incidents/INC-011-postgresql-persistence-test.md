# INC-011 — PostgreSQL Pod Recreation and Persistence Test

**Type:** Engineering verification record

**Recorded environment:** AWS EKS, namespace `devshop`

**Recorded result:** PASS

## What was being tested

The test checked whether PostgreSQL application data survived deletion and recreation of the PostgreSQL StatefulSet pod. It was intended to verify the boundary between a disposable pod and the persistent storage attached through its PVC. It did not test deletion of the PVC, PV, StorageClass, or EKS cluster.

The storage path is documented in the [PostgreSQL persistence diagram](../../Diagrams/AWS/PostgreSQL_persistence.md). The repeatable procedure is in the [pod recreation test](../tests/persistence/postgres-pod-recreation.md).

## Initial state

- StatefulSet: `devshop-postgres`, one replica.
- Pod: `devshop-postgres-0`.
- PVC: `devshop-postgres-data`, bound, 5 GiB.
- AWS overlay StorageClass: `devshop-gp3`, EBS gp3 through `ebs.csi.aws.com`.
- Existing records included administrator `admin@example.com` and product `AWS DevShop Laptop` (recorded product ID 1).

## Test procedure and observations

1. Confirmed the PostgreSQL pod was running and the PVC was bound.
2. Confirmed the known administrator and product records were present.
3. Deleted only `devshop-postgres-0`; the StatefulSet, PVC, and storage resources were left in place.
4. Waited for the StatefulSet to recreate the pod.
5. Confirmed the replacement pod became ready, the PVC remained bound, and the known records were still queryable.

## Result

**PASS.** Kubernetes recreated the PostgreSQL pod and it mounted the existing PVC. The administrator and product records remained available after the pod replacement.

## Lesson learned

Deleting a pod managed by a StatefulSet is different from deleting its persistent storage. The PVC and its bound volume outlived this pod recreation, so the replacement could mount the same data. This test does not establish protection from PVC deletion or cluster teardown: the current AWS StorageClass has `reclaimPolicy: Delete`.

During the broader AWS work, the repository also records an EBS CSI authorization issue involving `ec2:DescribeAvailabilityZones`; the current Terraform implementation configures a dedicated CSI role through EKS Pod Identity. The [destruction problem diagram](../../Diagrams/AWS/Destruction_problem.md) records the separate risk that an AWS load balancer created from a Kubernetes Service may remain during EKS teardown and interfere with VPC deletion.
