# VND Terraform Deployment

This provisions a single low-cost EC2 host for the reviewer dashboard:

- Ubuntu 24.04 in `eu-central-1` by default
- Docker Engine and Docker Compose plugin
- VND cloned from GitHub
- `docker compose up -d --build`
- Streamlit dashboard exposed on port `8501`
- FastAPI kept private by default

## 1. Prerequisites

Install Terraform and configure AWS credentials locally:

```bash
aws configure
terraform -version
```

Create an SSH key for the instance:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/vnd_aws -C "vnd-aws"
```

## 2. Configure

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and replace:

```hcl
admin_cidr_blocks = ["YOUR_PUBLIC_IP/32"]
```

You can get your public IP with:

```bash
curl https://checkip.amazonaws.com
```

## 3. Deploy

```bash
terraform init
terraform plan
terraform apply
```

Terraform prints `dashboard_url` when it finishes. The app may still build for a few minutes after the EC2 instance appears.

## 4. Check The Server

SSH into the host:

```bash
ssh -i ~/.ssh/vnd_aws ubuntu@<instance_public_ip>
```

Useful commands:

```bash
sudo tail -f /var/log/vnd-bootstrap.log
cd /opt/vnd
docker compose ps
docker compose logs -f
```

## 5. Tear Down

```bash
terraform destroy
```

Note: `.env` is created from `.env.example` on the server. Do not put real API keys into Terraform variables unless you are comfortable with them being stored in Terraform state.
