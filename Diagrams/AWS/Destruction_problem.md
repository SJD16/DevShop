flowchart TB
    subgraph Terraform["Terraform"]
        VPC["VPC"]
        EKS["EKS Cluster"]
        Subnets["Subnets"]
    end

    subgraph Kubernetes["Kubernetes"]
        Argo["Argo CD"]
        Service["argocd-server<br/>Service: LoadBalancer"]
    end

    AWSLB["AWS Network Load Balancer"]
    ENI["AWS Network Interfaces"]

    VPC --> Subnets
    Subnets --> EKS

    EKS --> Argo
    Argo --> Service
    Service --> AWSLB
    AWSLB --> ENI
    ENI --> Subnets

    EKS -. "Terraform destroy" .-> X1["Cluster deleted"]
    X1 -.-> X2["Kubernetes controller unavailable"]
    X2 -.-> X3["NLB may remain"]
    X3 -.-> X4["Terraform attempts subnet/VPC deletion"]
    X4 -.-> X5["Dependency / deletion error"]
