PostgreSQL Pod Recreation Persistence Test

Test ID: TEST-001
Date: 2026-09-23
Environment: AWS EKS
Cluster: devshop-eks
Namespace: devshop

Objective

Verify that PostgreSQL application data survives deletion and recreation of the PostgreSQL pod.

The purpose of this test is to confirm that database data is stored on persistent storage through the Kubernetes PersistentVolumeClaim (PVC) and AWS EBS volume rather than inside the lifecycle of the PostgreSQL pod itself.

Architecture
DevShop Application
        |
        v
devshop-postgres Service
        |
        v
PostgreSQL StatefulSet
        |
        v
devshop-postgres-0
        |
        v
PersistentVolumeClaim
devshop-postgres-data
        |
        v
PersistentVolume
        |
        v
AWS EBS gp3
        |
        v
5 GiB persistent storage


The expected behavior is:

PostgreSQL Pod
      |
      X  DELETE POD
      |
      v
StatefulSet creates replacement pod
      |
      v
Same PVC
      |
      v
Same EBS-backed storage
      |
      v
Existing PostgreSQL data

Storage Configuration

The PostgreSQL workload uses the AWS-specific StorageClass:

apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: devshop-gp3
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
parameters:
  type: gp3
  fsType: ext4
reclaimPolicy: Delete

Important

The current StorageClass uses:

reclaimPolicy: Delete


This means the EBS volume should not be treated as independently protected from deletion of the Kubernetes storage resources.

This test only validates pod recreation. It does not validate PVC deletion or EKS cluster destruction.

Initial Validation

Verify the PostgreSQL StatefulSet:

AWS_PROFILE=devshop kubectl get statefulset devshop-postgres -n devshop


Expected:

NAME               READY
devshop-postgres   1/1


Verify the PVC:

AWS_PROFILE=devshop kubectl get pvc devshop-postgres-data -n devshop


Expected:

NAME                    STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS
devshop-postgres-data   Bound    pvc-c9ac1d4d-0353-4d8a-ac0a-7bf16a945008   5Gi        RWO            devshop-gp3


Verify the PostgreSQL pod:

AWS_PROFILE=devshop kubectl get pod devshop-postgres-0 \
  -n devshop \
  -o wide


Initial state:

devshop-postgres-0   1/1   Running

Test Data

A test administrator account and product were created before performing the pod recreation test.

Administrator
Email: admin@example.com
Role: administrator

Product
Name: AWS DevShop Laptop
Price: 1299.99
Stock quantity: 10


Verify the product directly in PostgreSQL:

AWS_PROFILE=devshop kubectl exec \
  -n devshop \
  devshop-postgres-0 \
  -- psql -U devshop -d devshop_test \
  -c "SELECT id, name, price, stock_quantity FROM products WHERE name = 'AWS DevShop Laptop';"


Observed result:

 id |        name        |  price  | stock_quantity
----+--------------------+---------+----------------
  1 | AWS DevShop Laptop | 1299.99 |             10


Verify the administrator:

AWS_PROFILE=devshop kubectl exec \
  -n devshop \
  devshop-postgres-0 \
  -- psql -U devshop -d devshop_test \
  -c "SELECT id, email, role FROM users WHERE email = 'admin@example.com';"


Observed result:

 id |       email       |     role
----+-------------------+---------------
  1 | admin@example.com | administrator

Test Procedure
1. Record the current PostgreSQL pod
AWS_PROFILE=devshop kubectl get pod devshop-postgres-0 \
  -n devshop \
  -o wide


Initial pod:

devshop-postgres-0

2. Record the PVC
AWS_PROFILE=devshop kubectl get pvc devshop-postgres-data \
  -n devshop


The PVC was:

STATUS: Bound
CAPACITY: 5Gi
STORAGECLASS: devshop-gp3

3. Delete the PostgreSQL pod
AWS_PROFILE=devshop kubectl delete pod \
  devshop-postgres-0 \
  -n devshop


This intentionally deletes only the pod.

The StatefulSet and PVC are not deleted.

4. Observe pod recreation
AWS_PROFILE=devshop kubectl get pods \
  -n devshop \
  -w


The StatefulSet recreated:

devshop-postgres-0


The replacement pod reached:

READY   1/1
STATUS  Running

5. Verify the PVC
AWS_PROFILE=devshop kubectl get pvc \
  devshop-postgres-data \
  -n devshop


The PVC remained:

STATUS: Bound


