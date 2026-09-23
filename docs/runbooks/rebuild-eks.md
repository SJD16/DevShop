DevShop EKS Rebuild Runbook

This runbook rebuilds the disposable AWS/EKS development environment for DevShop.

The environment is intentionally disposable. PostgreSQL uses an EBS-backed PVC so that pod recreation can be tested, but the current StorageClass uses:

reclaimPolicy: Delete

Therefore, deleting the PVC/cluster can also delete the underlying EBS volume.

For persistent production data, this configuration must be changed.
0. Environment Variables

Set the environment variables used throughout the runbook.

export AWS_PROFILE=devshop
export AWS_REGION=us-east-1
export CLUSTER_NAME=devshop-eks
export NAMESPACE=devshop
export NODEPORT=31140
export CLIENT_IP="$(curl -4 -s https://checkip.amazonaws.com)"

Verify:

echo "AWS_PROFILE=$AWS_PROFILE"
echo "AWS_REGION=$AWS_REGION"
echo "CLUSTER_NAME=$CLUSTER_NAME"
echo "CLIENT_IP=$CLIENT_IP"

The CLIENT_IP value is the public IPv4 address from which the NodePort will be accessed.

If the public IP changes, the security-group rule must be updated.
1. Authenticate to AWS

aws login --profile "$AWS_PROFILE"

Verify the active identity:

AWS_PROFILE="$AWS_PROFILE" aws sts get-caller-identity

Verify the selected region:

AWS_PROFILE="$AWS_PROFILE" aws configure get region

2. Create the EKS Cluster

The cluster definition is stored in:

aws/eks/cluster.yaml

Create the cluster:

AWS_PROFILE="$AWS_PROFILE" eksctl create cluster \
  --config-file aws/eks/cluster.yaml

Wait for the cluster to become available.

Verify:

AWS_PROFILE="$AWS_PROFILE" kubectl get nodes -o wide

Expected:

NAME                           STATUS   ROLES    AGE   VERSION
...                            Ready    <none>   ...   ...
...                            Ready    <none>   ...   ...

Record the node information:

AWS_PROFILE="$AWS_PROFILE" kubectl get nodes -o wide

Do not hardcode node public IPs in this runbook. They can change after rebuilding the cluster.
3. Install EKS Pod Identity Agent

Install the EKS Pod Identity Agent:

AWS_PROFILE="$AWS_PROFILE" eksctl create addon \
  --cluster="$CLUSTER_NAME" \
  --name=eks-pod-identity-agent \
  --region="$AWS_REGION" \
  --wait

Verify:

AWS_PROFILE="$AWS_PROFILE" kubectl get pods \
  -n kube-system \
  -l app.kubernetes.io/instance=eks-pod-identity-agent

Also verify the addon:

AWS_PROFILE="$AWS_PROFILE" aws eks describe-addon \
  --cluster-name "$CLUSTER_NAME" \
  --addon-name eks-pod-identity-agent \
  --region "$AWS_REGION"

4. Install the AWS EBS CSI Driver

The PostgreSQL StatefulSet requires the EBS CSI driver to dynamically provision the EBS volume.

Install the addon:

AWS_PROFILE="$AWS_PROFILE" eksctl create addon \
  --cluster "$CLUSTER_NAME" \
  --region "$AWS_REGION" \
  --name aws-ebs-csi-driver \
  --version v1.66.0-eksbuild.1 \
  --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy \
  --auto-apply-pod-identity-associations \
  --wait

Verify the addon:

AWS_PROFILE="$AWS_PROFILE" aws eks describe-addon \
  --cluster-name "$CLUSTER_NAME" \
  --addon-name aws-ebs-csi-driver \
  --region "$AWS_REGION"

Verify the CSI components:

AWS_PROFILE="$AWS_PROFILE" kubectl get pods \
  -n kube-system \
  -l app.kubernetes.io/name=aws-ebs-csi-driver

5. Verify the EBS CSI Pod Identity Association

The CSI controller needs AWS permissions through EKS Pod Identity.

Check the association:

AWS_PROFILE="$AWS_PROFILE" aws eks list-pod-identity-associations \
  --cluster-name "$CLUSTER_NAME" \
  --region "$AWS_REGION"

Look for an association containing:

