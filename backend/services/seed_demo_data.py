import json
from pathlib import Path
from backend.database import SessionLocal
from backend.models import (
    Project,
    Dam,
    River,
    Scenario,
    ExposureAsset,
    Dataset,
    ObservedFlood,
    Simulation,
    SimulationResult,
)
from backend.schemas.scenario_contract import ScenarioContract

def seed_database_if_empty():
    db = SessionLocal()
    try:
        if db.query(Project).first() is not None:
            seed_rishi_ganga_project(db)
            return

        # 1. Create Demonstration Project: Tehri Dam Flood Analysis
        tehri_proj = Project(
            id="proj_tehri_001",
            name="Tehri Dam-Break & Bhagirathi Inundation Study",
            description="Physics-based dam-break simulation and HADR impact assessment for Tehri Dam on the Bhagirathi River down to Devprayag confluence.",
        )
        db.add(tehri_proj)
        db.flush()

        # 2. Add Dam
        tehri_dam = Dam(
            id="dam_tehri_001",
            project_id=tehri_proj.id,
            name="Tehri Dam",
            dam_type="Earth and Rockfill Embankment",
            crest_elevation_m=839.5,
            height_m=260.5,
            crest_length_m=575.0,
            reservoir_storage_m3=3.54e9, # 3.54 Billion m3
            location_lon=78.4808,
            location_lat=30.3778,
            properties={
                "state": "Uttarakhand",
                "district": "Tehri Garhwal",
                "river": "Bhagirathi",
                "completion_year": 2006,
                "power_capacity_mw": 1000,
            },
        )
        db.add(tehri_dam)

        # 3. Add River
        bhagirathi_river = River(
            id="riv_bhagirathi_001",
            project_id=tehri_proj.id,
            name="Bhagirathi River",
            basin_name="Ganga Basin",
            length_km=205.0,
            properties={
                "origin": "Gaumukh / Gangotri Glacier",
                "confluence": "Devprayag (meets Alaknanda to form Ganga)",
            },
        )
        db.add(bhagirathi_river)

        # 4. Add Exposure Assets (Villages, Roads, Infrastructure)
        villages = [
            ("Koti Colony", 78.4720, 30.3650, 1850, "Settlement directly downstream of spillway"),
            ("Malidewal", 78.4950, 30.3400, 920, "Riverside village community"),
            ("Khand", 78.5300, 30.2950, 1400, "Agriculture and residential cluster"),
            ("Chhiddarwala", 78.5600, 30.2400, 2100, "Valley floor settlement"),
            ("Devprayag", 78.5980, 30.1450, 4500, "Historic confluence town with Alaknanda River"),
        ]
        for name, lon, lat, pop, desc in villages:
            asset = ExposureAsset(
                project_id=tehri_proj.id,
                asset_type="village",
                name=name,
                source="OpenStreetMap / Census of India",
                geom_type="Point",
                geom_geojson={"type": "Point", "coordinates": [lon, lat]},
                properties={"population": pop, "description": desc},
            )
            db.add(asset)

        # Roads
        road_asset = ExposureAsset(
            project_id=tehri_proj.id,
            asset_type="road",
            name="NH-58 / Badrinath National Highway & Valley Arterial",
            source="OpenStreetMap",
            geom_type="LineString",
            geom_geojson={
                "type": "LineString",
                "coordinates": [
                    [78.480, 30.370],
                    [78.490, 30.345],
                    [78.520, 30.300],
                    [78.550, 30.250],
                    [78.595, 30.150],
                ]
            },
            properties={"length_km": 42.5, "classification": "National Highway"},
        )
        db.add(road_asset)

        # Bridges & Critical Infrastructure
        db.add(ExposureAsset(
            project_id=tehri_proj.id,
            asset_type="bridge",
            name="Devprayag Confluence Suspension Bridge",
            source="OpenStreetMap",
            geom_type="Point",
            geom_geojson={"type": "Point", "coordinates": [78.599, 30.146]},
            properties={"span_m": 120.0},
        ))
        db.add(ExposureAsset(
            project_id=tehri_proj.id,
            asset_type="hospital",
            name="Community Health Centre Devprayag",
            source="OpenStreetMap",
            geom_type="Point",
            geom_geojson={"type": "Point", "coordinates": [78.597, 30.148]},
            properties={"beds": 45},
        ))

        # 5. Add Scenario Contract
        scenario_contract = {
            "schema_version": "1.0.0",
            "project_id": tehri_proj.id,
            "dam_id": tehri_dam.id,
            "river_id": bhagirathi_river.id,
            "scenario_name": "Tehri Sudden Overtopping Breach (PMP Probable Maximum Flood)",
            "description": "Standard dam-break scenario evaluating downstream wave travel time and flood inundation under extreme monsoon inflow.",
            "domain": {
                "bbox": [78.45, 30.12, 78.65, 30.40],
                "crs": "EPSG:4326"
            },
            "terrain": {
                "dem_uri": "data/demo/tehri/dem_tehri.tif",
                "resolution_m": 30.0,
                "vertical_datum": "EGM2008",
                "conditioning": {
                    "burn_river": True,
                    "fill_sinks": False,
                    "preserve_structures": True
                }
            },
            "hydrology": {
                "initial_reservoir_level_m": 820.0,
                "initial_storage_m3": 2.4e9,
                "upstream_q_m3s": 1500.0,
                "downstream_bc": {
                    "type": "normal_depth",
                    "slope": 0.002
                }
            },
            "roughness": {
                "source": "landcover",
                "default_manning_n": 0.042
            },
            "breach": {
                "type": "trapezoidal_progressive",
                "failure_mode": "overtopping",
                "start_s": 0.0,
                "formation_time_s": 240.0,
                "bottom_width_m": 95.0,
                "top_width_m": 140.0,
                "side_slope_hv": 1.0,
                "bottom_elevation_m": 750.0,
                "hydrograph_model": "weir_dynamic"
            },
            "solvers": ["fast_swe", "dflowfm"],
            "numerics": {
                "simulation_duration_s": 600.0,
                "output_interval_s": 60.0,
                "max_courant": 0.85,
                "dry_threshold_m": 0.02
            },
            "products": {
                "depth": True,
                "velocity": True,
                "arrival_time": True,
                "duration": True,
                "extent_threshold_m": 0.10
            },
            "provenance": {
                "created_by": "National Dam Safety Authority Template",
                "datasets": ["cop-dem-glo-30", "osm-uttarakhand", "india-wris"]
            }
        }

        scenario = Scenario(
            id="scen_tehri_001",
            project_id=tehri_proj.id,
            dam_id=tehri_dam.id,
            river_id=bhagirathi_river.id,
            name="Tehri Probable Maximum Flood Breach",
            description="Sudden overtopping failure with empirical Froehlich breach progression.",
            status="validated",
            engine_config=scenario_contract,
        )
        db.add(scenario)

        # 6. Add Observed Satellite Flood dataset (Sentinel-1 SAR)
        obs_flood = ObservedFlood(
            id="obs_flood_tehri_001",
            project_id=tehri_proj.id,
            source="Sentinel-1 SAR IW GRD",
            sensor="Sentinel-1 C-band SAR",
            area_km2=28.4,
            metadata_json={
                "polarization": "VV+VH",
                "processing": "Google Earth Engine Otsu Thresholding",
                "orbit": "DESCENDING",
            }
        )
        db.add(obs_flood)

        # 7. Add Rishi Ganga Case Study (Case A from architecture report)
        seed_rishi_ganga_project(db)
        db.commit()
    finally:
        db.close()

