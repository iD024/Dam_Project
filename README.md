# Dam-Break Inundation Simulation & AI Decision-Support Platform

A state-of-the-art hydrodynamic simulation and AI-assisted emergency response platform designed for real-time flood modelling, breach parameter recommendation, and spatial impact assessment.

---

## System Architecture

The project consists of two core tiers:
1. **Frontend ([`frontend/`](frontend))**: Next.js 16 (React 19, Turbopack, Tailwind CSS v4, MapLibre GL) providing 4D temporal playback, scenario parameter controls, satellite observation overlays, and AI analytics dashboards.
2. **Backend ([`backend/`](backend))**: Python 3.12 FastAPI service with SQLite database, hydrodynamic solvers (Fast 2D SWE, D-Flow FM, DualSPHysics), surrogate machine learning models, and automated report generators.

---

## Local Development Quick Start

### 1. Backend Setup
```bash
# Activate virtual environment
source .venv/bin/activate

# Run test suite
pytest

# Launch FastAPI backend server
python -m uvicorn backend.main:app --reload --port 8000
```
Backend API interactive documentation will be available at `http://localhost:8000/docs`.

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` to interact with the platform.

---

## Production Deployment (Vercel & Render)

The system is architected for decoupled cloud deployment:
- **Frontend**: Deploy directly to **Vercel** with the Root Directory configured as `frontend`.
- **Backend**: Deploy to **Render** using the provided [`Dockerfile`](Dockerfile) and [`render.yaml`](render.yaml) blueprint.

👉 **Full Step-by-Step Instructions**: See the [Production Deployment Guide](docs/DEPLOYMENT_GUIDE_VERCEL.md).
