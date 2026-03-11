# SSH key pair
resource "aws_key_pair" "deploy" {
  key_name   = "votovc-deploy"
  public_key = var.ssh_public_key
}

# Find latest Amazon Linux 2023 ARM64 AMI
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-arm64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# EC2 instance
resource "aws_instance" "app" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.deploy.key_name
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.app.id]

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
  }

  user_data = templatefile("${path.module}/user-data.sh", {
    db_password = var.db_password
    domain      = var.domain
  })

  tags = { Name = "votovc-app" }
}

# Elastic IP (stable public IP)
resource "aws_eip" "app" {
  instance = aws_instance.app.id
  domain   = "vpc"

  tags = { Name = "votovc-eip" }
}
