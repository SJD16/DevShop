module "vpc" {
  source = "../../modules/vpc"

  name = "devshop-dev"

  vpc_cidr = "10.0.0.0/16"

  availability_zones = [
    "us-east-1a",
    "us-east-1b"
  ]

  public_subnet_cidrs = [
    "10.0.1.0/24",
    "10.0.2.0/24"
  ]
  private_subnet_cidrs = [
    "10.0.11.0/24",
    "10.0.12.0/24"
  ]

  tags = {
    Project     = "DevShop"
    Environment = "dev"
    ManagedBy   = "Terraform"
  }
}

module "eks" {
  source = "../../modules/eks"

  cluster_name    = "devshop-eks"
  cluster_version = "1.36"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.public_subnet_ids

  node_group_name = "devshop-ng"

  node_instance_types = ["t3.medium"]

  node_desired_size = 2
  node_min_size     = 2
  node_max_size     = 3

  node_disk_size = 20

  tags = {
    Project     = "DevShop"
    Environment = "dev"
    ManagedBy   = "Terraform"
  }
}
