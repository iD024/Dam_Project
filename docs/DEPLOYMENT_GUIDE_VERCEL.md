# Production Deployment Guide: Vercel & Render

This guide walks you step-by-step through deploying the **Dam-Break Flood Simulation & AI Decision-Support Platform** to production.

```
┌─────────────────────────────────────────────────────────────┐
│                     Vercel Edge Network                     │
│  Next.js 16 (React 19, Turbopack, Tailwind CSS, MapLibre GL)│
│  Root Directory: frontend/                                  │
│  Env: NEXT_PUBLIC_API_URL=https://<your-render-app>/api/v1   │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTPS (CORS Enabled)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                      Render Web Service                     │
│  FastAPI (Python 3.12, Uvicorn, Docker)                     │
│  Solvers: 2D SWE, D-Flow FM, DualSPHysics                   │
│  Env: CORS_ORIGINS=https://*.vercel.app,http://localhost:3000│
└─────────────────────────────────────────────────────────────┘
```

---

## Why This Architecture?

- **Frontend on Vercel**: Vercel provides instant builds, global edge caching, automated SSL certificates, and zero-config deployment for Next.js 16.
- **Backend on Render**: Hydrodynamic simulations (2D Shallow Water Equations, particle solvers) and SQLite write operations require a persistent container environment. Render provides persistent execution without the strict 10-second timeout limits of serverless functions.

---

## Phase 1: Deploy the Python Backend on Render (5 Minutes)

Deploy the backend first so you have your live API URL ready for Vercel.

### Method A: 1-Click Blueprint via `render.yaml` (Recommended)

1. Push your repository to GitHub:
   ```bash
   git add .
   git commit -m "feat: add vercel and render deployment configuration"
   git push origin main
   ```
