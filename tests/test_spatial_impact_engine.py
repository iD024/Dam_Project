import pytest
import numpy as np
from backend.services.impact_service import compute_spatial_impacts
from backend.schemas.api_schemas import ImpactResponse

def test_spatial_impact_true_intersections_and_hazard_rating():
    # Setup 100x100 raster over bounds [78.45, 30.10, 78.65, 30.40]
    ny, nx = 100, 100
    bounds = [78.45, 30.10, 78.65, 30.40]
    
    # Create flood channel with max depth and arrival times
    max_depth = np.zeros((ny, nx), dtype=np.float32)
    arrival_time = np.full((ny, nx), -9999.0, dtype=np.float32)
    velocity = np.zeros((ny, nx), dtype=np.float32)
    
    # Centerline channel from row 20 to 80, col 45 to 55
    max_depth[20:80, 45:55] = 3.5  # 3.5m depth (Extreme/High hazard)
    arrival_time[20:80, 45:55] = 25.0  # 25 min arrival
    velocity[20:80, 45:55] = 4.0  # 4 m/s flow velocity

    # Create GeoJSON polygon for flood extent
    extent_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [78.54, 30.16],
                        [78.56, 30.16],
                        [78.56, 30.34],
                        [78.54, 30.34],
                        [78.54, 30.16]
                    ]]
                },
                "properties": {"zone": "severe", "max_depth_m": 3.5}
            }
        ]
    }

    # Exposure assets
    exposure_assets = [
        {
            "asset_type": "village",
            "name": "Test Riverside Village",
            "geom_geojson": {"type": "Point", "coordinates": [78.55, 30.25]},
            "properties": {"population": 2500},
        },
        {
            "asset_type": "road",
            "name": "River Arterial Highway",
            "geom_geojson": {
                "type": "LineString",
                "coordinates": [
                    [78.50, 30.25],
                    [78.60, 30.25],  # Crosses the flood zone (0.02 deg ~ 2km)
                ]
            },
            "properties": {"length_km": 10.0},
        },
        {
            "asset_type": "bridge",
            "name": "Valley Bridge",
            "geom_geojson": {"type": "Point", "coordinates": [78.55, 30.28]},
            "properties": {"span_m": 80.0},
        },
        {
            "asset_type": "hospital",
            "name": "Valley Clinic",
            "geom_geojson": {"type": "Point", "coordinates": [78.55, 30.22]},
            "properties": {"beds": 20},
        },
    ]

    result: ImpactResponse = compute_spatial_impacts(
        simulation_id="sim_test_001",
        extent_geojson=extent_geojson,
        max_depth_raster=max_depth,
        arrival_time_raster=arrival_time,
        exposure_assets=exposure_assets,
        bounds=bounds,
        max_velocity_raster=velocity,
    )

    # 1. Villages must include exact coordinates and hazard metrics
    assert result.affected_villages_count == 1
    village = result.affected_villages[0]
    assert village.name == "Test Riverside Village"
    assert village.coordinates == [78.55, 30.25]
    assert village.max_depth_m > 3.0
    assert village.peak_velocity_ms >= 3.5
    assert village.risk_level in ["CRITICAL", "HIGH"]
    assert village.hazard_rating is not None
    assert village.hazard_rating > 2.0  # HR = d*(v+0.5) + DF = 3.5*(4.0+0.5) + 0.5 = 16.25

    # 2. Road intersection must calculate inundated length > 0
    assert result.affected_roads_km > 0.0
    assert result.affected_roads_km < 10.0

    # 3. Critical assets
    assert result.affected_bridges_count == 1
    assert result.affected_hospitals_count == 1

    # 4. Overall metrics
    assert result.max_depth_m >= 3.5
    assert result.max_velocity_ms >= 4.0
    assert result.earliest_arrival_min == 25.0