namespace: kube-system
service account: ebs-csi-controller-sa

You can also inspect the service account:

AWS_PROFILE="$AWS_PROFILE" kubectl get serviceaccount \
  ebs-csi-controller-sa \
  -n kube-system \
  -o yaml

If the association does not exist

Create it:

AWS_PROFILE="$AWS_PROFILE" eksctl create podidentityassociation \
  --cluster "$CLUSTER_NAME" \
  --region "$AWS_REGION" \
  --namespace kube-system \
  --service-account-name ebs-csi-controller-sa \
  --role-name devshop-eks-ebs-csi-role \
  --permission-policy-arns arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy

Then restart the CSI controller pods so they receive the Pod Identity credentials:

AWS_PROFILE="$AWS_PROFILE" kubectl delete pods \
  -n kube-system \
  -l app.kubernetes.io/name=aws-ebs-csi-driver,app.kubernetes.io/component=csi-driver

Wait for them:

AWS_PROFILE="$AWS_PROFILE" kubectl get pods \
  -n kube-system \
  -l app.kubernetes.io/name=aws-ebs-csi-driver \
  -w

They should eventually return to:

Running

Important

Do not blindly create the Pod Identity association every rebuild.

First check whether it already exists.

Creating infrastructure blindly is one of the reasons rebuild procedures become confusing.
6. Create the DevShop Namespace

Create the namespace:

AWS_PROFILE="$AWS_PROFILE" kubectl create namespace "$NAMESPACE"

If it already exists:

AWS_PROFILE="$AWS_PROFILE" kubectl get namespace "$NAMESPACE"

7. Create the Application Secret

The application requires:

    JWT_SECRET_KEY

    DB_PASSWORD

Do not commit these values to Git.

Generate a new JWT secret:

export JWT_SECRET_KEY="$(openssl rand -hex 32)"

Set the development database password:

export DB_PASSWORD='CHANGE_ME'

Create the Kubernetes Secret:

AWS_PROFILE="$AWS_PROFILE" kubectl create secret generic devshop-secret \
  --namespace "$NAMESPACE" \
  --from-literal=JWT_SECRET_KEY="$JWT_SECRET_KEY" \
  --from-literal=DB_PASSWORD="$DB_PASSWORD"

Verify that the Secret exists without printing its contents:

AWS_PROFILE="$AWS_PROFILE" kubectl get secret \
  devshop-secret \
  -n "$NAMESPACE"

Do not run commands that expose the secret value unnecessarily.
8. Deploy DevShop

Deploy the AWS overlay:

AWS_PROFILE="$AWS_PROFILE" kubectl apply -k k8s/overlays/aws

The AWS overlay contains the AWS-specific StorageClass/PVC configuration.

Verify:

AWS_PROFILE="$AWS_PROFILE" kubectl get pods -n "$NAMESPACE"

AWS_PROFILE="$AWS_PROFILE" kubectl get svc -n "$NAMESPACE"

AWS_PROFILE="$AWS_PROFILE" kubectl get pvc -n "$NAMESPACE"

9. Verify PostgreSQL Storage

Check the PVC:

AWS_PROFILE="$AWS_PROFILE" kubectl get pvc \
  devshop-postgres-data \
  -n "$NAMESPACE"

Expected:

STATUS   Bound

Get the PV:

AWS_PROFILE="$AWS_PROFILE" kubectl get pvc \
  devshop-postgres-data \
  -n "$NAMESPACE" \
  -o jsonpath='{.spec.volumeName}{"\n"}'

Store it:

export POSTGRES_PV="$(
  AWS_PROFILE="$AWS_PROFILE" kubectl get pvc \
    devshop-postgres-data \
    -n "$NAMESPACE" \
    -o jsonpath='{.spec.volumeName}'
)"

Inspect it:

AWS_PROFILE="$AWS_PROFILE" kubectl get pv "$POSTGRES_PV" -o wide

Verify the AWS EBS volume:

AWS_PROFILE="$AWS_PROFILE" kubectl get pv "$POSTGRES_PV" \
  -o jsonpath='{.spec.csi.volumeHandle}{"\n"}'

The result should look like:

vol-xxxxxxxxxxxxxxxxx

10. Verify PostgreSQL

Check the StatefulSet:

