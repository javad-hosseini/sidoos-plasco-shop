# Sidoos Django Deployment — Documentation

This document is the **complete record** of everything we did to deploy the `sidoos-plasco-shop` Django project on the `srv5517394641` server. It includes every config, path, command, and the remaining steps to move from development-mode to production (PostgreSQL + SSL).

---

## 1. Overview

| Item                     | Value                                                            |
| ------------------------ | ---------------------------------------------------------------- |
| Project                  | `sidoos-plasco-shop` (Django)                                    |
| Server IP                | `185.8.172.210`                                                  |
| Server hostname          | `srv5517394641`                                                  |
| OS                       | Ubuntu (systemd, Python 3.12)                                    |
| Primary Domain           | `sidoos.ir` (CNAMEs / redirects for `www.sidoos.ir`, `sidoos.com`, `www.sidoos.com`, `sidos.ir`) |
| Mail Hostname            | `mail.sidoos.ir`                                                 |
| Project root             | `/var/www/sidoos`                                                |
| WSGI entrypoint          | `config.wsgi:application`                                        |
| Web server               | Nginx 1.24.0 (HTTP/2, SSL termination)                           |
| App server               | Gunicorn 26.2.0 (socket-activated)                               |
| Current DB               | ✅ PostgreSQL 16 (`APP_ENV=production`, `sidoos_db`)            |
| Current SSL              | ✅ Multi-domain Let's Encrypt (`sidoos.ir`, `mail.sidoos.ir`, `sidoos.com`, etc.) |
| Mail Server              | ✅ Postfix 3.8 + Dovecot 2.3 + OpenDKIM (IMAP/POP3/SMTP)        |
| Active Mailboxes         | `support@sidoos.ir`, `noreply@sidoos.ir`, `sidoos@sidoos.ir`     |
| DNS                      | ✅ `sidoos.ir`, `mail.sidoos.ir` → `185.8.172.210` (MX: 10 mail.sidoos.ir) |

---

## 2. SSH Access (Passwordless)

Passwordless SSH was configured **on the Windows client**, so the server can be reached without typing IP or password.

### 2.1. Key generation (on Windows)

```powershell
ssh-keygen -t ed25519 -C "your_email@example.com"
```

Files created:

- `C:\Users\<User>\.ssh\id_ed25519` (private key — never share)
- `C:\Users\<User>\.ssh\id_ed25519.pub` (public key)

### 2.2. Copy public key to server

```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh root@185.8.172.210 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

### 2.3. SSH config file (`C:\Users\<User>\.ssh\config`)

```text
Host sidoos
    HostName 185.8.172.210
    User root
    IdentityFile ~/.ssh/id_ed25519
```

Now you can connect with:

```powershell
ssh sidoos
```

---

## 3. Project Transfer & Layout

### 3.1. Transfer from Windows to server

```powershell
scp -r "D:\projects\websites\sidoos-plasco-shop\*" sidoos:/var/www/sidoos-plasco-shop/
```

The project was then extracted/moved to its final location:

```
/var/www/sidoos
```

### 3.2. Final directory layout

```
/var/www/sidoos/
├── .env.dev
├── .env.example
├── .env.prod
├── .git/
├── .github/
├── .idea/
├── .gitignore
├── README.md
├── apps/
├── config/
│   ├── asgi.py
│   ├── settings.py
│   ├── wsgi.py
│   └── jazzmin.py
├── db.sqlite3
├── docs/
├── install.cmd
├── manage.py
├── media/
├── requirements.txt
├── srv.log
├── static/
├── staticfiles/
├── templates/
└── venv/
```

### 3.3. Media / Static paths

| Purpose          | Path                          |
| ---------------- | ----------------------------- |
| Static source    | `/var/www/sidoos/static`      |
| Static collected | `/var/www/sidoos/staticfiles` |
| Media            | `/var/www/sidoos/media`       |

---

## 4. Python Environment

### 4.1. Create venv

```bash
cd /var/www/sidoos
python3 -m venv venv
source venv/bin/activate
```

### 4.2. Install requirements (with Iranian mirror)

Because `pypi.org` was timing out from this server, the Runflare mirror was used:

```bash
pip install -r requirements.txt \
  --index-url https://mirror-pypi.runflare.com/simple \
  --trusted-host mirror-pypi.runflare.com
```

### 4.3. Gunicorn

```bash
pip install "gunicorn==26.2.0"
```

Verify:

```bash
pip show gunicorn
# Version: 26.2.0
```

---

## 5. Django Settings — Environment Logic

### 5.1. Env file selection (`config/settings.py`)

```python
ENV_FILE = BASE_DIR / (
    ".env.prod"
    if os.getenv("DJANGO_ENV") == "production"
    else ".env.dev"
)

