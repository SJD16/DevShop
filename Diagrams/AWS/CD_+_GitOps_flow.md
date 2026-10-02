flowchart LR
    Developer["Developer"]

    GitHub["GitHub<br/>SJD16/DevShop"]

    subgraph Jenkins["Jenkins CI"]
        Checkout["Checkout source"]
        Python["Create Python venv"]
        Dependencies["Install dependencies"]
        TestDB["Start PostgreSQL"]
        Migrations["Run Alembic migrations"]
        Tests["Run pytest"]
        Build["Build Docker image"]
        Trivy["Trivy security scan"]
        Validate["Run container validation"]
        PushImage["Push image to Docker Hub"]
        Update["Update Kustomize image tag"]
        Kustomize["Validate Kustomize"]
        Commit["Commit GitOps change"]
        PushGit["Push to master"]
    end

    DockerHub["Docker Hub<br/>sjd16/devshop"]

    subgraph ArgoCD["Argo CD"]
        Detect["Detect Git change"]
        Sync["Automated Sync"]
        Apply["Apply Kubernetes manifests"]
        Health["Monitor application health"]
    end

    subgraph EKS["AWS EKS"]
        Deployment["DevShop Deployment"]
        Migration["Migration Job"]
        PostgreSQL["PostgreSQL StatefulSet"]
    end

    Developer -->|"git push"| GitHub

    GitHub --> Checkout
    Checkout --> Python
    Python --> Dependencies
    Dependencies --> TestDB
    TestDB --> Migrations
    Migrations --> Tests

    Tests --> Build
    Build --> Trivy
    Trivy --> Validate
    Validate --> PushImage

    PushImage --> DockerHub
    PushImage --> Update

    Update --> Kustomize
    Kustomize --> Commit
    Commit --> PushGit
    PushGit --> GitHub

    GitHub --> Detect
    Detect --> Sync
    Sync --> Apply

    Apply --> Deployment
    Apply --> Migration
    Apply --> PostgreSQL

    Deployment --> Health
    Migration --> Health