AWS_PROFILE="$AWS_PROFILE" kubectl get statefulset \
  devshop-postgres \
  -n "$NAMESPACE"

Check the pod:

AWS_PROFILE="$AWS_PROFILE" kubectl get pod \
  devshop-postgres-0 \
  -n "$NAMESPACE" \
  -o wide

Check logs if necessary:

AWS_PROFILE="$AWS_PROFILE" kubectl logs \
  -n "$NAMESPACE" \
  devshop-postgres-0

11. Verify the Migration Job

Check:

AWS_PROFILE="$AWS_PROFILE" kubectl get jobs -n "$NAMESPACE"

The migration job should show:

Complete

If necessary:

AWS_PROFILE="$AWS_PROFILE" kubectl logs \
  -n "$NAMESPACE" \
  job/devshop-migration

12. Verify the Application

Check the Deployment:

AWS_PROFILE="$AWS_PROFILE" kubectl get deployment \
  devshop \
  -n "$NAMESPACE"

Check the Service:

AWS_PROFILE="$AWS_PROFILE" kubectl get svc \
  devshop \
  -n "$NAMESPACE"

The Service should be a NodePort.

Get the dynamically assigned NodePort:

export DEVSHOP_NODEPORT="$(
  AWS_PROFILE="$AWS_PROFILE" kubectl get svc devshop \
    -n "$NAMESPACE" \
    -o jsonpath='{.spec.ports[0].nodePort}'
)"

Verify:

echo "$DEVSHOP_NODEPORT"

Do not assume the NodePort will always be 31140.
13. Discover the Current Node Security Group

Do not reuse a security-group ID from a previous EKS cluster.

First obtain the EC2 instances:

AWS_PROFILE="$AWS_PROFILE" aws ec2 describe-instances \
  --filters \
    "Name=tag:eks:cluster-name,Values=$CLUSTER_NAME" \
  --query 'Reservations[].Instances[].{
    InstanceId:InstanceId,
    PrivateIP:PrivateIpAddress,
    PublicIP:PublicIpAddress,
    SecurityGroups:SecurityGroups[].GroupId
  }' \
  --output table

The cluster's node security group can then be identified from the returned instances.

If multiple security groups are attached, inspect them before adding the NodePort rule.
14. Allow Temporary NodePort Access

The NodePort is intentionally restricted to the current public IP.

Set:

export CLIENT_IP="$(curl -4 -s https://checkip.amazonaws.com)"

Verify:

echo "$CLIENT_IP"

Set the correct node security group manually after inspecting the previous step:

export NODE_SECURITY_GROUP_ID="sg-XXXXXXXX"

Verify it:

echo "$NODE_SECURITY_GROUP_ID"

Then authorize the current NodePort:

AWS_PROFILE="$AWS_PROFILE" aws ec2 authorize-security-group-ingress \
  --group-id "$NODE_SECURITY_GROUP_ID" \
  --protocol tcp \
  --port "$DEVSHOP_NODEPORT" \
  --cidr "${CLIENT_IP}/32" \
  --description "Temporary DevShop NodePort access"

Important

Never copy the security-group ID from yesterday's cluster.

An EKS rebuild can produce different EC2/security-group resource IDs.

The same applies to:

    EC2 instance IDs

    public IP addresses

    private IP addresses

    EBS volume IDs

    PV names

    ENI IDs

Discover these values after every rebuild.
15. Verify NodePort Access

Get current nodes:

AWS_PROFILE="$AWS_PROFILE" kubectl get nodes -o wide

Obtain the public IPs from AWS:

AWS_PROFILE="$AWS_PROFILE" aws ec2 describe-instances \
  --filters \
    "Name=tag:eks:cluster-name,Values=$CLUSTER_NAME" \
  --query 'Reservations[].Instances[].PublicIpAddress' \
  --output text

Test using a current node public IP:

curl -v \
  --connect-timeout 10 \
  "http://<CURRENT_NODE_PUBLIC_IP>:${DEVSHOP_NODEPORT}/"

Expected:

{"message":"DevShop is working!"}

Test the products endpoint:

curl -v \
  "http://<CURRENT_NODE_PUBLIC_IP>:${DEVSHOP_NODEPORT}/products"

