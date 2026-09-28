variable "name" {
  description = "Name of the Jenkins EC2 instance"
  type        = string
  default     = "devshop-jenkins"
}

variable "ami_id" {
  description = "AMI ID for the Jenkins EC2 instance"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type for Jenkins"
  type        = string
  default     = "t3.small"
}

variable "subnet_id" {
  description = "Public subnet ID for the Jenkins instance"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for the Jenkins security group"
  type        = string
}

variable "instance_profile_name" {
  description = "Existing IAM instance profile used by Jenkins"
  type        = string
  default     = "DevShopEC2Profile"
}

variable "tags" {
  description = "Tags applied to Jenkins resources"
  type        = map(string)
  default     = {}
}
