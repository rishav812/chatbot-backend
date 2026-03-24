# Deployment Steps for FastAPI Chatbot Backend on AWS EC2

This document outlines the exact steps taken to deploy the FastAPI backend onto an AWS EC2 instance, serving it via a custom domain name with a secure HTTPS connection using Nginx and Let's Encrypt.

## Prerequisites / Requirements
- AWS EC2 instance (Ubuntu 24.04/22.04)
- Port `80` (HTTP), Port `443` (HTTPS), and Port `22` (SSH) open in the EC2 Security Group.
- Port `8000` for the internal FastAPI app (does not need to be public after Nginx is configured, but useful for testing).
- Docker & Docker Compose installed on the server.

---

## 1. Docker Compose Setup

Initially, running `docker compose` or `docker-compose` threw errors based on version incompatibilities with modern Docker engines. 

**Problem 1:** `docker compose` (v2 plugin) wasn't installed natively.
**Problem 2:** Running the pre-installed `docker-compose` (v1) threw a `KeyError: 'ContainerConfig'` due to incompatibility with the new Docker Engine image metadata format.

**Solution:** Installed Docker Compose v2 as a CLI plugin manually using the following commands:
```bash
mkdir -p ~/.docker/cli-plugins
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m) -o ~/.docker/cli-plugins/docker-compose
chmod +x ~/.docker/cli-plugins/docker-compose
```

Once installed, the application was successfully started using the standard Compose V2 command:
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

---

## 3. Setting Up a Free Domain Name
To avoid sharing the raw AWS IP address, a custom domain was pointed to the EC2 server.

- **Attempt 1 (FreeDNS):** Tried `freedns.afraid.org` (chatbot-api.mooo.com), but DNS propagation was extremely slow, returning NXDOMAIN for too long.
- **Attempt 2 (DuckDNS):** Went to [duckdns.org](https://www.duckdns.org), signed in, and created the subdomain **`rishav-chatbot.duckdns.org`**. 
  - Pointed the IP directly to EC2 Public IP: `54.242.57.65`.
  - DNS resolved perfectly within seconds.

---

## 4. Install Nginx (Reverse Proxy) and Certbot
Nginx acts as a reverse proxy to route standard internet traffic (Ports 80/443) directly into the Docker container running on Port 8000. Certbot manages the SSL certificates.

```bash
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx -y
```

---

## 5. Configure Nginx
Created a new Nginx configuration file for the API:

```bash
sudo nano /etc/nginx/sites-available/chatbot-api
```

**Content:**
```nginx
server {
    listen 80;
    
    # Adding "_" makes it a catch-all, so it works when accessed via IP directly 
    # (e.g., http://54.242.57.65) — not just the domain name.
    server_name chatbot-api.mooo.com rishav-chatbot.duckdns.org _;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enabled the site by creating a symlink and removing the default config:
```bash
sudo ln -s /etc/nginx/sites-available/chatbot-api /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

---

## 6. SSL Certificate (HTTPS) with Let's Encrypt
To secure the connection, Let's Encrypt was used to generate an SSL certificate via Certbot:

```bash
sudo certbot --nginx -d rishav-chatbot.duckdns.org
```

This command automatically updated the Nginx configuration to handle HTTPS traffic and created an auto-renewal hook (certificate expires June 22, 2026).

---

## 7. Final Result
The API was completely deployed and is accessible securely at:

- **HTTPS (Production)**: [https://rishav-chatbot.duckdns.org](https://rishav-chatbot.duckdns.org)
- **Swagger Docs**: [https://rishav-chatbot.duckdns.org/docs](https://rishav-chatbot.duckdns.org/docs)
- **Direct IP (Fallback)**: `http://54.242.57.65`
