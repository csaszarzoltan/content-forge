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

### Deploy steps

**Option A: Railway CLI**

```bash
# 1. Create a Railway project
railway init --name contentforge

# 2. Set environment variables
railway vars set DATABASE_URL="postgresql+asyncpg://..."
railway vars set LLM_API_KEY="sk-..."
railway vars set SECRET_KEY="random-32-char-string"
railway vars set ENVIRONMENT="production"
railway vars set CORS_ORIGINS="https://myapp.com"

# 3. Deploy
railway up

# 4. Open the deployed URL
railway open
```

**Option B: GitHub auto-deploy**

1. Go to https://railway.app and create a new project
2. Select "Deploy from GitHub repo"
3. Connect your `csaszarzoltan/contentforge` repo
4. Railway auto-deploys on every push to the default branch

### Verify deployment

```bash
curl https://your-project.up.railway.app/health
```

Expected response:
```json
{"status":"healthy","version":"0.3.0","timestamp":"...","checks":{"database":"ok","scheduler":"ok","llm_provider":"ok"}}
```

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

---

## Railway free plan limits

Railway's free tier allows **2 projects per account**. If you already have projects (e.g., `locust-performance-kit`, `receiptslens`), you'll see:

```
Error: Free plan resource limit — 2 existing projects
```

**Workarounds:**

1. **Upgrade to a paid Railway plan** — removes the project limit
2. **Delete or archive an existing project**:
   ```bash
   railway project delete
   railway init --name contentforge
   railway up
   ```
3. **Use GitHub auto-deploy** — connect the repo via Railway dashboard (free tier limit still applies)

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
