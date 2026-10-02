flowchart TB
    Internet((Internet))

    subgraph AWS["AWS - us-east-1"]
        subgraph VPC["VPC 10.0.0.0/16"]

            subgraph Public["Public Subnets"]
                subnetA["us-east-1a<br/>10.0.1.0/24"]
                subnetB["us-east-1b<br/>10.0.2.0/24"]

                nodeA["EKS Node<br/>10.0.1.158"]
                nodeB["EKS Node<br/>10.0.2.37"]
            end

            subgraph EKS["EKS Cluster: devshop-eks"]
                subgraph Argo["argocd namespace"]
                    nlb["AWS Network Load Balancer"]
                    argocd["Argo CD Server<br/>Service: LoadBalancer"]
                end

                subgraph DevShop["devshop namespace"]
                    appSvc["DevShop Service<br/>NodePort :30929"]
                    app["DevShop Deployment<br/>FastAPI"]
                    migration["Migration Job"]
                    postgresSvc["PostgreSQL Service<br/>ClusterIP"]
                    postgres["PostgreSQL StatefulSet"]
                    pvc["PVC<br/>5 GiB"]
                end

                subgraph System["kube-system"]
                    csi["Secrets Store CSI Driver"]
                    podIdentity["EKS Pod Identity Agent"]
                    ebs["AWS EBS CSI Driver"]
                end
            end

            subgraph AWSStorage["AWS Storage"]
                ebsVolume["EBS gp3 Volume"]
            end

            subgraph Secrets["AWS Secrets Manager"]
                secret["devshop/devshop"]
            end
        end
    end

    Internet -->|"HTTPS / HTTP"| nlb
    nlb --> argocd

    Internet -->|"NodePort :30929"| appSvc
    appSvc --> app

    app -->|"TCP :5432"| postgresSvc
    postgresSvc --> postgres

    postgres --> pvc
    pvc -->|"EBS CSI"| ebsVolume

    app -->|"SecretProviderClass"| csi
    migration -->|"SecretProviderClass"| csi
    postgres -->|"SecretProviderClass"| csi

    csi -->|"GetSecretValue"| secret
    csi -->|"Pod Identity"| podIdentity

    ebs --> ebsVolume

    subnetA --- nodeA
    subnetB --- nodeB

    nodeA --- EKS
    nodeB --- EKS
