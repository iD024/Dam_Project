from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.database import init_db
from backend.services.seed_demo_data import seed_database_if_empty

from backend.api.projects import router as projects_router
from backend.api.scenarios import router as scenarios_router
from backend.api.simulations import router as simulations_router
from backend.api.validation import router as validation_router
from backend.api.ai import router as ai_router
from backend.api.exports import router as exports_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and demo seeds on startup
    init_db()
    seed_database_if_empty()
    yield

app = FastAPI(
    title="Dam-Break Flood Simulation & AI Decision-Support Platform",
    description="GIS-integrated hydrodynamic modelling (D-Flow FM, DualSPHysics, Fast 2D SWE) and decision support platform.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Dam-Break Inundation AI Platform",
        "version": "1.0.0",
        "supported_solvers": ["fast_swe", "dflowfm", "dualsphysics"],
    }

# Register API Routers under /api/v1
api_v1 = settings.API_V1_STR
app.include_router(projects_router, prefix=api_v1)
app.include_router(scenarios_router, prefix=api_v1)
app.include_router(simulations_router, prefix=api_v1)
app.include_router(validation_router, prefix=api_v1)
app.include_router(ai_router, prefix=api_v1)
app.include_router(exports_router, prefix=api_v1)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
