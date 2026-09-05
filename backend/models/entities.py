import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    dams = relationship("Dam", back_populates="project", cascade="all, delete-orphan")
    rivers = relationship("River", back_populates="project", cascade="all, delete-orphan")
    scenarios = relationship("Scenario", back_populates="project", cascade="all, delete-orphan")
    exposure_assets = relationship("ExposureAsset", back_populates="project", cascade="all, delete-orphan")
    datasets = relationship("Dataset", back_populates="project", cascade="all, delete-orphan")
    observed_floods = relationship("ObservedFlood", back_populates="project", cascade="all, delete-orphan")


class Dam(Base):
    __tablename__ = "dams"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    dam_type = Column(String(100), default="Embankment")
    crest_elevation_m = Column(Float, nullable=False)
    height_m = Column(Float, nullable=False)
    crest_length_m = Column(Float, nullable=True)
    reservoir_area_m2 = Column(Float, nullable=True)
    reservoir_storage_m3 = Column(Float, nullable=False)
    location_lon = Column(Float, nullable=False)
    location_lat = Column(Float, nullable=False)
    geom_geojson = Column(JSON, nullable=True)
    properties = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)

    project = relationship("Project", back_populates="dams")
    scenarios = relationship("Scenario", back_populates="dam")


class River(Base):
    __tablename__ = "rivers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    basin_name = Column(String(255), nullable=True)
    length_km = Column(Float, nullable=True)
    geom_geojson = Column(JSON, nullable=True)  # LineString or MultiLineString
    properties = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)

    project = relationship("Project", back_populates="rivers")
    scenarios = relationship("Scenario", back_populates="river")


class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    dam_id = Column(String(36), ForeignKey("dams.id", ondelete="SET NULL"), nullable=True)
    river_id = Column(String(36), ForeignKey("rivers.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="draft")  # draft, validated, ready
    engine_config = Column(JSON, nullable=False)  # Full ScenarioContract dict
    scenario_hash = Column(String(64), nullable=True)
    domain_geojson = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    project = relationship("Project", back_populates="scenarios")
    dam = relationship("Dam", back_populates="scenarios")
    river = relationship("River", back_populates="scenarios")
    simulations = relationship("Simulation", back_populates="scenario", cascade="all, delete-orphan")


class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    scenario_id = Column(String(36), ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False)
    solver = Column(String(50), nullable=False)  # fast_swe, dflowfm, dualsphysics
    solver_version = Column(String(50), default="1.0.0")
    status = Column(String(50), default="queued")  # queued, running, completed, failed
    progress_pct = Column(Float, default=0.0)
    current_phase = Column(String(100), default="initialized")
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    exit_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    log_uri = Column(String(500), nullable=True)
    work_dir = Column(String(500), nullable=True)
    metrics_summary = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)

    scenario = relationship("Scenario", back_populates="simulations")
    results = relationship("SimulationResult", back_populates="simulation", cascade="all, delete-orphan")
    validations = relationship("Validation", back_populates="simulation", cascade="all, delete-orphan")
    exports = relationship("ExportRecord", back_populates="simulation", cascade="all, delete-orphan")


class SimulationResult(Base):
    __tablename__ = "simulation_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    simulation_id = Column(String(36), ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False)
    product_type = Column(String(50), nullable=False)  # depth, velocity, max_depth, max_velocity, arrival_time, flood_extent
    file_path = Column(String(500), nullable=False)
    media_type = Column(String(50), default="image/tiff")
    crs = Column(String(50), default="EPSG:4326")
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    mean_value = Column(Float, nullable=True)
    bbox_geojson = Column(JSON, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)

    simulation = relationship("Simulation", back_populates="results")


class ExposureAsset(Base):
    __tablename__ = "exposure_assets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    asset_type = Column(String(50), nullable=False)  # village, road, building, bridge, hospital, school
    name = Column(String(255), nullable=True)
    source = Column(String(100), default="OSM")
    geom_type = Column(String(50), nullable=False)  # Point, LineString, Polygon
    geom_geojson = Column(JSON, nullable=False)
    properties = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)

    project = relationship("Project", back_populates="exposure_assets")


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    dataset_type = Column(String(50), nullable=False)  # dem, river_geometry, hydrology, landcover, satellite
    provider = Column(String(100), nullable=True)
    source_uri = Column(String(500), nullable=True)
    file_path = Column(String(500), nullable=True)
    checksum_sha256 = Column(String(64), nullable=True)
    crs = Column(String(50), default="EPSG:4326")
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)

    project = relationship("Project", back_populates="datasets")


class ObservedFlood(Base):
    __tablename__ = "observed_floods"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(100), default="Sentinel-1 SAR")
    acquisition_time = Column(DateTime, nullable=True)
    sensor = Column(String(50), default="Sentinel-1 GRD")
    mask_geojson = Column(JSON, nullable=True)  # MultiPolygon
    raster_path = Column(String(500), nullable=True)
    area_km2 = Column(Float, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)

    project = relationship("Project", back_populates="observed_floods")
    validations = relationship("Validation", back_populates="observed_flood")


class Validation(Base):
    __tablename__ = "validations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    simulation_id = Column(String(36), ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False)
    observed_flood_id = Column(String(36), ForeignKey("observed_floods.id", ondelete="CASCADE"), nullable=False)
    iou = Column(Float, nullable=False)
    csi = Column(Float, nullable=False)
    fpr = Column(Float, nullable=False)
    fnr = Column(Float, nullable=False)
    confusion_matrix = Column(JSON, default=dict)  # tp, fp, fn, tn
    metrics_summary = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)

    simulation = relationship("Simulation", back_populates="validations")
    observed_flood = relationship("ObservedFlood", back_populates="validations")


class ExportRecord(Base):
    __tablename__ = "exports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    simulation_id = Column(String(36), ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False)
    format = Column(String(20), nullable=False)  # shp, kml, geojson, geotiff
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, default=0)
    status = Column(String(50), default="completed")
    created_at = Column(DateTime, default=utc_now)

    simulation = relationship("Simulation", back_populates="exports")
