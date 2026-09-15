#!/usr/bin/env bash

# DevShop AWS EC2 deployment
# Region: us-east-1
# Purpose: Minimal AWS learning deployment
#
# WARNING:
# This file documents the commands used during the initial deployment.
# Review resource IDs and parameters before executing.
#
# AWS profile:
PROFILE="devshop"
REGION="us-east-1"

# -------------------------------------------------------------------
# 1. Verify AWS identity
# -------------------------------------------------------------------

aws sts get-caller-identity \
  --profile "$PROFILE"

aws configure list \
  --profile "$PROFILE"

# -------------------------------------------------------------------
# 2. Inspect default VPC/subnet
# -------------------------------------------------------------------

aws ec2 describe-vpcs \
  --profile "$PROFILE" \
  --region "$REGION" \
  --filters "Name=is-default,Values=true"

aws ec2 describe-subnets \
  --profile "$PROFILE" \
  --region "$REGION" \
  --filters "Name=default-for-az,Values=true"

# -------------------------------------------------------------------
# 3. Security group
# -------------------------------------------------------------------

SECURITY_GROUP_ID="sg-0208a1af1722a554c"

aws ec2 describe-security-groups \
  --profile "$PROFILE" \
  --region "$REGION" \
  --group-ids "$SECURITY_GROUP_ID"

# -------------------------------------------------------------------
# 4. IAM instance profile
# -------------------------------------------------------------------

aws iam get-instance-profile \
  --profile "$PROFILE" \
  --instance-profile-name DevShopEC2Profile

# -------------------------------------------------------------------
# 5. Launch EC2
# -------------------------------------------------------------------
#
# See the deployment command recorded in Git history/checkpoint.
#
# Important:
# - Review AMI ID
# - Review subnet
# - Review security group
# - Review instance profile
# - Review user-data file
# - Review instance type
#
# Example structure:
#
# aws ec2 run-instances \
#   --profile "$PROFILE" \
#   --region "$REGION" \
#   --image-id "ami-025d99823a4caad37" \
#   --instance-type "t3.small" \
#   --subnet-id "subnet-00f106f3b530dbae9" \
#   --security-group-ids "$SECURITY_GROUP_ID" \
#   --iam-instance-profile Name=DevShopEC2Profile \
#   --user-data file://user-data.sh

# -------------------------------------------------------------------
# 6. Verify instance
# -------------------------------------------------------------------

INSTANCE_ID="i-08faa28ab439d3c1c"

aws ec2 describe-instances \
  --profile "$PROFILE" \
  --region "$REGION" \
  --instance-ids "$INSTANCE_ID"

# -------------------------------------------------------------------
# 7. Verify SSM
# -------------------------------------------------------------------

aws ssm describe-instance-information \
  --profile "$PROFILE" \
  --region "$REGION"

# -------------------------------------------------------------------
# 8. Start SSM session
# -------------------------------------------------------------------

aws ssm start-session \
  --profile "$PROFILE" \
  --region "$REGION" \
  --target "$INSTANCE_ID"