config = Config(RepositoryEnv(ENV_FILE))
```

So:

- `DJANGO_ENV=production` (set via systemd) → loads `.env.prod`
- otherwise → loads `.env.dev`

### 5.2. Database selection (inside `.env.prod`)

```python
APP_ENV = config("APP_ENV", default="development")

if APP_ENV == "production":
    # PostgreSQL
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME"),
            "USER": config("DB_USER"),
            "PASSWORD": config("DB_PASSWORD"),
            "HOST": config("DB_HOST"),
            "PORT": config("DB_PORT", cast=int),
        }
    }
elif APP_ENV == "test" and os.getenv("DATABASE_URL"):
    # dj_database_url (CI)
    ...
else:
    # SQLite (development)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
```

### 5.3. `SECURE_SSL_REDIRECT` (made configurable)

Originally:

```python
if not DEBUG:
    SECURE_SSL_REDIRECT = True
```

Changed to:

```python
if not DEBUG:
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
```

This allows temporarily disabling HTTPS redirect while SSL isn't installed yet.

### 5.4. Current `.env.prod` (development-on-server mode)

```env
APP_ENV=development
SECRET_KEY='django-insecure-yni73wzqiq_2ra!0=2)+v7&z$vbrcfscto)v89k&7x(6+^!owo'
DEBUG=False
ALLOWED_HOSTS=sidoos.com,www.sidoos.com,185.8.172.210,localhost,127.0.0.1
SECURE_SSL_REDIRECT=False

DB_NAME=mydb
DB_USER=postgres
DB_PASSWORD=123456
DB_HOST=127.0.0.1
DB_PORT=5432
```

> ⚠️ `DB_*` values are **not used yet** — they are placeholders for the production PostgreSQL step (Section 11).

---

## 6. Gunicorn (systemd + socket activation)

### 6.1. `/etc/systemd/system/gunicorn.socket`

```ini
[Unit]
Description=gunicorn socket

[Socket]
ListenStream=/run/gunicorn.sock

[Install]
WantedBy=sockets.target
```

### 6.2. `/etc/systemd/system/gunicorn.service`

```ini
[Unit]
Description=gunicorn daemon for sidoos
Requires=gunicorn.socket
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=/var/www/sidoos
Environment="DJANGO_ENV=production"
ExecStart=/var/www/sidoos/venv/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --bind unix:/run/gunicorn.sock \
          config.wsgi:application

[Install]
WantedBy=multi-user.target
```

> Note: `User=root` is an explicit (but risky) decision. A dedicated `django` user is recommended later (Section 12).

### 6.3. Enable and start

```bash
systemctl daemon-reload
systemctl enable gunicorn.socket gunicorn.service
systemctl reset-failed gunicorn.service gunicorn.socket
systemctl restart gunicorn.socket
```

### 6.4. Verify

```bash
systemctl status gunicorn.service --no-pager
journalctl -u gunicorn.service -n 40 --no-pager
```

Expected log:

```
Starting gunicorn 26.2.0
Listening at: unix:/run/gunicorn.sock
Using worker: sync
Booting worker with pid: ...
```

### 6.5. Direct socket test

```bash
curl --unix-socket /run/gunicorn.sock -H "Host: sidoos.com" http://localhost/ -I
```

Expected:

```
HTTP/1.1 301 Moved Permanently
Location: https://sidoos.com/
```

or (after disabling redirect) `200 OK`.

---

## 7. Nginx

### 7.1. Installation

```bash
apt update
apt install nginx -y
systemctl enable nginx
systemctl start nginx
```

### 7.2. Site config — `/etc/nginx/sites-available/sidoos.com`

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name sidoos.com www.sidoos.com 185.8.172.210;

    client_max_body_size 20M;

    location /static/ {
        alias /var/www/sidoos/staticfiles/;
        expires 30d;
        access_log off;
    }

    location /media/ {
        alias /var/www/sidoos/media/;
        expires 30d;
        access_log off;
    }

    location / {
        proxy_pass http://unix:/run/gunicorn.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

### 7.3. Enable site & disable default

```bash
ln -s /etc/nginx/sites-available/sidoos.com /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
```

### 7.4. Verify

```bash
ls -la /etc/nginx/sites-enabled/
# only sidoos.com -> should appear

