flowchart LR
    User((User))

    subgraph AWS["AWS"]
        subgraph EKS["EKS: devshop-eks"]
            NodePort["DevShop NodePort<br/>:30929"]

            App["DevShop<br/>FastAPI :8000"]

            DBService["devshop-postgres<br/>ClusterIP :5432"]
            PostgreSQL["PostgreSQL :5432"]

            PVC["PVC"]
            EBS["EBS gp3"]
        end
    end

    User -->|"HTTP"| NodePort
    NodePort --> App
    App -->|"SQL"| DBService
    DBService --> PostgreSQL
    PostgreSQL --> PVC
    PVC --> EBS
