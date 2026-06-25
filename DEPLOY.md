# Deploying Aigram

Aigram is a **self-hosted** Telegram userbot + AI control panel. You run **your own**
instance with **your own** credentials — nobody else holds your Telegram session.
This guide covers getting it online cheaply (or free), including from regions where
Telegram/Google are blocked (e.g. Iran).

> ⚠️ Aigram logs in as a *real Telegram account* (userbot). That's against Telegram's
> ToS and can risk a ban. Use a **stable IP** (a steady VPS or a home device beats
> churny/flagged datacenter IPs), avoid mass/automated sending, and keep your access
> token secret.

---

## First-run: the setup wizard (no terminal login needed)

On a fresh box you don't need to edit `.env` by hand. Run the **setup wizard**:

```bash
sakaibot setup            # or: python -m src.cli.main setup
```

It prints a URL + token. Open it (locally, or through a tunnel — see below) and the
wizard walks you through: **Telegram API id/hash/phone → login code → 2FA (if any) →
LLM key**. It writes `.env` and logs you in. Then start the real panel:

```bash
sakaibot panel            # premium dashboard + the bot stays live in chats
```

The panel prints `http://127.0.0.1:8765/?token=…` — open that to use Aigram. You can
add/test more keys, set categorization, etc. all from the **Keys**, **Routing**, and
other panels.

---

## Where to run it

### 1. Cheap VPS — recommended, no credit card  ⭐

A ~€1.49–2.99/mo VPS (1 CPU / 1 GiB / 10 GiB is **enough for one user**) is the
simplest always-on option. To satisfy **no credit card + sanctioned region**:

- Pick a provider that takes **crypto** (e.g. Aeza and similar) — no card needed.
- Pick a **non-Iran location** (Amsterdam / Riga / Paris). The server then reaches
  Telegram/Google **directly** with a clean IP; you just manage it over a VPN.

```bash
# on the VPS (Ubuntu/Debian):
curl -fsSL https://get.docker.com | sh                 # install Docker
git clone <your-fork-of-aigram> aigram && cd aigram
# add a 2 GB swap so STT/ffmpeg spikes never OOM the 1 GiB box:
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile \
  && sudo mkswap /swapfile && sudo swapon /swapfile \
  && echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
docker compose up -d                                    # build + run
docker compose exec sakaibot sakaibot setup             # run the wizard once
```

**Docker, not Kubernetes:** for one user / one container, k8s is pure overhead (its
control plane alone would eat most of 1 GiB). The included `docker-compose.yml` is the
right tool (non-root, healthcheck, log rotation, restart-unless-stopped).

### 2. Home device — Termux / Raspberry Pi / old PC (free, most ban-safe)

Zero cost and a **stable residential IP** (the safest for ban-avoidance). Any
always-on machine with Docker works:

```bash
git clone <your-fork> aigram && cd aigram
docker compose up -d
docker compose exec sakaibot sakaibot setup
```

On Android, [Termux](https://termux.dev) runs Python directly (no Docker): install
`python`, `ffmpeg`, `git`, then `pip install -e .` and `sakaibot setup`.

**From Iran:** a home server has an Iranian IP, so the userbot can't reach Telegram
directly — route it through a proxy/VPN. Aigram ships proxy plumbing
(`docker/vps/enable_proxy.sh`, redsocks, SOCKS) for exactly this; or run the whole
device behind a VPN.

### 3. Use it on your phone (PWA)

Aigram is an installable PWA. To install it on your phone you need to reach the panel
over **HTTPS**:

- **Free, no card — Cloudflare Tunnel** (recommended): keeps the panel bound to
  `127.0.0.1` (safest) and exposes a public HTTPS URL.
  ```bash
  cloudflared tunnel --url http://127.0.0.1:8765
  ```
  Open the printed `https://…trycloudflare.com/?token=…` on your phone → browser menu →
  **Add to Home Screen**. Works offline (service worker) and from Iran via a VPN.
- **LAN + self-signed HTTPS** (home Wi-Fi): `sakaibot panel --expose-lan --tls-cert cert.pem --tls-key key.pem`
  (generate a cert with `openssl`/`mkcert`). Trust it once on the phone, then install.
- **LAN over HTTP**: `sakaibot panel --expose-lan` works as a basic shortcut but has
  **no** offline/service-worker (browsers require HTTPS for that).

### 4. Quick test — Railway

A one-click-ish PaaS for a fast try (burns trial credit, then pauses — not free-forever
24/7): push the repo, set the env vars (or run the wizard), done.

---

## Free-tier reality check

Most foreign free tiers (Oracle, Google Cloud, Fly, Render, Railway) need a credit
card and commonly block sign-ups from sanctioned regions — so for **no-card + Iran**,
the **cheap crypto VPS** or a **home device** are the realistic paths. A genuinely free
always-on cloud VM (Oracle Always Free / GCP e2-micro) works *if* you can sign up.

---

## Updating

```bash
git pull && docker compose up -d --build
```

Your `.env` and `data/` (session, settings) are preserved.
