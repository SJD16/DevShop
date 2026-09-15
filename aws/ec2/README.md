DevShop AWS EC2 Deployment
==========================

Date:
2026-09-15

Region:
us-east-1

Purpose:
Minimal AWS deployment of the existing DevShop application.

Architecture:

Internet
   |
   v
EC2
   |
   +-- Docker
   |     |
   |     +-- DevShop FastAPI
   |     |
   |     +-- PostgreSQL
   |
   +-- SSM Session Manager

Application:

Docker image:
sjd16/devshop:94010f6

Git commit associated with deployed image:
94010f6

Verification:

GET /
    HTTP 200

GET /products
    HTTP 200
    []

GET /docs
    Swagger UI available

Alembic:
    4aa138998147 (head)

Security:

EC2 access:
    AWS Systems Manager Session Manager

Application:
    TCP 8000

PostgreSQL:
    Not exposed through the EC2 security group

Instance:
    t3.small

AMI:
    Ubuntu 24.04
