# Design Spec: Production Deployment on Vercel (Decoupled Architecture)

- **Date:** 2026-09-06
- **Status:** Approved
- **Topic:** Deploying Dam-Break Inundation & AI Platform on Vercel

## 1. Context & Objectives

The Dam-Break Inundation Simulation & AI Platform is a full-stack system composed of:
1. **Frontend (`frontend/`)**: Next.js 16 (React 19, Turbopack, Tailwind CSS v4, MapLibre GL).
2. **Backend (`backend/`)**: FastAPI Python service with SQLite database (`dam_platform.db`), hydrodynamic solvers (Fast 2D SWE, D-Flow FM, DualSPHysics), and AI services.

The goal is to deploy the Next.js frontend to **Vercel** with high performance, edge CDN, and automatic SSL, while ensuring the Python backend is easily deployable to a persistent cloud provider (such as Render, Railway, Fly.io, or VPS) with CORS configured to communicate with the Vercel domain.

---

## 2. Architecture & Components

```
┌────────────────────────────────────────────────────────┐
│                   Vercel Edge Network                  │
│  Next.js 16 App Router (React 19 + MapLibre GL)        │
│  Root Directory: frontend/                             │
│  Env: NEXT_PUBLIC_API_URL=https://<backend>/api/v1      │
└────────────────────────┬───────────────────────────────┘
                         │ HTTPS / REST (CORS enabled)
                         ▼
┌────────────────────────────────────────────────────────┐
│             Persistent Backend Cloud Host              │
│       (Render / Railway / Fly.io / Docker / VPS)       │
│                                                        │
│  - FastAPI Web API (Uvicorn)                           │
│  - Dynamic CORS via CORS_ORIGINS environment variable  │
│  - Persistent SQLite / volume for simulation data      │
│  - Hydrodynamic Engines (SWE / D-Flow / DualSPHysics)  │
└────────────────────────────────────────────────────────┘
```

---

## 3. Implementation Requirements

### A. Frontend Production Configuration
1. **`frontend/vercel.json`**:
   Ensure Next.js caching, clean build parameters, and security headers.
2. **`frontend/lib/api.ts`**:
   - Normalize `NEXT_PUBLIC_API_URL` to remove any accidental trailing slashes.
   - Enhance error handling with user-friendly diagnostics when the backend is waking up or unreachable (e.g. Render free-tier cold starts).

### B. Backend Production Readiness
1. **`backend/config.py`**:
   - Update `CORS_ORIGINS` to parse comma-separated values from the `CORS_ORIGINS` environment variable (e.g. `https://my-dam-app.vercel.app,http://localhost:3000`).
   - Retain default local development origins when unset.
2. **`requirements.txt`**:
   - Generate root `requirements.txt` pinning the runtime dependencies (`fastapi`, `uvicorn`, `pydantic`, `sqlalchemy`, `rasterio`, `shapely`, `scipy`, `numpy`, `optuna`, `httpx`).
3. **`Dockerfile` & `render.yaml`**:
   - Multi-stage Debian-based Dockerfile with GDAL/C++ runtime dependencies for rasterio and hydrodynamic computations.
   - `render.yaml` Infrastructure-as-Code manifest for 1-click backend deployment to Render.

### C. Comprehensive Deployment Guide
1. **`docs/DEPLOYMENT_GUIDE_VERCEL.md`**:
   - Crystal-clear, step-by-step walkthrough covering:
     - Part 1: Deploying the Backend (Render 1-click / Railway / Docker).
     - Part 2: Deploying the Frontend to Vercel (Dashboard & CLI workflows).
     - Part 3: Environment Variables & CORS configuration.
     - Part 4: Verification, testing, and troubleshooting cold starts.
2. Update root `README.md` and `frontend/README.md` with deployment quick-links.

---

## 4. Verification Plan
- **Frontend Build**: Run `npm --prefix frontend run build` to ensure zero compilation or TypeScript errors.
- **Backend Tests**: Run `.venv/bin/pytest` to verify all 18 test suites continue passing.
- **CORS Configuration Check**: Test `backend/config.py` with both default and custom `CORS_ORIGINS` strings.