16. Verify Kubernetes Internal Connectivity

Before troubleshooting AWS networking, verify the application works inside Kubernetes.

AWS_PROFILE="$AWS_PROFILE" kubectl run curl-test \
  -n "$NAMESPACE" \
  --rm -it \
  --restart=Never \
  --image=curlimages/curl \
  -- \
  curl -v "http://devshop:8000/"

Expected:

{"message":"DevShop is working!"}

Test:

AWS_PROFILE="$AWS_PROFILE" kubectl run curl-test \
  -n "$NAMESPACE" \
  --rm -it \
  --restart=Never \
  --image=curlimages/curl \
  -- \
  curl -v "http://devshop:8000/products"

If this fails, investigate Kubernetes before investigating AWS security groups.
17. Initialize the Application

The database is new after a completely new cluster/storage deployment.

Register an application user through the externally reachable application:

curl -i -X POST \
  "http://<CURRENT_NODE_PUBLIC_IP>:${DEVSHOP_NODEPORT}/auth/register" \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "admin@example.com",
    "password": "admin-password"
  }'

Promote the user to administrator:

AWS_PROFILE="$AWS_PROFILE" kubectl exec \
  -n "$NAMESPACE" \
  devshop-postgres-0 \
  -- psql -U devshop -d devshop_test \
  -c "UPDATE users SET role = 'administrator' WHERE email = 'admin@example.com';"

Verify:

AWS_PROFILE="$AWS_PROFILE" kubectl exec \
  -n "$NAMESPACE" \
  devshop-postgres-0 \
  -- psql -U devshop -d devshop_test \
  -c "SELECT id, email, role FROM users WHERE email = 'admin@example.com';"

18. Authenticate

Set the current application endpoint:

export DEVSHOP_URL="http://<CURRENT_NODE_PUBLIC_IP>:${DEVSHOP_NODEPORT}"

Login:

TOKEN="$(
  curl -s -X POST \
    "$DEVSHOP_URL/auth/login" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    -d 'grant_type=password' \
    -d 'username=admin@example.com' \
    -d 'password=admin-password' \
    -d 'scope=' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])'
)"

Verify the token:

curl -s \
  -H "Authorization: Bearer $TOKEN" \
  "$DEVSHOP_URL/auth/me"

19. Create Test Data

Create a test product:

curl -s -X POST \
  "$DEVSHOP_URL/products" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "AWS DevShop Laptop",
    "description": "Test product created through the EKS deployment",
    "price": 1299.99,
    "stock_quantity": 10
  }'

Verify:

curl -s \
  "$DEVSHOP_URL/products"

20. PostgreSQL Persistence Test

This test verifies that PostgreSQL data survives PostgreSQL pod recreation.

See the dedicated runbook:

docs/runbooks/postgres-pod-recreation.md

The important distinction is:

Delete PostgreSQL Pod
        |
        v
StatefulSet recreates Pod
        |
        v
Existing PVC remains
        |
        v
Existing EBS volume remains attached
        |
        v
PostgreSQL starts
        |
        v
Existing database data remains

This is different from deleting the PVC or destroying the EKS cluster.
21. Full Health Check

Run:

AWS_PROFILE="$AWS_PROFILE" kubectl get nodes -o wide

AWS_PROFILE="$AWS_PROFILE" kubectl get pods -n "$NAMESPACE"

AWS_PROFILE="$AWS_PROFILE" kubectl get svc -n "$NAMESPACE"

AWS_PROFILE="$AWS_PROFILE" kubectl get pvc -n "$NAMESPACE"

AWS_PROFILE="$AWS_PROFILE" kubectl get pv

AWS_PROFILE="$AWS_PROFILE" kubectl get jobs -n "$NAMESPACE"

Expected components:

    EKS cluster: Ready

    EKS nodes: Ready

    Pod Identity Agent: Running

    EBS CSI controller: Running

    EBS CSI node daemonset: Running

    PostgreSQL StatefulSet: 1/1

    PostgreSQL PVC: Bound

    Migration Job: Complete

    DevShop Deployment: Available

    DevShop Service: NodePort

    Internal HTTP access: Working

    External NodePort access: Working

    /products: Working

22. Troubleshooting Order

When something fails, troubleshoot from inside outward.
Application

