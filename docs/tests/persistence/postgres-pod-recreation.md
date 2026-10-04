# PostgreSQL Pod Recreation Persistence Test

This test verifies that a known product record survives deletion and recreation of the PostgreSQL pod. It deliberately deletes only the pod. Do not use it to infer safety of deleting the PVC, PV, EBS volume, or cluster.

The recorded execution passed; see [INC-011](../../incidents/INC-011-postgresql-persistence-test.md). The data path is shown in the [PostgreSQL persistence diagram](../../../Diagrams/AWS/PostgreSQL_persistence.md).

## Preconditions

- Current `kubectl` context points to the intended EKS cluster.
- Namespace `devshop` has a ready DevShop application and PostgreSQL StatefulSet.
- The `devshop-postgres-data` PVC is bound.
- You can create a unique marker product through the DevShop API using an administrator account, or insert it directly into the development database. Use disposable test data only.

## Procedure

### 1. Create known test data

Create a unique product through the application API and record its exact name and ID. Alternatively, insert a marker directly into PostgreSQL (replace the marker with a unique value for this run):

```sh
kubectl exec -n devshop devshop-postgres-0 -- \
  psql -U devshop -d devshop \
  -c "INSERT INTO products (name, description, price, stock_quantity, is_active) VALUES ('persistence-check-REPLACE-ME', 'pod recreation test', 1.00, 1, true) RETURNING id, name;"
```

Record the returned product ID and unique name. Use the configured database name if it differs from `devshop`.

### 2. Identify the PostgreSQL pod

```sh
kubectl get pods -n devshop -l app=devshop-postgres -o wide
```

Record the current pod name. The current StatefulSet creates `devshop-postgres-0`.

### 3. Verify the PVC and record its PV

```sh
kubectl get pvc devshop-postgres-data -n devshop -o wide
export POSTGRES_PV="$(kubectl get pvc devshop-postgres-data -n devshop -o jsonpath='{.spec.volumeName}')"
kubectl get pv "$POSTGRES_PV" -o wide
```

The PVC should be `Bound`. Record the PV name for comparison after recreation.

### 4. Delete only the PostgreSQL pod

```sh
kubectl delete pod devshop-postgres-0 -n devshop
```

Do not delete the StatefulSet or PVC.

### 5. Wait for Kubernetes to recreate it

```sh
kubectl wait --for=condition=Ready pod/devshop-postgres-0 -n devshop --timeout=5m
kubectl get pod devshop-postgres-0 -n devshop -o wide
```

The pod should return to `Running` and become ready.

### 6. Verify the PVC/PV remains bound

```sh
kubectl get pvc devshop-postgres-data -n devshop -o wide
kubectl get pv "$POSTGRES_PV" -o wide
```

The PVC should remain `Bound` to the same PV recorded before deletion.

### 7. Verify PostgreSQL is ready

```sh
kubectl exec -n devshop devshop-postgres-0 -- pg_isready -U devshop -d devshop
```

The command should report that PostgreSQL accepts connections. If not, inspect the pod events and logs before continuing.

### 8. Query the application/database again

Query the marker record directly, replacing the value with the unique name from step 1:

```sh
kubectl exec -n devshop devshop-postgres-0 -- \
  psql -U devshop -d devshop \
  -c "SELECT id, name, price, stock_quantity FROM products WHERE name = 'persistence-check-REPLACE-ME';"
```

Optionally verify the application path too: port-forward `svc/devshop` in one terminal, then request `GET /products` from another and confirm the marker product appears.

### 9. Confirm the record survived

Compare the returned product ID and values with the values recorded before pod deletion.

## Expected result

The PostgreSQL pod is recreated and ready, the PVC remains bound to the same PV, and the exact marker record remains queryable. Record the date, cluster/environment, pod name before and after, PVC/PV status, marker ID, and PASS/FAIL outcome without recording credentials or Secret values.

This test validates pod recreation only. The current AWS StorageClass uses `reclaimPolicy: Delete`; PVC removal or cluster teardown can have a different volume lifecycle and requires a separate test and data-retention decision.
