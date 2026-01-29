# SakaiBot Secrets Directory

> ⚠️ **SECURITY WARNING**: This directory contains sensitive credentials.
> Never commit contents of this directory to git!

## Purpose

This directory is used for:

1. Temporary storage of encrypted secrets before transfer
2. Local backup of credentials

## Security Guidelines

1. **File Permissions**: All files should have `chmod 600`
2. **Encryption**: Always encrypt before transferring
3. **Cleanup**: Remove files after use

## Secure Transfer Process

### Option 1: GPG Encryption (Recommended)

```bash
# On your LOCAL machine:

# 1. Copy credentials to secrets/
cp .env secrets/.env.production
cp data/*.session secrets/

# 2. Create encrypted archive
tar -czf - secrets/ | gpg --symmetric --cipher-algo AES256 > sakaibot-secrets.tar.gz.gpg

# 3. Transfer to VPS
scp sakaibot-secrets.tar.gz.gpg user@your-vps:/home/user/

# 4. Clean up local secrets
rm -rf secrets/*

# On your VPS:

# 1. Decrypt
gpg --decrypt sakaibot-secrets.tar.gz.gpg | tar -xzf -

# 2. Move to correct locations
mv secrets/.env.production .env
mv secrets/*.session data/

# 3. Set permissions
chmod 600 .env data/*.session

# 4. Clean up
rm sakaibot-secrets.tar.gz.gpg
rm -rf secrets/
```

### Option 2: Direct SCP with SSH Key

```bash
# Only if using SSH key authentication (no password prompt)
scp -i ~/.ssh/vps_key .env user@your-vps:/path/to/sakaibot/.env
scp -i ~/.ssh/vps_key data/*.session user@your-vps:/path/to/sakaibot/data/
```

## Required Credentials

| Credential            | Required | Source          |
| --------------------- | -------- | --------------- |
| TELEGRAM_API_ID       | Yes      | my.telegram.org |
| TELEGRAM_API_HASH     | Yes      | my.telegram.org |
| TELEGRAM_PHONE_NUMBER | Yes      | Your phone      |
| GEMINI_API_KEY_1      | Yes\*    | AI Studio       |
| GEMINI_API_KEY_2      | No       | AI Studio       |
| GEMINI_API_KEY_3      | No       | AI Studio       |
| OPENROUTER_API_KEY    | No       | openrouter.ai   |
| SDXL_API_KEY          | No       | Cloudflare      |

\*At least one AI provider key is required for AI features.

## Session File Warning

The `.session` file contains your logged-in Telegram session.
If this file is compromised, an attacker can:

- Read your messages
- Send messages as you
- Access your contacts

**Always transfer securely and never share!**
