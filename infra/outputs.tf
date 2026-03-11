output "instance_ip" {
  description = "Public IP of the EC2 instance"
  value       = aws_eip.app.public_ip
}

output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.app.id
}

output "nameservers" {
  description = "Route 53 nameservers (point your domain registrar here)"
  value       = aws_route53_zone.main.name_servers
}

output "ssh_command" {
  description = "SSH into the instance"
  value       = "ssh ec2-user@${aws_eip.app.public_ip}"
}

output "cloudfront_domain" {
  description = "CloudFront distribution domain"
  value       = aws_cloudfront_distribution.main.domain_name
}

output "cloudfront_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.main.id
}
