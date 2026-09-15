OWASP ZAP — Dynamic Application Security Testing

This directory documents the OWASP ZAP Dynamic Application Security Testing (DAST) procedure used against the running DevShop application in Kubernetes.

ZAP is intentionally run as a temporary Kubernetes pod rather than as a Jenkins pipeline stage.
Purpose

The objective is to demonstrate dynamic security testing against the deployed DevShop application:

Argo CD
   ↓
Kubernetes
   ↓
Running DevShop
   ↓
OWASP ZAP
   ↓
DAST Report

This complements the other DevSecOps controls in the project:

Dependency Security → OWASP Dependency-Check
Container Security  → Trivy
Dynamic Security    → OWASP ZAP
SAST                → SonarQube (deferred)

Why ZAP Runs Separately

The available Argo CD/Kubernetes playground provides CLI access to the Kubernetes control plane, but does not provide a convenient browser-based environment for using the ZAP GUI.

The Kubernetes node also does not have Docker or Java installed directly.

Instead, ZAP is executed inside a Kubernetes pod using the official:

zaproxy/zap-stable

container image.

This allows the ZAP container to communicate with DevShop through the Kubernetes Service:

http://devshop:8000

No external exposure of DevShop is required for the scan.
Prerequisites

The Kubernetes environment must have:

    A running DevShop deployment
    The devshop Kubernetes Service
    kubectl access
    Permission to create pods in the devshop namespace

Verify the application first:

kubectl get pods -n devshop
kubectl get svc -n devshop

Example:

NAME       TYPE       PORT(S)
devshop    NodePort   8000:31686/TCP

The NodePort is not required by ZAP because the scan runs inside the cluster.
1. Create the Temporary ZAP Pod

Create zap.yaml:

apiVersion: v1
kind: Pod
metadata:
  name: zap
  namespace: devshop
spec:
  containers:
    - name: zap
      image: zaproxy/zap-stable
      command:
        - sleep
        - "infinity"
      volumeMounts:
        - name: zap-work
          mountPath: /zap/wrk
  volumes:
    - name: zap-work
      emptyDir: {}

Apply it:

kubectl apply -f zap.yaml

Verify that the pod is running:

kubectl get pod zap -n devshop

Expected state:

zap    1/1    Running

Why /zap/wrk is mounted

The ZAP Docker image uses /zap/wrk as a working directory for generated reports.

The emptyDir volume provides writable temporary storage for:

zap-report.html
zap-report.json

Without a writable working directory, ZAP's report generation can fail.
2. Verify DevShop

Confirm the application is running:

kubectl get pods -n devshop

For example:

devshop-xxxxxxxxxx-xxxxx       1/1   Running
devshop-migration-xxxxx        0/1   Completed
devshop-postgres-xxxxxxxxxx    1/1   Running

Test the application through the Kubernetes Service from the control plane:

curl http://127.0.0.1:<NODEPORT>

Example:

curl http://127.0.0.1:31686

Expected:

{"message":"DevShop is working!"}

Also test:

curl http://127.0.0.1:<NODEPORT>/products

Expected:

[]

3. Verify ZAP → DevShop Connectivity

Before running the security scan, verify that the ZAP pod can reach DevShop through the Kubernetes DNS Service.

Run:

kubectl exec -n devshop zap -- \
  curl -fsS http://devshop:8000/

Expected:

{"message":"DevShop is working!"}

Also verify the products endpoint:

kubectl exec -n devshop zap -- \
  curl -fsS http://devshop:8000/products

Expected:

[]

This confirms:

ZAP Pod
   ↓
Kubernetes DNS
   ↓
devshop Service
   ↓
DevShop Pod
   ↓
FastAPI

At this point ZAP can reach the application without requiring the NodePort.
4. Run the ZAP Baseline Scan

Run the scan from inside the ZAP pod:

kubectl exec -n devshop zap -- sh -c '
cd /zap/wrk &&
zap-baseline.py \
  -t http://devshop:8000 \
  -r zap-report.html \
  -J zap-report.json
'

Important detail

The command changes directory first:

cd /zap/wrk

The report filenames are then specified as relative paths:

-r zap-report.html
-J zap-report.json

This is important with the ZAP Docker image's Automation Framework.

Using:

-r /zap/wrk/zap-report.html

can cause the generated Automation Framework plan to resolve the path incorrectly in this environment.

The working approach was therefore:

cd /zap/wrk

followed by:

-r zap-report.html
-J zap-report.json

5. Review the Scan Output

A successful scan produces output similar to:

Total of 3 URLs

PASS: Vulnerable JS Library (Powered by Retire.js) [10003]
PASS: In Page Banner Information Leak [10009]
...

WARN-NEW: X-Content-Type-Options Header Missing [10021] x 1
WARN-NEW: Storable and Cacheable Content [10049] x 3
WARN-NEW: Cross-Origin-Resource-Policy Header Missing or Invalid [90004] x 1

FAIL-NEW: 0
WARN-NEW: 3
INFO: 0
PASS: 64

The baseline scan demonstrated:

High:          0
Medium:        0
Low:           2
Informational: 1
False Positives: 0

The exact findings and counts may change between scans depending on the ZAP version, rules, application responses, and discovered URLs.
6. Verify the Generated Reports

Check the ZAP working directory:

kubectl exec -n devshop zap -- \
  ls -lah /zap/wrk/

Expected files include:

zap-report.html
zap-report.json

For example:

-rw-r--r-- 1 zap zap 33K zap-report.html
-rw-r--r-- 1 zap zap 8.6K zap-report.json

The HTML report is intended for human review.

The JSON report provides machine-readable scan results.
7. Copy the Reports Out of Kubernetes

The reports exist inside the temporary pod, so copy them to the control-plane machine:

kubectl cp \
  devshop/zap:/zap/wrk/zap-report.html \
  ./zap-report.html

And:

kubectl cp \
  devshop/zap:/zap/wrk/zap-report.json \
  ./zap-report.json

Verify:

ls -lh zap-report.html zap-report.json

The reports can then be downloaded or preserved as portfolio evidence.
8. Optional: Inspect the JSON Report

The JSON report can be inspected directly:

cat zap-report.json

If jq is available:

jq . zap-report.json

The JSON format is useful for extracting findings programmatically.
9. Remove the Temporary ZAP Pod

ZAP is not intended to remain permanently deployed in this playground.

After the scan and report extraction:

kubectl delete pod zap -n devshop

Verify:

kubectl get pods -n devshop

Only the normal DevShop workloads should remain.
Complete Workflow

The complete demonstrated workflow is:

1. Verify Kubernetes
       ↓
2. Verify DevShop
       ↓
3. Deploy temporary ZAP pod
       ↓
4. Mount /zap/wrk
       ↓
5. Verify ZAP → DevShop connectivity
       ↓
6. Run zap-baseline.py
       ↓
7. Generate HTML + JSON reports
       ↓
8. Copy reports from pod
       ↓
9. Preserve evidence
       ↓
10. Delete temporary ZAP pod

Evidence

The important evidence produced by this exercise is:

OWASP ZAP
    ↓
Baseline DAST scan
    ↓
Running Kubernetes DevShop
    ↓
HTML report
    ↓
JSON report

The generated reports are artifacts, not application source code.

They should generally not be committed to the main DevShop repository because:

    vulnerability results can become outdated;
    ZAP rules and versions can change;
    reports are generated