2. Log in to your [Render Dashboard](https://dashboard.render.com).
3. Click **Blueprints** in the top navigation bar, then click **New Blueprint Instance**.
4. Select your GitHub repository.
5. Render will automatically detect the [`render.yaml`](file:///home/laksh/Projects/Dam_Project/render.yaml) file:
   - **Service Name**: `dam-break-simulation-backend`
   - **Runtime**: Docker (builds from [`Dockerfile`](file:///home/laksh/Projects/Dam_Project/Dockerfile))
   - **Environment Variables**: Pre-configured (`CORS_ORIGINS`, `PORT`)
6. Click **Apply**. Render will build the Docker container and deploy the service.

---

### Method B: Manual Web Service on Render

If you prefer to configure the service manually:

1. In the [Render Dashboard](https://dashboard.render.com), click **New +** → **Web Service**.
2. Connect your GitHub repository.
3. Configure the following fields:
   - **Name**: `dam-break-backend` (or your choice)
   - **Region**: Select the region closest to you (e.g., Oregon, Frankfurt, Singapore)
   - **Language**: **Docker**
   - **Dockerfile Path**: `./Dockerfile`
   - **Instance Type**: Free (or Starter for higher compute)
4. Under **Environment Variables**, add:
   | Key | Value | Description |
   | :--- | :--- | :--- |
   | `CORS_ORIGINS` | `https://*.vercel.app,http://localhost:3000` | Allows requests from Vercel deployments and localhost |
   | `PORT` | `8000` | Application listen port |
5. Click **Deploy Web Service**.

---

### Verify Backend Health

Once Render finishes building (usually 2–3 minutes):
1. Copy your Render service URL (e.g., `https://dam-break-backend.onrender.com`).
2. Test the health check endpoint in your browser or terminal:
   ```bash
   curl https://<your-render-service-url>.onrender.com/api/health
   ```
3. Expected JSON response:
   ```json
   {
     "status": "healthy",
     "service": "Dam-Break Inundation AI Platform",
     "version": "1.0.0",
     "supported_solvers": ["fast_swe", "dflowfm", "dualsphysics"]
   }
   ```

---

## Phase 2: Deploy the Next.js Frontend to Vercel (3 Minutes)

### Method A: Via Vercel Web Dashboard (Recommended)

1. Go to [Vercel Dashboard](https://vercel.com) and click **"Add New..."** → **Project**.
2. Under **Import Git Repository**, choose your GitHub repository and click **Import**.
3. **CRITICAL STEP — Configure Root Directory**:
   - In the **Project Settings** screen, look for **Root Directory**.
   - Click **Edit** next to `./`.
   - Select or type `frontend` and click **Continue**.
4. **Framework Preset**: Vercel will automatically detect **Next.js**.
5. **Environment Variables**:
   - Expand the **Environment Variables** section.
   - Add the following variable:
     | Key | Value |
     | :--- | :--- |
     | `NEXT_PUBLIC_API_URL` | `https://<your-render-service-url>.onrender.com/api/v1` |
   > [!IMPORTANT]
   > Ensure the URL includes `/api/v1` at the end (the frontend automatically normalizes this, but it's best practice to specify it explicitly).
6. Click **Deploy**.

Vercel will build the Next.js application (using Turbopack) and provide a live production URL (e.g., `https://dam-project-xxx.vercel.app`).

---

### Method B: Via Vercel CLI

If you have the Vercel CLI installed:

```bash
# Navigate to the frontend directory
cd frontend

# Deploy using Vercel CLI
npx vercel
```

Follow the interactive prompts:
- **Set up and deploy?**: `yes`
- **Which scope?**: Choose your personal/team account
- **Link to existing project?**: `no`
- **What's your project's name?**: `dam-break-platform`
- **In which directory is your code located?**: `./`

Once linked, set the environment variable and deploy to production:
```bash
npx vercel env add NEXT_PUBLIC_API_URL production
# When prompted, paste: https://<your-render-service-url>.onrender.com/api/v1

npx vercel --prod
```

---

## Phase 3: Post-Deployment Verification Checklist

After deploying both services, run through this quick checklist:

- [ ] **Open Vercel App**: Visit your Vercel deployment URL (`https://<your-project>.vercel.app`).
- [ ] **Map Visualization**: Verify that the MapLibre GL satellite map renders properly.
- [ ] **Project Switcher**: Switch between **Tehri Dam (Uttarakhand)** and **Chamoli Flash Flood (Rishi Ganga)** in the top navigation bar.
- [ ] **Run Fast SWE Simulation**: Click **Run Fast SWE (2D)** on the scenario drawer and verify the progress bar reaches 100%.
- [ ] **4D Timeline Playback**: Scrub the time-step slider or click **Play** to observe dynamic inundation propagation.
- [ ] **AI Decision Assistant**: Click the AI Assistant button and test a natural language query (e.g. *"What is the peak arrival time at Rishikesh?"*).

---

## Troubleshooting & FAQs

### 1. Render Free Tier Cold Starts
- **Symptom**: The first request after 15 minutes of inactivity takes 30–50 seconds to respond.
- **Cause**: Free tier instances on Render sleep when idle to conserve resources.
- **Solution**: Once the instance wakes up, all subsequent simulation and data requests respond instantly. For critical production use, upgrade to Render Starter plan ($7/mo) to keep the instance warm 24/7.

### 2. CORS Errors in Browser Console
- **Symptom**: `Access to fetch at '...' from origin 'https://your-app.vercel.app' has been blocked by CORS policy`.
- **Solution**: Check the `CORS_ORIGINS` environment variable in your Render dashboard. Ensure it contains `https://*.vercel.app` or your exact Vercel deployment URL (e.g., `https://your-app.vercel.app`).

### 3. Vercel Build Shows 404 on Root Directory
- **Symptom**: Vercel says `No Next.js version detected` during deployment.
- **Cause**: The Root Directory was left as root (`.`) instead of `frontend`.
- **Solution**: Go to your project on Vercel → **Settings** → **General** → **Root Directory** → Set to `frontend` → Click **Save** and trigger a redeploy.
