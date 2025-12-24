# Optional CDN/WAF Integration

This service can be fronted by a CDN/WAF to reduce origin exposure and add DDoS protection.

## Cloudflare (example)
1. Set DNS `A/AAAA` for `APP_DOMAIN` to the edge host.
2. Enable WAF (managed rules + bot protection).
3. Enable TLS mode "Full (strict)".
4. Add an origin access rule to only allow Cloudflare IP ranges to the host.
5. Configure cache for static assets if desired.

## AWS CloudFront + WAF (example)
1. Create a CloudFront distribution with the Caddy edge as origin.
2. Attach AWS WAF with managed rules and rate limiting.
3. Use an ACM certificate for `APP_DOMAIN`.
4. Restrict the origin security group to CloudFront IP ranges.

## Origin Hardening
- Keep ports 80/443 open only to CDN/WAF IP ranges.
- Configure Caddy to trust the reverse proxy headers for real client IPs.
