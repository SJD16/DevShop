flowchart TB
    App["DevShop Application"]

    Service["devshop-postgres<br/>ClusterIP"]

    StatefulSet["PostgreSQL StatefulSet<br/>replicas: 1"]

    PVC["PersistentVolumeClaim<br/>5Gi"]

    SC["StorageClass<br/>devshop-gp3"]

    CSI["AWS EBS CSI Driver"]

    EBS["AWS EBS gp3 Volume"]

    NewPod["New PostgreSQL Pod"]

    App -->|"DATABASE_URL"| Service
    Service --> StatefulSet

    StatefulSet --> PVC
    PVC --> SC
    SC --> CSI
    CSI --> EBS

    StatefulSet -. "Pod deleted" .-> NewPod
    NewPod --> PVC
    PVC --> EBS

    EBS -. "Existing database data" .-> NewPod
