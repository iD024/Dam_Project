# Production Deployment on Vercel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide end-to-end production deployment readiness for Vercel (frontend) coupled with a persistent Python backend host (Render/Railway/Docker), including configuration, manifests, and a complete guide.

**Architecture:** Decoupled cloud architecture. Next.js 16 frontend deploys to Vercel's global Edge CDN, communicating via HTTPS REST with FastAPI backend running on a containerized or persistent Python host (Render/Railway) with persistent SQLite/volumes and dynamic CORS.

**Tech Stack:** Next.js 16 (React 19, Turbopack, Tailwind CSS v4, MapLibre GL), FastAPI, Python 3.12, Uvicorn, Docker, Render/Railway, Vercel.

**Spec:** `docs/superpowers/specs/2026-09-06-vercel-deployment-design.md`

## Global Constraints
- Python backend must preserve compatibility with Python 3.12 and all existing 18 pytest tests.
- Next.js build (`npm --prefix frontend run build`) must compile cleanly with 0 TypeScript/ESLint errors.
- CORS must allow Vercel production domains (`https://*.vercel.app`) as well as custom domains.
- No hardcoded external secrets; environment variables must be used for API base URLs and database paths.

---

### Task 1: Backend Production Readiness (CORS, Requirements & Dockerfile)

**Files:**
- Modify: `backend/config.py`
- Create: `requirements.txt`
- Create: `Dockerfile`
- Create: `render.yaml`
- Test: `tests/test_config_cors.py`

- [ ] **Step 1: Write test for dynamic CORS configuration**
  Test that `backend/config.py` correctly parses comma-separated origins from `os.environ["CORS_ORIGINS"]` and strips whitespace.

- [ ] **Step 2: Run test to verify it fails/passes**
  Run: `.venv/bin/pytest tests/test_config_cors.py -v`

- [ ] **Step 3: Update `backend/config.py`**
  Add dynamic parsing of `CORS_ORIGINS` from environment variable.

- [ ] **Step 4: Create `requirements.txt`, `Dockerfile`, and `render.yaml`**
  - Pin required packages (`fastapi`, `uvicorn`, `pydantic`, `sqlalchemy`, `rasterio`, `shapely`, `scipy`, `numpy`, `optuna`, `httpx`, `python-multipart`, `pyyaml`).
  - Create production-ready `Dockerfile` with GDAL/system libraries.
  - Create `render.yaml` for 1-click deploy to Render.

- [ ] **Step 5: Run tests and verify**
  Run: `.venv/bin/pytest` to ensure all tests pass.

---

### Task 2: Frontend Production Readiness for Vercel

**Files:**
- Create: `frontend/vercel.json`
- Modify: `frontend/lib/api.ts`
- Test: Frontend build with `npm --prefix frontend run build`

- [ ] **Step 1: Update `frontend/lib/api.ts`**
  Normalize `NEXT_PUBLIC_API_URL` to remove trailing slashes and guard against empty strings.

- [ ] **Step 2: Create `frontend/vercel.json`**
  Configure standard Next.js deployment headers and framework detection.

- [ ] **Step 3: Run production build verification**
  Run: `npm --prefix frontend run build` to verify clean build.

---

### Task 3: Comprehensive Vercel & Cloud Deployment Guide

**Files:**
- Create: `docs/DEPLOYMENT_GUIDE_VERCEL.md`
- Modify: `README.md` (or create if not present in root)
- Modify: `frontend/README.md`

- [ ] **Step 1: Write `docs/DEPLOYMENT_GUIDE_VERCEL.md`**
  Complete documentation covering:
  - Architecture overview & why decoupled deployment is used.
  - Quick Start: Step 1 (Backend on Render with 1-click or Railway).
  - Quick Start: Step 2 (Frontend on Vercel via GitHub or CLI).
  - Configuring Environment Variables (`NEXT_PUBLIC_API_URL`, `CORS_ORIGINS`).
  - Health check & Live verification procedures.
  - Troubleshooting tips (CORS errors, cold start delays, tile loading).

- [ ] **Step 2: Link guide in README files**
  Add deployment section to root `README.md` and `frontend/README.md`.
