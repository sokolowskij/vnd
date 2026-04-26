variable "project_name" {
  description = "Name prefix for AWS resources."
  type        = string
  default     = "vnd"
}

variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "eu-central-1"
}

variable "repo_url" {
  description = "Git repository URL cloned by the EC2 bootstrap script."
  type        = string
  default     = "https://github.com/sokolowskij/vnd.git"
}

variable "repo_branch" {
  description = "Git branch to deploy."
  type        = string
  default     = "master"
}

variable "instance_type" {
  description = "EC2 instance type. t3.small is a practical low-cost default for Docker builds."
  type        = string
  default     = "t3.small"
}

variable "root_volume_size_gb" {
  description = "Root EBS volume size in GB."
  type        = number
  default     = 24
}

variable "ssh_public_key_path" {
  description = "Path to the SSH public key Terraform should register as an EC2 key pair."
  type        = string
  default     = "~/.ssh/vnd_aws.pub"
}

variable "ssh_private_key_path" {
  description = "Path to the matching SSH private key, used only to print the SSH command output."
  type        = string
  default     = "~/.ssh/vnd_aws"
}

variable "admin_cidr_blocks" {
  description = "CIDR blocks allowed to SSH into the instance. Use your public IP as x.x.x.x/32."
  type        = list(string)
}

variable "reviewer_cidr_blocks" {
  description = "CIDR blocks allowed to access the Streamlit dashboard on port 8501."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "expose_backend_api" {
  description = "Whether to expose FastAPI port 8000 publicly through the security group."
  type        = bool
  default     = false
}