curl -I http://localhost -H "Host: sidoos.com"
# HTTP/1.1 200 OK
```

### 7.5. Firewall

```bash
ufw allow 'Nginx Full'
ufw allow OpenSSH
ufw status
# Status: inactive  (no active firewall on this host)
```

---

## 8. Static Files

Collected with:

```bash
cd /var/www/sidoos
source venv/bin/activate
python manage.py collectstatic --noinput
# → 316 static files copied to /var/www/sidoos/staticfiles
```

Served by Nginx via the `/static/` location (Section 7.2). Verified:

```bash
curl -I http://localhost/static/fonts/fonts.css
# HTTP/1.1 200 OK
# Content-Type: text/css
```

---

## 9. DNS Status (⚠️ ACTION REQUIRED)

At the time of writing:

```bash
dig sidoos.com +short      # 185.239.1.100   ❌
dig www.sidoos.com +short  # 185.239.1.100   ❌
hostname -I                # 185.8.172.210   ✅
```

**The domain must be repointed** to `185.8.172.210` before SSL can be issued.

### 9.1. Required DNS records

| Type | Name  | Value           | TTL        |
| ---- | ----- | --------------- | ---------- |
| A    | `@`   | `185.8.172.210` | Auto / 300 |
| A    | `www` | `185.8.172.210` | Auto / 300 |

Remove any stale `AAAA` (IPv6) records.

### 9.2. Verify propagation

```bash
dig sidoos.com +short
# must return 185.8.172.210
```

---

## 10. SSL (Certbot / Let's Encrypt) — AFTER DNS IS FIXED

> ⚠️ Do **not** run Certbot until `dig sidoos.com +short` returns `185.8.172.210`.

### 10.1. Install Certbot

```bash
apt install certbot python3-certbot-nginx -y
```

### 10.2. Issue certificate

```bash
certbot --nginx -d sidoos.com -d www.sidoos.com
```

Answers:

- Email: your real email
- Agree: `A`
- Redirect HTTP → HTTPS: choose **`2` (Redirect)**

Certbot will:

- Obtain the certificate
- Patch the Nginx config for TLS on 443
- Insert the `return 301 https://$host$request_uri;` redirect for port 80

### 10.3. Re-enable HTTPS redirect in Django

In `.env.prod`:

```env
SECURE_SSL_REDIRECT=True
```

Also add if not present:

```env
CSRF_TRUSTED_ORIGINS=https://sidoos.com,https://www.sidoos.com
```

Restart:

```bash
systemctl restart gunicorn.socket
```

### 10.4. Auto-renewal check

```bash
systemctl status certbot.timer
certbot renew --dry-run
```

### 10.5. Final verification

```bash
curl -I http://sidoos.com
# HTTP/1.1 301 Moved Permanently
# Location: https://sidoos.com/

curl -I https://sidoos.com
# HTTP/2 200
```

---

## 11. Production Migration (PostgreSQL)

Once SSL is working and you want to move off SQLite:

### 11.1. Install PostgreSQL + Python driver

```bash
apt install postgresql postgresql-contrib -y

cd /var/www/sidoos
source venv/bin/activate
pip install "psycopg[binary]"
# or, if the project requires psycopg2:
# pip install psycopg2-binary

pip freeze > requirements.txt
```

### 11.2. Create database & user

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE mydb;
CREATE USER sidoos_user WITH ENCRYPTED PASSWORD 'a-strong-password';
ALTER ROLE sidoos_user SET client_encoding TO 'utf8';
ALTER ROLE sidoos_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE sidoos_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE mydb TO sidoos_user;
\q
```

### 11.3. Update `.env.prod`

```env
APP_ENV=production
SECRET_KEY='<generate-a-new-strong-key>'
DEBUG=False
ALLOWED_HOSTS=sidoos.com,www.sidoos.com,185.8.172.210,localhost,127.0.0.1
SECURE_SSL_REDIRECT=True
CSRF_TRUSTED_ORIGINS=https://sidoos.com,https://www.sidoos.com

DB_NAME=mydb
DB_USER=sidoos_user
DB_PASSWORD=a-strong-password
DB_HOST=127.0.0.1
DB_PORT=5432
```

### 11.4. Migrate & collectstatic

```bash
cd /var/www/sidoos
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
```

### 11.5. (Optional) Migrate data from SQLite → Postgres

```bash
python manage.py dumpdata --natural-foreign --natural-primary \
  --exclude=contenttypes --exclude=auth.permission \
  --indent 2 > /tmp/dump.json
