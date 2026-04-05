# Render Deployment (API + Workers)

This repo includes a Render Blueprint at `render.yaml` for:

- `pharmanexus-api` (web service running `app.py`)
- `pharmanexus-celery-worker` (background worker)
- `pharmanexus-celery-beat` (scheduler)
- `pharmanexus-postgres` (managed database)
- `pharmanexus-redis` (managed Redis)

## 1. Deploy Blueprint

1. Push your latest branch to GitHub.
2. In Render, go to **New +** -> **Blueprint**.
3. Select this repository.
4. Render will detect `render.yaml` and show all resources.
5. Click **Apply**.

## 2. Required Manual Env Vars

Set these on `pharmanexus-api` after initial apply:

- `ALLOWED_ORIGINS` = your Vercel URL (for example `https://app.yourdomain.com`)
- `GOOGLE_CLIENT_ID` (if OAuth enabled)
- `GOOGLE_CLIENT_SECRET` (if OAuth enabled)
- `ANTHROPIC_API_KEY` (if analyst endpoints enabled)

Then mirror the same optional vars on worker services if needed.

## 3. Validate API

After deploy, copy the API URL from Render and run:

```powershell
./smoke_prod.ps1 -ApiBaseUrl "https://YOUR-API.onrender.com"
```

Expected: all checks pass.

## 4. Validate Workers

In Render logs:

- `pharmanexus-celery-worker`: should show broker connection and worker ready.
- `pharmanexus-celery-beat`: should show scheduler startup.

## 5. Frontend Hand-off

After API is healthy:

1. Deploy frontend to Vercel from `frontend/` root.
2. Set `VITE_API_URL=https://YOUR-API.onrender.com`.
3. Re-run:

```powershell
./smoke_prod.ps1 -ApiBaseUrl "https://YOUR-API.onrender.com" -FrontendUrl "https://YOUR-APP.vercel.app"
```

## 6. DNS Cut

Only cut DNS after smoke passes:

- `api.yourdomain.com` -> Render API custom domain
- `app.yourdomain.com` -> Vercel
