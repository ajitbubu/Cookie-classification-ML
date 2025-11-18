# SSL/TLS Configuration Guide

This document provides comprehensive guidance on configuring SSL/TLS for the Cookie Scanner Platform to ensure secure communication.

## Overview

The platform enforces HTTPS/TLS for:
- API endpoints
- Dashboard access
- Database connections
- External service integrations

## Production SSL/TLS Setup

### Option 1: Let's Encrypt (Recommended for most deployments)

Let's Encrypt provides free SSL certificates with automatic renewal.

#### Using Certbot

```bash
# Install Certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d api.example.com -d dashboard.example.com

# Test automatic renewal
sudo certbot renew --dry-run
```

#### Certificate locations:
- Certificate: `/etc/letsencrypt/live/api.example.com/fullchain.pem`
- Private key: `/etc/letsencrypt/live/api.example.com/privkey.pem`

### Option 2: Commercial SSL Certificate

#### Generate CSR (Certificate Signing Request)

```bash
# Generate private key and CSR
openssl req -new -newkey rsa:2048 -nodes \
  -keyout server.key \
  -out server.csr \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=api.example.com"

# Submit CSR to certificate authority
# Download signed certificate and intermediate certificates
```

### Option 3: Self-Signed Certificate (Development only)

```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout server.key \
  -out server.crt \
  -days 365 \
  -subj "/CN=localhost"

# Set permissions
chmod 600 server.key
chmod 644 server.crt
```

## Application Configuration

### FastAPI with Uvicorn

#### Method 1: Uvicorn with SSL

```bash
# Run with SSL
uvicorn api.main:app \
  --host 0.0.0.0 \
  --port 443 \
  --ssl-keyfile=/path/to/privkey.pem \
  --ssl-certfile=/path/to/fullchain.pem
```

#### Method 2: Environment Variables

```bash
# .env file
SSL_KEYFILE=/etc/letsencrypt/live/api.example.com/privkey.pem
SSL_CERTFILE=/etc/letsencrypt/live/api.example.com/fullchain.pem
HTTPS_REDIRECT_ENABLED=true
```

#### Method 3: Configuration in code

```python
# run_api.py
import uvicorn
from core.config import get_config

if __name__ == "__main__":
    config = get_config()
    
    uvicorn_config = {
        "app": "api.main:app",
        "host": "0.0.0.0",
        "port": 443,
        "workers": 4,
    }
    
    # Add SSL configuration if certificates are available
    if config.ssl.enabled:
        uvicorn_config.update({
            "ssl_keyfile": config.ssl.keyfile,
            "ssl_certfile": config.ssl.certfile,
        })
    
    uvicorn.run(**uvicorn_config)
```

### Enable HTTPS Redirect Middleware

```python
# api/main.py
from fastapi import FastAPI
from api.middleware.https_redirect import HTTPSRedirectMiddleware, SecurityHeadersMiddleware
from core.config import get_config

app = FastAPI()
config = get_config()

# Add HTTPS redirect middleware (production only)
if config.environment == "production":
    app.add_middleware(
        HTTPSRedirectMiddleware,
        enabled=True,
        exclude_paths=['/health', '/api/v1/health']
    )
    
    # Add security headers
    app.add_middleware(
        SecurityHeadersMiddleware,
        hsts_max_age=31536000,  # 1 year
        hsts_include_subdomains=True,
        hsts_preload=False
    )
```

### Secure Cookie Configuration

```python
# api/auth/dependencies.py
from fastapi import Response

def set_secure_cookie(response: Response, name: str, value: str, max_age: int = 3600):
    """Set a secure cookie with proper security flags."""
    response.set_cookie(
        key=name,
        value=value,
        max_age=max_age,
        httponly=True,      # Prevent JavaScript access
        secure=True,        # HTTPS only
        samesite='strict',  # CSRF protection
        domain=None,        # Current domain only
        path='/'
    )
```

## Reverse Proxy Configuration

### Nginx

```nginx
# /etc/nginx/sites-available/cookie-scanner

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name api.example.com dashboard.example.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name api.example.com;
    
    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/api.example.com/chain.pem;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;
    
    # Proxy to FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

# Dashboard server
server {
    listen 443 ssl http2;
    server_name dashboard.example.com;
    
    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/dashboard.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dashboard.example.com/privkey.pem;
    
    # SSL configuration (same as above)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    
    # Proxy to Next.js
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Apache

```apache
# /etc/apache2/sites-available/cookie-scanner.conf

<VirtualHost *:80>
    ServerName api.example.com
    Redirect permanent / https://api.example.com/
</VirtualHost>

<VirtualHost *:443>
    ServerName api.example.com
    
    # SSL configuration
    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/api.example.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/api.example.com/privkey.pem
    
    # SSL protocols and ciphers
    SSLProtocol all -SSLv3 -TLSv1 -TLSv1.1
    SSLCipherSuite ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256
    SSLHonorCipherOrder off
    
    # HSTS
    Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
    
    # Security headers
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-Frame-Options "DENY"
    Header always set X-XSS-Protection "1; mode=block"
    
    # Proxy to FastAPI
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/
    
    # Set forwarded headers
    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-Port "443"