```

Switch `APP_ENV` to `production`, then:

```bash
python manage.py loaddata /tmp/dump.json
```

### 11.6. Restart

```bash
systemctl restart gunicorn.socket
```

---

## 12. Mail Server Setup (`mail.sidoos.ir` & `sidoos.ir`)

A fully-featured, secure mail server stack was installed and configured on the server to handle inbound and outbound email for `@sidoos.ir`.

### 12.1. Architecture & Components

- **MTA (Postfix 3.8)**: Handles SMTP (port 25), Submission with STARTTLS (port 587), and SMTPS (port 465).
- **MDA / IMAP / POP3 (Dovecot 2.3)**: Handles mailbox storage via Maildir format, Dovecot LMTP delivery socket (`/var/spool/postfix/private/dovecot-lmtp`), SASL authentication socket (`/var/spool/postfix/private/auth`), IMAPS (port 993), and POP3S (port 995).
- **DKIM Signing (OpenDKIM)**: Automatically signs outgoing messages from `@sidoos.ir` with selector `default` via milter on `127.0.0.1:8891`.
- **Mail Storage**: Stored securely in `/var/vmail/sidoos.ir/<username>/` under virtual user `vmail:vmail` (UID/GID 5000).

### 12.2. Configured Mailboxes

All mailboxes use SHA512-CRYPT password hashing in `/etc/dovecot/users`.

| Mailbox | Initial Password | Maildir Directory |
| --- | --- | --- |
| `support@sidoos.ir` | `Evana@5674` | `/var/vmail/sidoos.ir/support` |
| `noreply@sidoos.ir` | `Evana@5674` | `/var/vmail/sidoos.ir/noreply` |
| `sidoos@sidoos.ir` | `Evana@5674` | `/var/vmail/sidoos.ir/sidoos` |

### 12.3. Client Connection Settings

For configuring mail clients (Thunderbird, Outlook, Apple Mail, mobile devices):

- **Incoming Mail (IMAP)**:
  - Hostname: `mail.sidoos.ir`
  - Port: `993`
  - Security: `SSL/TLS`
  - Authentication: Normal Password
  - Username: Full email address (e.g. `support@sidoos.ir`)
- **Incoming Mail (POP3)** (alternative):
  - Hostname: `mail.sidoos.ir`
  - Port: `995`
  - Security: `SSL/TLS`
- **Outgoing Mail (SMTP)**:
  - Hostname: `mail.sidoos.ir`
  - Port: `587` (STARTTLS) or `465` (SSL/TLS)
  - Security: STARTTLS or SSL/TLS
  - Authentication: Normal Password
  - Username: Full email address

### 12.4. Required DNS Records

To ensure 100% email deliverability and avoid spam filters, add the following DNS records at your domain registrar/DNS manager for `sidoos.ir`:

1. **MX Record**:
   - Host / Name: `@` (or `sidoos.ir`)
   - Type: `MX`
   - Value: `mail.sidoos.ir`
   - Priority: `10`

2. **A Record for Mail**:
   - Host / Name: `mail`
   - Type: `A`
   - Value: `185.8.172.210`

3. **SPF (Sender Policy Framework)**:
   - Host / Name: `@` (or `sidoos.ir`)
   - Type: `TXT`
   - Value: `v=spf1 mx a:mail.sidoos.ir ip4:185.8.172.210 ~all`

4. **DKIM (DomainKeys Identified Mail)**:
   - Host / Name: `default._domainkey` (or `default._domainkey.sidoos.ir`)
   - Type: `TXT`
   - Value:
     ```text
     v=DKIM1; h=sha256; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAvPgV287Qtg9xmfh8fpLNrqhRBlA9glMHelfo4WqPsS12MdqhnmqDdqkG4OCFm+oeLEOYveBt8V5Si+f1es1B7lO5L/nKs/il5pZ+tEDFi/rRW9mSI8wUFFB9rODKIdHZw/es3NcojFqQQlJon8vZih4sVbjIxNl//GwA4Nr7yxiUesoOm2kykCMVbRzdm2SHenVJp1gMUa4ITNNm/N8bW2VP2MUqRszv+rIlb12+J7C3Ud86SjvPTR75a471yavnaQUiV8g3QEiQUStTVrInlvsEafF6ODqSZ4SikDSG86PNfcU1/We6nMZaCoIjrShQ19w+tEZs4c5HZWJuYBpEiwIDAQAB
     ```

5. **DMARC**:
   - Host / Name: `_dmarc` (or `_dmarc.sidoos.ir`)
   - Type: `TXT`
   - Value: `v=DMARC1; p=none; sp=none; rua=mailto:support@sidoos.ir`

### 12.5. Django Email Integration

Django is configured in `config/settings.py` and `/var/www/sidoos/.env.prod` to send transactional emails through the local Postfix instance:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = '127.0.0.1'
EMAIL_PORT = 25
DEFAULT_FROM_EMAIL = 'noreply@sidoos.ir'
SERVER_EMAIL = 'noreply@sidoos.ir'
```

