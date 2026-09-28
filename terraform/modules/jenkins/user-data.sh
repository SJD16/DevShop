#!/bin/bash
set -euxo pipefail

exec > >(tee -a /var/log/jenkins-bootstrap.log | logger -t jenkins-bootstrap -s 2>/dev/console) 2>&1

echo "===== DevShop Jenkins bootstrap started ====="

export DEBIAN_FRONTEND=noninteractive

# --------------------------------------------------
# System packages
# --------------------------------------------------

apt-get update

apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    unzip \
    git \
    fontconfig \
    openjdk-21-jre
    python3-venv

# --------------------------------------------------
# Docker
# --------------------------------------------------

install -m 0755 -d /etc/apt/keyrings

curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    -o /etc/apt/keyrings/docker.asc

chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update

apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

systemctl enable --now docker

# --------------------------------------------------
# Jenkins
# --------------------------------------------------

curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2026.key \
    -o /usr/share/keyrings/jenkins-keyring.asc

echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] \
https://pkg.jenkins.io/debian-stable binary/" \
    > /etc/apt/sources.list.d/jenkins.list

apt-get update

apt-get install -y jenkins

systemctl enable jenkins
systemctl start jenkins

# Jenkins needs Docker access.
usermod -aG docker jenkins

systemctl restart jenkins

# --------------------------------------------------
# AWS CLI
# --------------------------------------------------

curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" \
    -o /tmp/awscliv2.zip

unzip -q /tmp/awscliv2.zip -d /tmp

/tmp/aws/install

rm -rf /tmp/aws /tmp/awscliv2.zip

# --------------------------------------------------
# kubectl
# --------------------------------------------------

KUBECTL_VERSION="$(curl -L -s https://dl.k8s.io/release/stable.txt)"

curl -LO \
    "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl"

install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

rm kubectl

# --------------------------------------------------
# Trivy
# --------------------------------------------------

TRIVY_VERSION="$(curl -s https://api.github.com/repos/aquasecurity/trivy/releases/latest \
    | grep '"tag_name":' \
    | head -1 \
    | cut -d '"' -f4)"

curl -LO \
    "https://github.com/aquasecurity/trivy/releases/download/${TRIVY_VERSION}/trivy_${TRIVY_VERSION#v}_Linux-64bit.tar.gz"

tar -xzf "trivy_${TRIVY_VERSION#v}_Linux-64bit.tar.gz" trivy

install -m 0755 trivy /usr/local/bin/trivy

rm -f trivy "trivy_${TRIVY_VERSION#v}_Linux-64bit.tar.gz"

# --------------------------------------------------
# Verification
# --------------------------------------------------

echo "Java:"
java -version

echo "Docker:"
docker --version

echo "Jenkins:"
systemctl --no-pager --full status jenkins || true

echo "AWS CLI:"
aws --version

echo "kubectl:"
kubectl version --client

echo "Trivy:"
trivy --version

echo "===== DevShop Jenkins bootstrap completed ====="
