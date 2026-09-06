import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DEMO_DIR = DATA_DIR / "demo"
OUTPUT_DIR = DATA_DIR / "outputs"

# Ensure runtime directories exist
DATA_DIR.mkdir(exist_ok=True)
DEMO_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

def get_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS")
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return ["http://localhost:3000", "http://127.0.0.1:3000", "*"]

class Settings(BaseModel):
    PROJECT_NAME: str = "Dam-Break Inundation Modelling & AI Decision-Support Platform"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/dam_platform.db")
    CORS_ORIGINS: list[str] = get_cors_origins()
    DATA_DIR: Path = DATA_DIR
    DEMO_DIR: Path = DEMO_DIR
    OUTPUT_DIR: Path = OUTPUT_DIR
    DEFAULT_CRS: str = "EPSG:32644"  # UTM Zone 44N (Northern India / Himalayas)

settings = Settings()

