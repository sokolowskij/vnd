output "dashboard_url" {
  description = "Reviewer-facing Streamlit dashboard URL."
  value       = "http://${aws_instance.this.public_ip}:8501"
}

output "backend_health_url" {
  description = "Backend health URL. The security group exposes this only if expose_backend_api=true."
  value       = "http://${aws_instance.this.public_ip}:8000/health"
}

output "ssh_command" {
  description = "SSH command for administering the instance."
  value       = "ssh -i ${pathexpand(var.ssh_private_key_path)} ubuntu@${aws_instance.this.public_ip}"
}

output "instance_public_ip" {
  description = "Public IP of the VND EC2 instance."
  value       = aws_instance.this.public_ip
}