---

## 13. Security / Hardening Recommendations (not done yet)

| Item                    | Current state                                            | Recommendation                                                                                                |
| ----------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Gunicorn user           | `root`                                                   | Create `django` user; `chown -R django:django /var/www/sidoos`; set `User=django` in unit file                |
| `.env.prod` permissions | `600`                                                    | Maintained                                                                                                    |
| `SECRET_KEY`            | Strong random secret key                                 | Maintained                                                                                                    |
| `DB_PASSWORD`           | Strong random password                                   | Maintained                                                                                                    |
| Suspicious packages     | `config==0.5.1`, `testcase==0.1.0` in `requirements.txt` | `grep -R "import config\|from config\|import testcase\|from testcase" /var/www/sidoos` and remove if unused   |
| Firewall                | `ufw inactive`                                           | Enable UFW allowing SSH (`22`), Nginx (`80`, `443`), Postfix (`25`, `465`, `587`), Dovecot (`993`, `995`)   |
| SSH root login          | enabled                                                  | Consider `PermitRootLogin prohibit-password` + dedicated deploy user                                          |
| Fail2ban                | not installed                                            | Install and enable for SSH/Nginx/Postfix/Dovecot                                                              |
| Backups                 | none                                                     | Set up `pg_dump` + media + mail sync cron                                                                     |

---

## 14. Remaining Tasks (Checklist)

- [x] Fix DNS: point `sidoos.com` and `www.sidoos.com` to `185.8.172.210`
- [x] Switch primary domain to `sidoos.ir` with multi-domain SSL
- [x] Configure Nginx 301 redirects for secondary domains to `https://sidoos.ir`
- [x] Re-enable `SECURE_SSL_REDIRECT=True`
- [x] Set `CSRF_TRUSTED_ORIGINS` to HTTPS URLs
- [x] Configure Certbot automatic renewal hook (`systemctl reload nginx`)
- [x] `chmod 600 .env.prod`
- [x] Install `psycopg[binary]` and migrate to PostgreSQL
- [x] Set up Postfix, Dovecot, and OpenDKIM mail server
- [x] Create mailboxes (`support@sidoos.ir`, `noreply@sidoos.ir`, `sidoos@sidoos.ir`)
- [x] Integrate Django with local Postfix email sending
- [ ] Add DKIM, SPF, and DMARC TXT records in DNS manager
- [ ] (Optional) Create dedicated `django` OS user for Gunicorn
- [ ] (Recommended) Enable UFW firewall
- [ ] (Recommended) Install Fail2ban

---

## 15. Useful Commands Cheat Sheet

### Mail Server Management

```bash
# Check services status
systemctl status postfix dovecot opendkim --no-pager

# Reload configs
postfix reload
systemctl restart dovecot
systemctl restart opendkim

# Check listening mail ports
ss -tlpn | grep -E ':(25|465|587|143|993|110|995|8891)'

# Test user mailbox authentication
doveadm auth test support@sidoos.ir 'Evana@5674'
doveadm auth test noreply@sidoos.ir 'Evana@5674'
doveadm auth test sidoos@sidoos.ir 'Evana@5674'

# View mail logs
journalctl -u postfix -n 50 --no-pager
journalctl -u dovecot -n 50 --no-pager
journalctl -u opendkim -n 50 --no-pager
```

### Services & Web

```bash
systemctl status gunicorn.service --no-pager
systemctl restart gunicorn
systemctl reload  nginx
```

---

## 16. Summary of What Works Right Now

✅ SSH passwordless access via `ssh sidoos`  
✅ Project deployed to `/var/www/sidoos` on `develop` branch  
✅ Python venv with all requirements  
✅ Gunicorn 26.2.0 running via socket activation on `/run/gunicorn.sock`  
✅ Django loads correctly under `DJANGO_ENV=production` (`.env.prod`)  
✅ PostgreSQL 16 database (`sidoos_db`) active in production with seeded sample data  
✅ Primary domain configured as `https://sidoos.ir` with HTTP/2 and multi-domain Let's Encrypt SSL  
✅ Secondary domains (`sidoos.com`, `www.sidoos.com`, `www.sidoos.ir`) 301 redirect to `https://sidoos.ir`  
✅ Postfix + Dovecot + OpenDKIM mail server running and listening on 25, 465, 587, 143, 993, 110, 995  
✅ Mailboxes `support@sidoos.ir`, `noreply@sidoos.ir`, `sidoos@sidoos.ir` active with verified authentication  
✅ Django email backend connected and successfully verified with DKIM signing and local delivery  

---

*End of document.*