The same volume remained associated with the PVC:

pvc-c9ac1d4d-0353-4d8a-ac0a-7bf16a945008

6. Verify the product after pod recreation
AWS_PROFILE=devshop kubectl exec \
  -n devshop \
  devshop-postgres-0 \
  -- psql -U devshop -d devshop_test \
  -c "SELECT id, name, price, stock_quantity FROM products WHERE name = 'AWS DevShop Laptop';"


Observed:

 id |        name        |  price  | stock_quantity
----+--------------------+---------+----------------
  1 | AWS DevShop Laptop | 1299.99 |             10

7. Verify the administrator after pod recreation
AWS_PROFILE=devshop kubectl exec \
  -n devshop \
  devshop-postgres-0 \
  -- psql -U devshop -d devshop_test \
  -c "SELECT id, email, role FROM users WHERE email = 'admin@example.com';"


Observed:

 id |       email       |     role
----+-------------------+---------------
  1 | admin@example.com | administrator

Result

PASS

The PostgreSQL pod was deleted and recreated successfully.

The following remained intact:

PostgreSQL StatefulSet

PostgreSQL PVC

EBS-backed persistent storage

Administrator account

Product data

The replacement PostgreSQL pod successfully mounted the existing persistent storage.

What This Test Demonstrates

This test demonstrates the difference between pod lifecycle and persistent storage lifecycle.

The PostgreSQL pod is disposable:

Pod
  ↓
can be deleted
  ↓
StatefulSet recreates it


The database data is stored separately:

Pod
 ↓
PVC
 ↓
PV
 ↓
EBS


Therefore, deleting the pod does not delete the database.

This is one of the key reasons Kubernetes StatefulSets are commonly used with persistent workloads.

What This Test Does NOT Demonstrate

This test does not prove that the data will survive:

PVC deletion

PV deletion

StorageClass deletion

EKS cluster deletion

AWS account/resource deletion

Those are separate storage lifecycle scenarios.

The current StorageClass uses:

reclaimPolicy: Delete


Therefore, destructive storage experiments should be performed deliberately and only after deciding whether the underlying EBS volume should be preserved.

Troubleshooting Notes

During the AWS EKS setup, the EBS CSI driver initially experienced an IAM authorization problem:

ec2:DescribeAvailabilityZones
UnauthorizedOperation


The problem was related to the EBS CSI controller's IAM/Pod Identity configuration.

The final architecture uses:

EBS CSI Controller
        |
        v
ebs-csi-controller-sa
        |
        v
EKS Pod Identity
        |
        v
devshop-eks-ebs-csi-role
        |
        v
AmazonEBSCSIDriverPolicy
        |
        v
AWS EBS APIs


This is important because the EBS CSI controller should have its required AWS permissions through its dedicated identity rather than relying on the worker node IAM role.

Lessons Learned
1. Pods are disposable

Deleting the PostgreSQL pod does not necessarily mean deleting the database.

The StatefulSet recreated the pod automatically.

2. Persistent storage is independent of pod lifecycle

The PostgreSQL data survived because the replacement pod mounted the existing PVC.

3. StatefulSet provides stable workload identity

The PostgreSQL workload returned as:

devshop-postgres-0


rather than receiving an arbitrary deployment-style pod identity.

4. PVC is the Kubernetes abstraction for persistent storage

The application does not directly manage the EBS volume.

The relationship is:

PostgreSQL
    ↓
Pod
    ↓
PVC
    ↓
PV
    ↓
EBS CSI Driver
    ↓
AWS EBS

5. Reclaim policy matters

The current:

reclaimPolicy: Delete


is acceptable for this disposable demonstration environment, but would require reconsideration for a production workload where data preservation is important.

Future Tests

Potential future storage tests:

Delete and recreate the PostgreSQL pod — completed

Reschedule PostgreSQL onto another EKS node

Verify EBS volume attachment to the new node

Test application recovery after node failure

Test PVC expansion

Investigate EBS volume lifecycle

Compare Delete versus Retain reclaim policies

Test backup and restore

Introduce AWS-native database backup strategies

These tests should be performed separately from this baseline test.

Final Conclusion

The AWS DevShop PostgreSQL deployment successfully demonstrated persistent database storage across PostgreSQL pod deletion and recreation.

The database records remained available after the original PostgreSQL pod was removed because the replacement pod reattached to the existing PVC backed by an AWS EBS gp3 volume.

Test status: PASS