</VirtualHost>
```

## CORS Configuration for Production

```python
# api/main.py
from fastapi.middleware.cors import CORSMiddleware

# Production CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://dashboard.example.com",
        "https://app.example.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
    max_age=3600
)
```

## Docker Configuration

### Docker Compose with SSL

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "443:443"
    volumes:
      - /etc/letsencrypt:/etc/letsencrypt:ro
    environment:
      - SSL_KEYFILE=/etc/letsencrypt/live/api.example.com/privkey.pem
      - SSL_CERTFILE=/etc/letsencrypt/live/api.example.com/fullchain.pem
      - HTTPS_REDIRECT_ENABLED=true
    command: >
      uvicorn api.main:app
      --host 0.0.0.0
      --port 443
      --ssl-keyfile=/etc/letsencrypt/live/api.example.com/privkey.pem
      --ssl-certfile=/etc/letsencrypt/live/api.example.com/fullchain.pem
```

## Testing SSL/TLS Configuration

### Test SSL Certificate

```bash
# Check certificate details
openssl s_client -connect api.example.com:443 -servername api.example.com

# Check certificate expiration
echo | openssl s_client -connect api.example.com:443 2>/dev/null | \
  openssl x509 -noout -dates

# Verify certificate chain
openssl s_client -connect api.example.com:443 -showcerts
```

### Test SSL Configuration

```bash
# Test with curl
curl -v https://api.example.com/api/v1/health

# Test HTTPS redirect
curl -v http://api.example.com/api/v1/health

# Test with specific TLS version
curl --tlsv1.2 https://api.example.com/api/v1/health
curl --tlsv1.3 https://api.example.com/api/v1/health
```

### SSL Labs Test

Visit [SSL Labs](https://www.ssllabs.com/ssltest/) and test your domain for SSL/TLS configuration quality.

### Test Security Headers

```bash
# Check security headers
curl -I https://api.example.com/api/v1/health

# Should include:
# Strict-Transport-Security: max-age=31536000; includeSubDomains
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# X-XSS-Protection: 1; mode=block
```

## Certificate Renewal

### Automatic Renewal (Let's Encrypt)

```bash
# Certbot automatically renews certificates
# Test renewal process
sudo certbot renew --dry-run

# Check renewal timer
sudo systemctl status certbot.timer

# Manual renewal if needed
sudo certbot renew
```

### Renewal Notification

```bash
# Add renewal hook to restart services
sudo nano /etc/letsencrypt/renewal-hooks/deploy/restart-services.sh

#!/bin/bash
systemctl reload nginx
systemctl restart cookie-scanner-api

# Make executable
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/restart-services.sh
```

## Troubleshooting

### Certificate Not Trusted

**Problem**: Browser shows "Certificate not trusted" error

**Solutions**:
- Ensure certificate chain is complete (include intermediate certificates)
- Check certificate is not expired
- Verify domain name matches certificate CN/SAN
- For self-signed certificates, add to browser trust store

### Mixed Content Warnings

**Problem**: HTTPS page loading HTTP resources

**Solutions**:
- Update all resource URLs to use HTTPS
- Use protocol-relative URLs (`//example.com/resource`)
- Configure Content Security Policy to block mixed content

### HSTS Issues

**Problem**: Cannot access site after HSTS is enabled

**Solutions**:
- Clear HSTS cache in browser (chrome://net-internals/#hsts)
- Ensure certificate is valid before enabling HSTS
- Start with shorter max-age for testing

## Security Best Practices

1. **Use TLS 1.2 or higher**: Disable SSLv3, TLS 1.0, and TLS 1.1
2. **Strong cipher suites**: Use modern, secure cipher suites
3. **Enable HSTS**: Force HTTPS for all connections
4. **Certificate pinning**: Consider for mobile apps
5. **Regular updates**: Keep SSL/TLS libraries updated
6. **Monitor expiration**: Set up alerts for certificate expiration
7. **Use CAA records**: Specify which CAs can issue certificates for your domain

## Environment-Specific Configuration

### Development

```bash
# .env.development
HTTPS_REDIRECT_ENABLED=false
SECURE_COOKIES=false
SSL_KEYFILE=
SSL_CERTFILE=
```

### Staging

```bash
# .env.staging
HTTPS_REDIRECT_ENABLED=true
SECURE_COOKIES=true
SSL_KEYFILE=/etc/letsencrypt/live/staging.example.com/privkey.pem
SSL_CERTFILE=/etc/letsencrypt/live/staging.example.com/fullchain.pem
```

### Production

```bash
# .env.production
HTTPS_REDIRECT_ENABLED=true
SECURE_COOKIES=true
HSTS_ENABLED=true
HSTS_MAX_AGE=31536000
SSL_KEYFILE=/etc/letsencrypt/live/api.example.com/privkey.pem
SSL_CERTFILE=/etc/letsencrypt/live/api.example.com/fullchain.pem
```

## References

- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [OWASP Transport Layer Protection](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html)
- [SSL Labs Best Practices](https://github.com/ssllabs/research/wiki/SSL-and-TLS-Deployment-Best-Practices)
