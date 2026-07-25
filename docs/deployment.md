# Deployment

ContentForge is containerised and ready for deployment on [Railway](https://railway.app).

---

## Railway deployment

### Prerequisites

- [Railway CLI](https://docs.railway.app/develop/cli) installed and authenticated
- A GitHub repo with your ContentForge code pushed
- Railway account with available project slots

### Files included

| File | Purpose |
|------|---------|
| `Dockerfile` | Python 3.11-slim container with uvicorn, health check, layer caching |
| `railway.json` | Build/deploy config — Nixpacks builder, health check path, restart policy |

### Live URL

**Production:** https://contentforge-production-7e96.up.railway.app

### Deploy steps

**Option A: Railway CLI (if project slot available)**

```bash
# 1. Create a Railway project
railway init --name contentforge

# 2. Set environment variables
railway variable set DATABASE_URL="postgresql+asyncpg://..."
railway variable set LLM_API_KEY="sk-..."
railway variable set SECRET_KEY="random-32-char-string"
railway variable set ENVIRONMENT="production"
railway variable set CORS_ORIGINS="https://myapp.com"

# 3. Deploy
railway up

# 4. Generate a public domain
railway domain

# 5. Open the deployed URL
railway open
```

**Option A2: Railway CLI (add as service to existing project)**

```bash
# 1. Link to an existing project
railway link --project <existing-project>

# 2. Create a new service
railway add --service contentforge

# 3. Link to the new service
railway link --project <existing-project> --service contentforge

# 4. Set environment variables
railway variable set ENVIRONMENT=production SECRET_KEY="your-secret"

# 5. Deploy
railway up

# 6. Generate a public domain
railway domain

# 7. Open the deployed URL
railway open
```

**Option B: GitHub auto-deploy**

1. Go to https://railway.app and create a new project
2. Select "Deploy from GitHub repo"
3. Connect your `csaszarzoltan/contentforge` repo
4. Railway auto-deploys on every push to the default branch

### Verify deployment

```bash
curl https://contentforge-production-7e96.up.railway.app/health
```

Expected response:
```json
{"status":"healthy","version":"0.3.0","timestamp":"...","checks":{"database":"ok","scheduler":"ok","llm_provider":"ok"}}
```

### Notes

- **Database tables** are auto-created on app startup via `Base.metadata.create_all()` in the lifespan handler. No manual migration step needed for SQLite.
- **`$PORT` variable**: The `startCommand` in `railway.json` wraps `$PORT` with a shell (`sh -c '...'`) to ensure shell variable expansion works correctly.
- **Service vs Project**: Railway free plan limits you to 2 **projects**, but you can add unlimited **services** per project. ContentForge was deployed as a service within the existing `locust-performance-kit` project.

---

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | `sqlite+aiosqlite:///./contentforge.db` | PostgreSQL connection string (auto-set by Railway Postgres addon). Falls back to SQLite for local dev. |
| `LLM_API_KEY` | Yes | `""` | OpenAI API key. Content generation returns stub data without this. |
| `SECRET_KEY` | Yes | `change-me-in-production` | Used for session signing. Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`. |
| `LLM_MODEL` | No | `gpt-4o` | Model identifier passed to the LLM provider. |
| `LLM_PROVIDER` | No | `openai` | Provider name. Currently only `openai` is implemented. |
| `LLM_BASE_URL` | No | — | Custom base URL for OpenAI-compatible proxies / self-hosted endpoints. |
| `ENVIRONMENT` | No | `development` | Set to `production` in deployment. Controls debug mode and logging. |
| `CORS_ORIGINS` | No | `*` | Comma-separated allowed CORS origins. In production, restrict to your frontend domain(s). |
| `HEALTH_CHECK_LLM` | No | `false` | When `true`, the `/health` endpoint performs a live LLM connectivity check. |
| `JWT_SECRET` | **Yes** | `change-me-in-production` | Secret key for JWT token signing. Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`. |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm (HS256, RS256, etc.). |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `15` | How long access tokens are valid, in minutes. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `30` | How long refresh tokens are valid, in days. |

---

## Railway free plan limits

Railway's free tier allows **2 projects per account** with unlimited services per project. If both project slots are occupied:

**Strategy: Add as a service to an existing project**

Instead of creating a new project (which would hit the 2-project limit), you can add a new service to an existing project:

```bash
# 1. Link to an existing project
railway link --project <existing-project>

# 2. Create the new service
railway add --service contentforge

# 3. Link to the new service
railway link --project <existing-project> --service contentforge

# 4. Set environment variables
railway variable set ENVIRONMENT=production SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"

# 5. Deploy
railway up

# 6. Generate a public domain
railway domain
```

---

## Local development

```bash
# Start with SQLite (no external deps)
uvicorn src.main:app --reload

# Or with PostgreSQL
DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/contentforge" \
  uvicorn src.main:app --reload

# Run tests
pytest

# Lint
ruff check src/
```

---

## Docker build (any platform)

```bash
# Build
docker build -t contentforge .

# Run
docker run -p 8000:8000 \
  -e DATABASE_URL="sqlite+aiosqlite:///./contentforge.db" \
  -e LLM_API_KEY="sk-..." \
  -e SECRET_KEY="your-secret" \
  contentforge

# Verify
curl http://localhost:8000/health
```