def seed_rishi_ganga_project(db):
    rishi_proj = db.query(Project).filter(Project.id == "proj_chamoli_002").first()
    if not rishi_proj:
        rishi_proj = Project(
            id="proj_chamoli_002",
            name="Rishi Ganga Steep Mountain Flash Flood",
            description="Hydrodynamic routing of high-energy rock/ice surge in steep mountain gorge (Chamoli Disaster reference benchmark).",
        )
        db.add(rishi_proj)
        db.flush()

    # Add Tapovan Barrage
    tapovan_dam = db.query(Dam).filter(Dam.id == "dam_tapovan_002").first()
    if not tapovan_dam:
        tapovan_dam = Dam(
            id="dam_tapovan_002",
            project_id=rishi_proj.id,
            name="Tapovan Vishnugad Barrage",
            dam_type="Concrete Gravity Barrage",
            crest_elevation_m=1803.0,
            height_m=22.0,
            crest_length_m=200.0,
            reservoir_storage_m3=1.45e7,
            location_lon=79.6300,
            location_lat=30.5150,
            properties={
                "state": "Uttarakhand",
                "district": "Chamoli",
                "river": "Dhauliganga",
                "power_capacity_mw": 520,
            },
        )
        db.add(tapovan_dam)

    # Add River
    rishi_river = db.query(River).filter(River.id == "riv_rishi_002").first()
    if not rishi_river:
        rishi_river = River(
            id="riv_rishi_002",
            project_id=rishi_proj.id,
            name="Rishi Ganga & Dhauliganga River",
            basin_name="Alaknanda Basin",
            length_km=55.0,
            properties={"confluence": "Vishnuprayag"},
        )
        db.add(rishi_river)

    # Add Exposure Assets
    if db.query(ExposureAsset).filter(ExposureAsset.project_id == rishi_proj.id).first() is None:
        chamoli_villages = [
            ("Raini Village", 79.6950, 30.4900, 450, "Historic Chipko movement riverside village"),
            ("Tapovan Barrage Worksite", 79.6300, 30.5150, 180, "Barrage structure and maintenance depot"),
            ("NTPC Head Race Tunnel", 79.6250, 30.5200, 120, "Tunnel intake portal workforce zone"),
            ("Vishnuprayag Confluence", 79.5750, 30.5600, 850, "Dhauliganga-Alaknanda confluence settlement"),
            ("Joshimath Lower Terraces", 79.5650, 30.5550, 3200, "High altitude Himalayan valley gateway"),
        ]
        for name, lon, lat, pop, desc in chamoli_villages:
            db.add(ExposureAsset(
                project_id=rishi_proj.id,
                asset_type="village",
                name=name,
                source="OpenStreetMap / Census of India",
                geom_type="Point",
                geom_geojson={"type": "Point", "coordinates": [lon, lat]},
                properties={"population": pop, "description": desc},
            ))

        db.add(ExposureAsset(
            project_id=rishi_proj.id,
            asset_type="road",
            name="Joshimath-Malari Border Road (NH-107B)",
            source="OpenStreetMap",
            geom_type="LineString",
            geom_geojson={
                "type": "LineString",
                "coordinates": [
                    [79.700, 30.485],
                    [79.650, 30.510],
                    [79.600, 30.540],
                    [79.570, 30.560],
                ]
            },
            properties={"length_km": 28.5, "classification": "Border Highway"},
        ))

        db.add(ExposureAsset(
            project_id=rishi_proj.id,
            asset_type="bridge",
            name="Raini Gorge Motor Bridge",
            source="OpenStreetMap",
            geom_type="Point",
            geom_geojson={"type": "Point", "coordinates": [79.694, 30.491]},
            properties={"span_m": 65.0},
        ))

    # Add Scenario with Flash Flood Config
    rishi_contract = {
        "schema_version": "1.0.0",
        "project_id": rishi_proj.id,
        "dam_id": "dam_tapovan_002",
        "river_id": "riv_rishi_002",
        "scenario_name": "Rishi Ganga High-Energy Alpine Flash Flood & GLOF Surge",
        "description": "Hydrodynamic routing of extreme rock/ice avalanche and flash flood surge down Rishi Ganga gorge to Vishnuprayag.",
        "domain": {
            "bbox": [79.55, 30.45, 79.75, 30.58],
            "crs": "EPSG:4326"
        },
        "terrain": {
            "dem_uri": "data/demo/tehri/dem_tehri.tif",
            "resolution_m": 30.0,
        },
        "hydrology": {
            "initial_reservoir_level_m": 1800.0,
            "initial_storage_m3": 1.45e7,
        },
        "roughness": {
            "source": "landcover",
            "default_manning_n": 0.055
        },
        "breach": {
            "type": "trapezoidal_progressive",
            "failure_mode": "overtopping",
            "bottom_width_m": 60.0,
            "top_width_m": 90.0,
            "bottom_elevation_m": 1780.0,
        },
        "flash_flood": {
            "event_type": "flash_flood",
            "rainfall_intensity_mmh": 125.0,
            "catchment_area_km2": 320.0,
            "runoff_coefficient": 0.85,
            "peak_discharge_m3s": 8500.0,
            "surge_duration_s": 2400.0,
        },
        "solvers": ["fast_swe", "dflowfm", "dualsphysics"],
        "numerics": {
            "simulation_duration_s": 600.0,
            "output_interval_s": 60.0,
            "max_courant": 0.85,
            "dry_threshold_m": 0.02,
        },
        "products": {
            "depth": True,
            "velocity": True,
            "arrival_time": True,
            "duration": True,
            "extent_threshold_m": 0.10,
        },
    }

    rishi_scenario = db.query(Scenario).filter(Scenario.id == "scen_rishi_002").first()
    if not rishi_scenario:
        rishi_scenario = Scenario(
            id="scen_rishi_002",
            project_id=rishi_proj.id,
            dam_id="dam_tapovan_002",
            river_id="riv_rishi_002",
            name="Rishi Ganga High-Energy Alpine Flash Flood & GLOF Surge",
            description="Dynamic flash flood surge propagation modeled with high peak discharge (8,500 m3/s).",
            status="validated",
            engine_config=rishi_contract,
        )
        db.add(rishi_scenario)
    else:
        rishi_scenario.engine_config = rishi_contract

    # Add Observed Satellite Flood
    if db.query(ObservedFlood).filter(ObservedFlood.project_id == rishi_proj.id).first() is None:
        db.add(ObservedFlood(
            id="obs_flood_chamoli_002",
            project_id=rishi_proj.id,
            source="Sentinel-1 SAR IW GRD",
            sensor="Sentinel-1 C-band SAR",
            area_km2=19.8,
            metadata_json={
                "polarization": "VV+VH",
                "processing": "Google Earth Engine Otsu Thresholding",
                "event": "Chamoli Flash Flood SAR detection",
            }
        ))
    db.commit()

    # Ensure baseline completed simulation for Chamoli exists with valid Chamoli coordinates
    from backend.config import settings
    from backend.simulation_engines.fast_swe.solver import FastSWE2DEngine
    from backend.services.impact_service import compute_spatial_impacts
    from datetime import datetime, timezone
    import numpy as np

    sim_id = "sim_chamoli_demo_002"
    sim_rec = db.query(Simulation).filter(Simulation.id == sim_id).first()
    results_dir = settings.OUTPUT_DIR / sim_id / "results"
    workdir = settings.OUTPUT_DIR / sim_id / "work"
    geojson_path = results_dir / "flood_extent.geojson"

    needs_sim_gen = not sim_rec or not geojson_path.exists()
    if not needs_sim_gen and geojson_path.exists():
        try:
            with open(geojson_path) as f:
                geo_check = json.load(f)
                if not geo_check.get("features"):
                    needs_sim_gen = True
                else:
                    first_coord = geo_check["features"][0]["geometry"]["coordinates"]
                    sample_lon = first_coord[0][0][0] if isinstance(first_coord[0][0][0], (int, float)) else first_coord[0][0][0][0]
                    if sample_lon < 79.5:
                        needs_sim_gen = True
        except Exception:
            needs_sim_gen = True

    if needs_sim_gen:
        workdir.mkdir(parents=True, exist_ok=True)
        results_dir.mkdir(parents=True, exist_ok=True)

        contract = ScenarioContract(**rishi_contract)
        engine = FastSWE2DEngine()
        engine.prepare(contract, workdir)
        exec_summary = engine.run(contract, workdir)
        norm_summary = engine.parse_and_normalize(contract, workdir, results_dir)

        assets = db.query(ExposureAsset).filter(ExposureAsset.project_id == rishi_proj.id).all()
        asset_dicts = [
            {"asset_type": a.asset_type, "name": a.name, "geom_geojson": a.geom_geojson, "properties": a.properties}
            for a in assets
        ]
        sim_data = np.load(workdir / "raw_simulation.npz")
        with open(geojson_path) as f:
            extent_geojson = json.load(f)

        impact_data = compute_spatial_impacts(
            simulation_id=sim_id,
            extent_geojson=extent_geojson,
            max_depth_raster=sim_data["max_depth"],
            arrival_time_raster=sim_data["arrival_time"],
            exposure_assets=asset_dicts,
            bounds=sim_data["extent"].tolist(),
            max_velocity_raster=sim_data.get("max_velocity"),
        )

        metrics = exec_summary.metrics
        metrics["impact"] = impact_data.model_dump()

        if not sim_rec:
            sim_rec = Simulation(
                id=sim_id,
                scenario_id="scen_rishi_002",
                solver="fast_swe",
                solver_version="1.0.0",
                status="completed",
                progress_pct=100.0,
                current_phase="Simulation finished successfully",
                work_dir=str(workdir),
                metrics_summary=metrics,
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
            )
            db.add(sim_rec)
        else:
            sim_rec.status = "completed"
            sim_rec.metrics_summary = metrics
            sim_rec.finished_at = datetime.now(timezone.utc)

        for ptype in ["max_depth", "max_velocity", "arrival_time"]:
            tif_file = results_dir / f"{ptype}.tif"
            if tif_file.exists() and db.query(SimulationResult).filter(SimulationResult.simulation_id == sim_id, SimulationResult.product_type == ptype).first() is None:
                db.add(SimulationResult(
                    simulation_id=sim_id,
                    product_type=ptype,
                    file_path=str(tif_file),
                    media_type="image/tiff",
                    crs=contract.domain.crs,
                    min_value=0.0,
                    max_value=float(metrics.get(f"{ptype}_m", 10.0)),
                ))

        # Delete any previous broken simulations for scen_rishi_002
        db.query(Simulation).filter(Simulation.scenario_id == "scen_rishi_002", Simulation.id != sim_id).delete()
        db.commit()

