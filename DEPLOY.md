# Deployment Guide

Free stack: Vercel (frontend) + Render (backend) + Neon (PostgreSQL) + Upstash (Redis, already configured)

---

## Step 1 — Neon PostgreSQL (free database)

1. Go to https://neon.tech and sign in with GitHub
2. Create project → name it `pod-manufacturing`, region `EU Frankfurt`
3. Copy the **connection string** — looks like:
   ```
   postgresql://user:pass@ep-xxx.eu-central-1.aws.neon.tech/neondb?sslmode=require
   ```
4. Run Alembic migrations from your local machine:
   ```bash
   cd backend
   DATABASE_URL="postgresql://..." python -m alembic upgrade head
   ```
5. Run the manual migration scripts in order:
   ```bash
   DATABASE_URL="postgresql://..." python migrate_finish_catalogue.py
   DATABASE_URL="postgresql://..." python migrate_finish_packages.py
   DATABASE_URL="postgresql://..." python migrate_pod_spec_finishes.py
   DATABASE_URL="postgresql://..." python migrate_settings.py
   DATABASE_URL="postgresql://..." python migrate_finish_catalogue_link_rules.py
   ```
6. Seed the finish catalogue:
   ```bash
   DATABASE_URL="postgresql://..." python seeds/finish_catalogue_seed.py
   ```

---

## Step 2 — Render backend (free web service)

1. Push this repo to GitHub (if not already there)
2. Go to https://render.com → New → Web Service
3. Connect your GitHub repo, set **Root Directory** to `backend`
4. Render auto-detects `render.yaml` — confirm the settings:
   - Build: `pip install -e "."`
   - Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Region: Frankfurt
5. Add these environment variables in the Render dashboard:
   ```
   DATABASE_URL      = <neon connection string from Step 1>
   REDIS_URL         = <upstash redis URL from .env>
   CLERK_JWKS_URL    = https://<your-clerk-prod-domain>/.well-known/jwks.json
   CLERK_SECRET_KEY  = sk_live_...  (from Clerk production dashboard)
   CORS_ORIGINS      = https://<your-vercel-url>.vercel.app
   ```
6. Deploy. Note your backend URL: `https://pod-manufacturing-api.onrender.com`

---

## Step 3 — Clerk production keys

1. Go to https://clerk.com → your app → **Production** instance
2. Copy:
   - Publishable key: `pk_live_...`
   - Secret key: `sk_live_...`
   - JWKS URL: `https://<your-prod-domain>.clerk.accounts.dev/.well-known/jwks.json`
3. Under **Restrictions** → enable **Allowlist** → disable open sign-ups
4. Under **Users** → invite yourself and team members by email
5. Under **Domains** → add your Vercel URL as an allowed origin

---

## Step 4 — Vercel frontend

1. Go to https://vercel.com → Import Project → select this repo
2. Framework preset: **Vite**
3. Build command: `npm run build`
4. Output directory: `dist`
5. Add environment variables:
   ```
   VITE_API_URL                = https://pod-manufacturing-api.onrender.com
   VITE_CLERK_PUBLISHABLE_KEY  = pk_live_...
   ```
6. Deploy. 

---

## Step 5 — Wire CORS

After Vercel deploys, copy your Vercel URL (e.g. `https://pod-mfg.vercel.app`) and update
`CORS_ORIGINS` in Render to include it. Redeploy the Render service.

---

## Notes

- **Render free tier cold-starts** after 15 minutes of inactivity. First request of the day
  takes 30–60 seconds. This is normal for an internal tool.
- **Access control**: only email addresses you invite in the Clerk dashboard can sign in.
  Nobody else can create an account.
- To add a custom domain later (e.g. `pod.toprins.com`): add it in Vercel's domain settings
  and point a DNS CNAME record to `cname.vercel-dns.com`.
