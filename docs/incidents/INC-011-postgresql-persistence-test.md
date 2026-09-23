INC-011 — PostgreSQL Pod Recreation / Persistent Storage Test

Objective:
Verify that PostgreSQL data survives deletion and recreation
of the PostgreSQL StatefulSet pod.

Initial state:
- PostgreSQL StatefulSet: devshop-postgres
- PVC: devshop-postgres-data
- StorageClass: devshop-gp3
- Volume type: AWS EBS gp3
- Capacity: 5Gi

Test data:
- User: admin@example.com
- Role: administrator
- Product: AWS DevShop Laptop
- Product ID: 1

Procedure:
1. Verify PostgreSQL pod is Running.
2. Verify PVC is Bound.
3. Verify test records exist.
4. Delete devshop-postgres-0.
5. Wait for StatefulSet to recreate the pod.
6. Verify the PVC remains Bound.
7. Query PostgreSQL again.

Expected result:
The replacement PostgreSQL pod mounts the existing PVC
and the previously created records remain available.

Result:
PASS

Observed:
- Original PostgreSQL pod deleted.
- StatefulSet recreated devshop-postgres-0.
- PVC remained Bound.
- Administrator user remained present.
- AWS DevShop Laptop remained present.

Conclusion:
PostgreSQL data is persisted independently of the lifecycle
of the PostgreSQL pod through the Kubernetes PVC backed by
an AWS EBS gp3 volume.
