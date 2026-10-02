flowchart TB
    Terraform["Terraform"]

    subgraph AWS["AWS"]
        VPC["VPC<br/>10.0.0.0/16"]

        PublicA["Public Subnet<br/>10.0.1.0/24"]
        PublicB["Public Subnet<br/>10.0.2.0/24"]

        EKS["EKS Cluster<br/>devshop-eks"]

        Nodes["Managed Node Group<br/>devshop-ng<br/>2-3 × t3.medium"]

        PodIdentity["EKS Pod Identity Agent"]

        EBSCSI["AWS EBS CSI Driver"]

        Secrets["Secrets Manager<br/>devshop/devshop"]

        IAMSecrets["IAM Role<br/>devshop-secrets"]

        IAMCSI["IAM Role<br/>ebs-csi"]

        Jenkins["EC2<br/>Jenkins"]
    end

    Terraform --> VPC
    Terraform --> EKS
    Terraform --> Nodes
    Terraform --> Secrets
    Terraform --> IAMSecrets
    Terraform --> IAMCSI
    Terraform --> Jenkins

    VPC --> PublicA
    VPC --> PublicB

    PublicA --> Nodes
    PublicB --> Nodes

    EKS --> Nodes
    EKS --> PodIdentity
    EKS --> EBSCSI

    IAMSecrets --> Secrets
    IAMCSI --> EBSCSI