Application
    |
    └── Pod logs

Check:

AWS_PROFILE="$AWS_PROFILE" kubectl logs \
  -n "$NAMESPACE" \
  deployment/devshop

Kubernetes Service

Pod
 |
Service
 |
EndpointSlice

Check:

AWS_PROFILE="$AWS_PROFILE" kubectl get svc \
  devshop \
  -n "$NAMESPACE"

AWS_PROFILE="$AWS_PROFILE" kubectl get endpointslice \
  -n "$NAMESPACE"

PostgreSQL

Check:

AWS_PROFILE="$AWS_PROFILE" kubectl get statefulset \
  -n "$NAMESPACE"

AWS_PROFILE="$AWS_PROFILE" kubectl get pvc \
  -n "$NAMESPACE"

EBS

Check:

AWS_PROFILE="$AWS_PROFILE" kubectl get pv

Then inspect the CSI volume handle.
AWS networking

Only after Kubernetes connectivity is confirmed, investigate:

Client
  |
  v
Public Node IP
  |
  v
Security Group
  |
  v
NodePort
  |
  v
Kubernetes Service
  |
  v
Pod

Check:

    current public node IP

    current node security group

    NodePort

    security-group inbound rule

    subnet route table

    Internet Gateway

    Network ACL

23. Destroy the Development Environment

When finished with the AWS lab:

AWS_PROFILE="$AWS_PROFILE" eksctl delete cluster \
  --name "$CLUSTER_NAME" \
  --region "$AWS_REGION"

Before destroying the cluster, remember:

StorageClass reclaimPolicy = Delete

Therefore, the EBS-backed PostgreSQL volume may be deleted as part of the cluster/storage cleanup.

This environment should therefore be considered disposable.
24. Important Rebuild Lessons
Never hardcode ephemeral AWS IDs

Do not reuse values from a previous rebuild:

sg-xxxxxxxx
i-xxxxxxxx
vol-xxxxxxxx
eni-xxxxxxxx

Always rediscover them.
Never assume the NodePort

The Kubernetes Service may receive a different NodePort.

Discover it:

kubectl get svc devshop -n devshop

or:

kubectl get svc devshop \
  -n devshop \
  -o jsonpath='{.spec.ports[0].nodePort}'

Never assume the public node IP

Discover current nodes:

kubectl get nodes -o wide

or query EC2 directly.
Never commit credentials

Do not commit:

JWT_SECRET_KEY
DB_PASSWORD
AWS credentials
access tokens
private keys

Pod Identity and EBS CSI

The EBS CSI controller must have the correct AWS permissions.

If the CSI controller reports:

UnauthorizedOperation
ec2:DescribeAvailabilityZones

check:

    EBS CSI addon

    Pod Identity Agent

    Pod Identity association

    IAM role

    CSI controller pods

Restart the CSI controller after creating a missing Pod Identity association.
Kubernetes Secrets are namespace-scoped

If the application reports:

secret "devshop-secret" not found

check:

AWS_PROFILE="$AWS_PROFILE" kubectl get secret \
  devshop-secret \
  -n devshop

PostgreSQL lost+found

If PostgreSQL reports that its data directory is not empty because of:

lost+found

the EBS filesystem is mounted, but PostgreSQL is attempting to initialize directly at the filesystem root.

The long-term configuration should use a PostgreSQL data subdirectory.
25. Rebuild Sequence Summary

The complete rebuild sequence is:

AWS Login
    |
    v
Create EKS
    |
    v
Verify Nodes
    |
    v
Pod Identity Agent
    |
    v
EBS CSI Driver
    |
    v
Verify Pod Identity
    |
    v
Create Namespace
    |
    v
Create Application Secret
    |
    v
Deploy Kustomize AWS Overlay
    |
    v
Verify PVC / EBS
    |
    v
Verify PostgreSQL
    |
    v
Verify Migration
    |
    v
Discover NodePort
    |
    v
Discover Node Security Group
    |
    v
Discover Client Public IP
    |
    v
Authorize Temporary NodePort
    |
    v
Test Internal Connectivity
    |
    v
Test External Connectivity
    |
    v
Register Application User
    |
    v
Promote User
    |
    v
Create Test Product
    |
    v
Run PostgreSQL Persistence Test