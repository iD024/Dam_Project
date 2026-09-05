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
)
from backend.schemas.scenario_contract import ScenarioContract

def seed_database_if_empty():
    db = SessionLocal()
    try:
        if db.query(Project).first() is not None:
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
        rishi_proj = Project(
            id="proj_chamoli_002",
            name="Rishi Ganga Steep Mountain Flash Flood",
            description="Hydrodynamic routing of high-energy rock/ice surge in steep mountain gorge (Chamoli Disaster reference benchmark).",
        )
        db.add(rishi_proj)

        db.commit()
    finally:
        db.close()
