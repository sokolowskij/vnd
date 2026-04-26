locals {
  common_tags = {
    Project   = var.project_name
    ManagedBy = "terraform"
  }
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_key_pair" "this" {
  key_name   = "${var.project_name}-deploy-key"
  public_key = file(pathexpand(var.ssh_public_key_path))

  tags = local.common_tags
}

resource "aws_security_group" "this" {
  name        = "${var.project_name}-web"
  description = "Security group for VND dashboard host"

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.admin_cidr_blocks
  }

  ingress {
    description = "Streamlit dashboard"
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = var.reviewer_cidr_blocks
  }

  dynamic "ingress" {
    for_each = var.expose_backend_api ? [1] : []

    content {
      description = "FastAPI backend"
      from_port   = 8000
      to_port     = 8000
      protocol    = "tcp"
      cidr_blocks = var.reviewer_cidr_blocks
    }
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}

resource "aws_instance" "this" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.this.key_name
  vpc_security_group_ids = [aws_security_group.this.id]

  user_data = templatefile("${path.module}/templates/cloud-init.yml.tftpl", {
    repo_url    = var.repo_url
    repo_branch = var.repo_branch
  })

  root_block_device {
    volume_size = var.root_volume_size_gb
    volume_type = "gp3"
    encrypted   = true
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-dashboard"
  })
}
