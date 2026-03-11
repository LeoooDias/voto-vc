# Route 53 hosted zone
resource "aws_route53_zone" "main" {
  name = var.domain
}

# Root domain -> CloudFront (A record alias)
resource "aws_route53_record" "root" {
  zone_id = aws_route53_zone.main.zone_id
  name    = var.domain
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.main.domain_name
    zone_id                = aws_cloudfront_distribution.main.hosted_zone_id
    evaluate_target_health = false
  }
}

# origin.voto.vc -> EC2 directly (used by CloudFront as origin)
resource "aws_route53_record" "origin" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "origin.${var.domain}"
  type    = "A"
  ttl     = 60
  records = [aws_eip.app.public_ip]
}

# www -> CloudFront (A record alias)
resource "aws_route53_record" "www" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "www.${var.domain}"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.main.domain_name
    zone_id                = aws_cloudfront_distribution.main.hosted_zone_id
    evaluate_target_health = false
  }
}
