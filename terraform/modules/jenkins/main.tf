data "aws_iam_instance_profile" "jenkins" {
  name = var.instance_profile_name
}

resource "aws_security_group" "jenkins" {
  name        = "${var.name}-sg"
  description = "Security group for DevShop Jenkins"
  vpc_id      = var.vpc_id

  ingress {
    description = "Jenkins web interface"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow outbound internet access"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.name}-sg"
    }
  )
}

resource "aws_instance" "jenkins" {
  ami                         = var.ami_id
  instance_type               = var.instance_type
  subnet_id                   = var.subnet_id
  vpc_security_group_ids      = [aws_security_group.jenkins.id]
  associate_public_ip_address = true
  iam_instance_profile        = data.aws_iam_instance_profile.jenkins.name

  user_data = file("${path.module}/user-data.sh")

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
    encrypted   = true
  }

  tags = merge(
    var.tags,
    {
      Name = var.name
    }
  )
}
