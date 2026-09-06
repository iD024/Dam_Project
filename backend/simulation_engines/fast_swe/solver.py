import math
import numpy as np
from pathlib import Path
from typing import Callable, Optional, Dict, Any, Tuple
from backend.schemas.scenario_contract import ScenarioContract
from backend.simulation_engines.base import SimulationEngine, ExecutionSummary

class FastSWE2DEngine(SimulationEngine):
    @property
    def name(self) -> str:
        return "fast_swe"

    def validate(self, scenario: ScenarioContract) -> Tuple[bool, list[str]]:
        errors = []
        if scenario.breach.bottom_width_m <= 0:
            errors.append("Breach bottom width must be greater than 0")
        if scenario.hydrology.initial_reservoir_level_m <= scenario.breach.bottom_elevation_m:
            errors.append("Initial reservoir level must be above breach bottom elevation")
        if scenario.numerics.simulation_duration_s <= 0:
            errors.append("Simulation duration must be greater than 0")
        return len(errors) == 0, errors

    def prepare(self, scenario: ScenarioContract, workdir: Path) -> Path:
        workdir.mkdir(parents=True, exist_ok=True)
        return workdir

    def _generate_or_load_dem(
        self,
        scenario: ScenarioContract,
        nx: int = 60,
        ny: int = 80,
    ) -> Tuple[np.ndarray, float, float, float, float, float, float]:
        """
        Loads DEM GeoTIFF or generates a realistic valley/gorge terrain model
        matching the study basin bounding box.
        """
        bbox = scenario.domain.bbox
        xmin, ymin, xmax, ymax = bbox

        is_chamoli = (
            "chamoli" in scenario.project_id.lower()
            or "rishi" in scenario.scenario_name.lower()
            or scenario.dam_id == "dam_tapovan_002"
        )
        if is_chamoli and (xmin < 79.0 or xmax < 79.0):
            xmin, ymin, xmax, ymax = 79.55, 30.45, 79.75, 30.58

        if (xmax - xmin) < 10.0:  # Geographic coordinates in degrees
            mid_lat = (ymin + ymax) / 2.0
            width_m = (xmax - xmin) * 111320.0 * math.cos(math.radians(mid_lat))
            height_m = (ymax - ymin) * 110574.0
            dx = max(width_m / nx, 15.0)
            dy = max(height_m / ny, 15.0)
        else:  # Projected metric coordinates
            dx = max((xmax - xmin) / nx, 15.0)
            dy = max((ymax - ymin) / ny, 15.0)

        # Check if DEM file exists (only load existing DEM if it matches active project)
        dem_path = Path(scenario.terrain.dem_uri)
        can_use_dem = dem_path.exists() and dem_path.suffix.lower() in [".tif", ".tiff"] and (not is_chamoli or "chamoli" in str(dem_path).lower())
        if can_use_dem:
            try:
                import rasterio
                with rasterio.open(dem_path) as src:
                    zb = src.read(1).astype(np.float64)
                    # Resample if needed
                    from scipy.ndimage import zoom
                    if zb.shape != (ny, nx):
                        zoom_y = ny / zb.shape[0]
                        zoom_x = nx / zb.shape[1]
                        zb = zoom(zb, (zoom_y, zoom_x), order=1)
                    return zb, dx, dy, xmin, ymin, xmax, ymax
            except Exception:
                pass

        # Generate realistic valley topography following the actual river corridor
        x = np.linspace(0, 1, nx)
        y = np.linspace(0, 1, ny)
        X, Y = np.meshgrid(x, y)

        # River and upstream reservoir corridor waypoints in EPSG:4326
        is_chamoli = (
            "chamoli" in scenario.project_id.lower()
            or "rishi" in scenario.scenario_name.lower()
            or scenario.dam_id == "dam_tapovan_002"
        )

        if is_chamoli:
            river_waypoints = [
                (79.7200, 30.4750),  # Upstream Glacial Origin
                (79.6950, 30.4900),  # Raini Village
                (79.6600, 30.5050),  # Tapovan Vishnugad Barrage
                (79.6300, 30.5150),  # NTPC Tunnel Worksite
                (79.6250, 30.5200),  # Dhauliganga Valley Gorge
                (79.6050, 30.5350),  # Lower Gorge
                (79.5850, 30.5500),  # Vishnuprayag Confluence
                (79.5750, 30.5600),  # Joshimath Canyon Floor
                (79.5650, 30.5550),  # Alaknanda Mainstream
            ]
        else:
            river_waypoints = [
                (78.5050, 30.3950),  # Upper Reservoir Bhagirathi Inflow
                (78.4900, 30.3880),  # Tehri Reservoir Lake Basin
                (78.4808, 30.3778),  # Tehri Dam (Breach Origin)
                (78.4720, 30.3650),  # Koti Colony
                (78.4850, 30.3520),  # Upper Gorge
                (78.4950, 30.3400),  # Malidewal
                (78.5080, 30.3200),  # Mid Valley Turn
                (78.5200, 30.3050),  # Chamba Valley Approach
                (78.5300, 30.2950),  # Khand
                (78.5480, 30.2680),  # Lower Gorge
                (78.5600, 30.2400),  # Chhiddarwala
                (78.5720, 30.2050),  # Canyon Approach
                (78.5860, 30.1700),  # Pre-Devprayag Canyon
                (78.5980, 30.1450),  # Devprayag Confluence
            ]

        # Convert river waypoints to local metric offsets
        m_per_deg_lon = width_m / max(xmax - xmin, 1e-6)
        m_per_deg_lat = height_m / max(ymax - ymin, 1e-6)
        r_m = np.array([((lon - xmin) * m_per_deg_lon, (lat - ymin) * m_per_deg_lat) for lon, lat in river_waypoints])
        segs = np.diff(r_m, axis=0)
        seg_lens = np.sqrt((segs**2).sum(axis=1))
        cum_dist = np.concatenate(([0], np.cumsum(seg_lens)))
        total_len = max(cum_dist[-1], 1.0)

        # 2D Grid in metric coordinates
        xs_m = np.linspace(0, width_m, nx)
        ys_m = np.linspace(height_m, 0, ny)  # Row 0 is North (ymax)
        X_grid_m, Y_grid_m = np.meshgrid(xs_m, ys_m)

        min_dist_m = np.full((ny, nx), 1e9)
        along_river_m = np.zeros((ny, nx))

        for k in range(len(segs)):
            p0 = r_m[k]
            v = segs[k]
            l2 = seg_lens[k] ** 2
            if l2 == 0:
                continue
            t = np.clip(((X_grid_m - p0[0]) * v[0] + (Y_grid_m - p0[1]) * v[1]) / l2, 0.0, 1.0)
            proj_x = p0[0] + t * v[0]
            proj_y = p0[1] + t * v[1]
            dist = np.sqrt((X_grid_m - proj_x) ** 2 + (Y_grid_m - proj_y) ** 2)
            mask = dist < min_dist_m
            min_dist_m[mask] = dist[mask]
            along_river_m[mask] = cum_dist[k] + t[mask] * seg_lens[k]

        # Riverbed drops ~230m from Tehri Dam down to Devprayag
        bed_bottom_el = scenario.breach.bottom_elevation_m - 15.0
        downstream_el = bed_bottom_el - 230.0
        base_slope = bed_bottom_el - (bed_bottom_el - downstream_el) * (along_river_m / total_len)

        # Himalayan mountain gorge: steep V-shaped canyon with 450m-700m canyon sidewalls
        # River channel is ~200-350m wide, then walls climb rapidly
        canyon_depth = 450.0 * (1.0 - np.exp(-(min_dist_m / 350.0) ** 2)) + 450.0 * np.maximum(0.0, (min_dist_m - 350.0) / 1000.0) ** 1.5
        zb = base_slope + canyon_depth

        return zb, dx, dy, xmin, ymin, xmax, ymax

    def run(
        self,
        scenario: ScenarioContract,
        workdir: Path,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> ExecutionSummary:
        sim_id = scenario.project_id
        if progress_callback:
            progress_callback(5.0, "Initializing computational grid and bathymetry")

        nx, ny = 75, 100
        zb, dx, dy, xmin, ymin, xmax, ymax = self._generate_or_load_dem(scenario, nx, ny)
        cell_area = dx * dy

        # Physical constants
        g = 9.81
        manning_n = scenario.roughness.default_manning_n
        dry_thresh = scenario.numerics.dry_threshold_m
        cfl = scenario.numerics.max_courant

        # State arrays: depth h (m), velocity u (m/s), velocity v (m/s)
        h = np.zeros((ny, nx), dtype=np.float64)
        u = np.zeros((ny, nx), dtype=np.float64)
        v = np.zeros((ny, nx), dtype=np.float64)

        # Dam location: mapped directly from geographic coordinates
        is_chamoli = (
            "chamoli" in scenario.project_id.lower()
            or "rishi" in scenario.scenario_name.lower()
            or scenario.dam_id == "dam_tapovan_002"
        )
        if is_chamoli:
            dam_lon = 79.6600
            dam_lat = 30.5050
        else:
            dam_lon = 78.4808
            dam_lat = 30.3778

        dam_j = int(np.clip((dam_lon - xmin) / (xmax - xmin) * nx, 1, nx - 2))
        dam_i = int(np.clip((ymax - dam_lat) / (ymax - ymin) * ny, 1, ny - 2))

        # Reservoir state
        reservoir_vol = scenario.hydrology.initial_storage_m3
        h_res = scenario.hydrology.initial_reservoir_level_m
        h_breach_bottom = scenario.breach.bottom_elevation_m
        t_form = scenario.breach.formation_time_s
        b_final = scenario.breach.bottom_width_m

        # Check for dynamic flash flood surge mode
        is_flash_flood = (
            scenario.flash_flood is not None
            and scenario.flash_flood.event_type in ["flash_flood", "cloudburst", "glof"]
        )

        # Inflow cell coordinates
        if is_flash_flood and is_chamoli:
            origin_lon, origin_lat = 79.7200, 30.4750
            inflow_j = int(np.clip((origin_lon - xmin) / (xmax - xmin) * nx, 1, nx - 2))
            inflow_i = int(np.clip((ymax - origin_lat) / (ymax - ymin) * ny, 1, ny - 2))
        else:
            inflow_j, inflow_i = dam_j, dam_i

        # Initialize upstream reservoir lake water body at T=0
        if is_chamoli:
            for r in range(dam_i, ny):
                for c in range(0, nx):
                    if zb[r, c] < h_res:
                        res_depth = min(h_res - zb[r, c], 40.0)
                        if res_depth > 0.5:
                            h[r, c] = res_depth
        else:
            for r in range(0, dam_i + 1):
                for c in range(0, nx):
                    if zb[r, c] < h_res:
                        res_depth = min(h_res - zb[r, c], 90.0)
                        if res_depth > 0.5:
                            h[r, c] = res_depth

        # Simulation time parameters
        total_duration = min(max(scenario.numerics.simulation_duration_s, 300.0), 7200.0)
        save_interval = max(scenario.numerics.output_interval_s, 60.0)
        n_saves = int(total_duration / save_interval) + 1

        # Diagnostic collectors
        history_times = []
        history_depth = []
        history_vel = []

        max_depth = np.zeros_like(h)
        max_velocity = np.zeros_like(h)
        arrival_time = np.full_like(h, np.nan)

        total_inflow_m3 = 0.0
        current_time = 0.0
        step = 0
        save_idx = 0

        # Save t=0 (with full standing reservoir lake)
        history_times.append(0.0)
        history_depth.append(h.copy())
        history_vel.append(np.zeros_like(h))

        if progress_callback:
            progress_callback(15.0, "Hydrodynamic solver running")

        while current_time < total_duration:
            # 1. Inflow hydrograph calculation
            if is_flash_flood:
                # Dynamic alpine cloudburst / GLOF surge wave hydrograph
                ff = scenario.flash_flood
                q_peak = ff.peak_discharge_m3s or 6500.0
                t_surge = ff.surge_duration_s or 1800.0
                t_peak = t_surge * 0.20
                if current_time <= t_surge:
                    t_norm = max(current_time / max(t_peak, 1.0), 1e-4)
                    q_breach = q_peak * (t_norm ** 2.2) * math.exp(-2.2 * (t_norm - 1.0))
                else:
                    q_breach = 0.0
            elif current_time >= scenario.breach.start_s and reservoir_vol > 0:
                t_rel = current_time - scenario.breach.start_s
                form_frac = min(1.0, t_rel / max(t_form, 1.0))
                
                # Progressive trapezoidal breach widening & deepening
                w_b = max(5.0, b_final * form_frac)
                z_b_curr = h_res - (h_res - h_breach_bottom) * form_frac
                head = max(0.0, h_res - z_b_curr)
                
                if head > 0:
                    # Broad-crested weir equation: Q = 1.7 * b * H^1.5
                    q_breach = 1.708 * w_b * (head ** 1.5)
                else:
                    q_breach = 0.0
            else:
                q_breach = 0.0

            # 2. Adaptive time-step via CFL condition
            celerity = np.sqrt(g * np.maximum(h, 0.0))
            max_vel_x = np.max(np.abs(u) + celerity)
            max_vel_y = np.max(np.abs(v) + celerity)
            max_speed = max(max_vel_x, max_vel_y, 0.5)
            dt = min(0.45 * min(dx, dy) / max_speed, 4.0)

            if current_time + dt > total_duration:
                dt = total_duration - current_time

            # Update reservoir storage depletion
            vol_released = q_breach * dt
            if not is_flash_flood:
                if vol_released > reservoir_vol:
                    vol_released = reservoir_vol
                    q_breach = vol_released / max(dt, 1e-6)
                reservoir_vol -= vol_released
            total_inflow_m3 += vol_released

            # Inject breach/inflow into source cell
            h[inflow_i, inflow_j] += (q_breach * dt) / cell_area

            # 3. Finite-Volume Shallow Water flux update (Rusanov / Local Lax-Friedrichs Flux)
            eta = zb + h  # Water surface elevation

            # Spatial gradients for momentum pressure/gravity (central difference on interior)
            d_eta_x = np.zeros_like(h)
            d_eta_y = np.zeros_like(h)
            d_eta_x[:, 1:-1] = (eta[:, 2:] - eta[:, :-2]) / (2.0 * dx)
            d_eta_y[1:-1, :] = (eta[2:, :] - eta[:-2, :]) / (2.0 * dy)

            # Mass flux across cell interfaces using Rusanov (Local Lax-Friedrichs) wave speed
            # X-direction interface flux
            qx = h * u
            cL_x = np.abs(u[:, :-1]) + np.sqrt(g * np.maximum(h[:, :-1], 0.0))
            cR_x = np.abs(u[:, 1:]) + np.sqrt(g * np.maximum(h[:, 1:], 0.0))
            wave_speed_x = np.maximum(cL_x, cR_x)
            flux_mass_x = 0.5 * (qx[:, 1:] + qx[:, :-1]) - 0.5 * wave_speed_x * (h[:, 1:] - h[:, :-1])

            # Y-direction interface flux
            qy = h * v
            cB_y = np.abs(v[:-1, :]) + np.sqrt(g * np.maximum(h[:-1, :], 0.0))
            cT_y = np.abs(v[1:, :]) + np.sqrt(g * np.maximum(h[1:, :], 0.0))
            wave_speed_y = np.maximum(cB_y, cT_y)
            flux_mass_y = 0.5 * (qy[1:, :] + qy[:-1, :]) - 0.5 * wave_speed_y * (h[1:, :] - h[:-1, :])

            # Update depth
            h_new = h.copy()
            h_new[:, 1:-1] -= (dt / dx) * (flux_mass_x[:, 1:] - flux_mass_x[:, :-1])
            h_new[1:-1, :] -= (dt / dy) * (flux_mass_y[1:, :] - flux_mass_y[:-1, :])
            h_new = np.nan_to_num(h_new, nan=0.0, posinf=0.0, neginf=0.0)
            h_new = np.maximum(0.0, h_new)

            # Momentum updates with gravity acceleration and Manning bed friction
            mask_wet = h_new > dry_thresh
            u_new = np.zeros_like(u)
            v_new = np.zeros_like(v)

            # Gravity acceleration along free surface slope
            u_star = u - g * dt * d_eta_x
            v_star = v - g * dt * d_eta_y

            # Downstream boundary free-drain condition
            v_star[-1, :] = np.maximum(v_star[-2, :], 0.0)

            # Semi-implicit Manning friction: u_next = u_star / (1 + dt * g * n^2 * |u| / h^(4/3))
            speed = np.sqrt(u_star**2 + v_star**2)
            friction_coeff = np.zeros_like(h)
            friction_coeff[mask_wet] = (g * (manning_n ** 2) * speed[mask_wet]) / (np.maximum(h_new[mask_wet], 0.05) ** (4.0 / 3.0))
            damping = 1.0 / (1.0 + dt * friction_coeff)

            u_new[mask_wet] = u_star[mask_wet] * damping[mask_wet]
            v_new[mask_wet] = v_star[mask_wet] * damping[mask_wet]

            # Enforce physical velocity limits (max 25 m/s)
            u_new = np.clip(u_new, -25.0, 25.0)
            v_new = np.clip(v_new, -25.0, 25.0)

            # Enforce boundary reflections/damping
            u_new[:, 0] = 0.0
            u_new[:, -1] = 0.0
            v_new[0, :] = 0.0

            # Commit new states
            h = h_new
            u = u_new
            v = v_new
            current_time += dt
            step += 1

            # Update cumulative maximums
            current_speed = np.sqrt(u**2 + v**2)
            max_depth = np.maximum(max_depth, h)
            max_velocity = np.maximum(max_velocity, current_speed)

            # Arrival time record: first instant where h > extent_threshold
            newly_wetted = (h > scenario.products.extent_threshold_m) & np.isnan(arrival_time)
            arrival_time[newly_wetted] = current_time / 60.0  # In minutes

            # Checkpoint save
            if current_time >= len(history_times) * save_interval:
                history_times.append(current_time)
                history_depth.append(h.copy())
                history_vel.append(current_speed.copy())
                if progress_callback:
                    pct = 15.0 + 65.0 * (current_time / total_duration)
                    progress_callback(pct, f"Solved t={int(current_time)}s / {int(total_duration)}s (Released: {int(total_inflow_m3/1e6)}M m³)")

        if progress_callback:
            progress_callback(85.0, "Hydrodynamics complete. Normalizing outputs")

        # Save numpy raw archive to workdir
        np.savez_compressed(
            workdir / "raw_simulation.npz",
            times=np.array(history_times),
            depths=np.array(history_depth),
            velocities=np.array(history_vel),
            max_depth=max_depth,
            max_velocity=max_velocity,
            arrival_time=arrival_time,
            zb=zb,
            extent=[xmin, ymin, xmax, ymax],
        )

        # Scientific QA verification: Mass Balance
        flooded_cells = np.count_nonzero(max_depth > scenario.products.extent_threshold_m)
        peak_flood_area_km2 = (flooded_cells * cell_area) / 1e6
        total_remaining_vol = float(np.sum(h) * cell_area)

        metrics = {
            "simulation_duration_s": current_time,
            "timesteps": step,
            "total_water_released_m3": float(total_inflow_m3),
            "peak_flooded_area_km2": float(peak_flood_area_km2),
            "max_depth_m": float(np.max(max_depth)),
            "max_velocity_ms": float(np.max(max_velocity)),
            "earliest_arrival_min": float(np.nanmin(arrival_time)) if not np.all(np.isnan(arrival_time)) else 0.0,
            "mass_balance_ratio": float(total_remaining_vol / max(total_inflow_m3, 1.0)),
        }

        return ExecutionSummary(
            simulation_id=sim_id,
            solver=self.name,
            exit_code=0,
            status="completed",
            metrics=metrics,
        )

    def parse_and_normalize(
        self,
        scenario: ScenarioContract,
        workdir: Path,
        out_dir: Path,
    ) -> Dict[str, Any]:
        """
        Normalizes raw solver arrays to GeoTIFF rasters and GeoJSON flood extent.
        """
        import rasterio
        from rasterio.transform import from_bounds

        data = np.load(workdir / "raw_simulation.npz")
        xmin, ymin, xmax, ymax = data["extent"]
        max_depth = data["max_depth"]
        max_velocity = data["max_velocity"]
        arrival_time = data["arrival_time"]
        ny, nx = max_depth.shape

        out_dir.mkdir(parents=True, exist_ok=True)
        transform = from_bounds(xmin, ymin, xmax, ymax, nx, ny)
        crs = scenario.domain.crs

        # 1. Write max_depth.tif
        max_depth_path = out_dir / "max_depth.tif"
        with rasterio.open(
            max_depth_path,
            "w",
            driver="GTiff",
            height=ny,
            width=nx,
            count=1,
            dtype=rasterio.float32,
            crs=crs,
            transform=transform,
            nodata=-9999.0,
        ) as dst:
            dst.write(max_depth.astype(np.float32), 1)

        # 2. Write max_velocity.tif
        max_vel_path = out_dir / "max_velocity.tif"
        with rasterio.open(
            max_vel_path,
            "w",
            driver="GTiff",
            height=ny,
            width=nx,
            count=1,
            dtype=rasterio.float32,
            crs=crs,
            transform=transform,
            nodata=-9999.0,
        ) as dst:
            dst.write(max_velocity.astype(np.float32), 1)

        # 3. Write arrival_time.tif
        arr_clean = np.where(np.isnan(arrival_time), -9999.0, arrival_time)
        arrival_path = out_dir / "arrival_time.tif"
        with rasterio.open(
            arrival_path,
            "w",
            driver="GTiff",
            height=ny,
            width=nx,
            count=1,
            dtype=rasterio.float32,
            crs=crs,
            transform=transform,
            nodata=-9999.0,
        ) as dst:
            dst.write(arr_clean.astype(np.float32), 1)

        # 4. Generate GeoJSON flood extent with depth tiers for MapLibre dynamic styling
        from shapely.geometry import box
        from shapely.ops import unary_union
        import json

        thresh = scenario.products.extent_threshold_m
        tiers = [
            ("shallow", thresh, 1.5, 1.0),
            ("moderate", 1.5, 3.0, 2.5),
            ("deep", 3.0, 5.0, 4.0),
            ("severe", 5.0, 1000.0, max(float(np.max(max_depth)), 6.0)),
        ]

        features = []
        for tier_name, t_low, t_high, rep_val in tiers:
            tier_polys = []
            for i in range(ny):
                for j in range(nx):
                    d = max_depth[i, j]
                    if t_low <= d < t_high or (t_high >= 1000.0 and d >= t_low):
                        c_xmin = xmin + j * ((xmax - xmin) / nx)
                        c_xmax = c_xmin + ((xmax - xmin) / nx)
                        c_ymax = ymax - i * ((ymax - ymin) / ny)
                        c_ymin = c_ymax - ((ymax - ymin) / ny)
                        tier_polys.append(box(c_xmin, c_ymin, c_xmax, c_ymax))
            if tier_polys:
                tier_geom = unary_union(tier_polys)
                try:
                    tier_geom = tier_geom.buffer(0.0012, quad_segs=4).buffer(-0.0012, quad_segs=4).simplify(0.0003, preserve_topology=True)
                except Exception:
                    pass
                features.append({
                    "type": "Feature",
                    "geometry": tier_geom.__geo_interface__,
                    "properties": {
                        "simulation_id": scenario.project_id,
                        "zone": tier_name,
                        "min_depth_m": t_low,
                        "max_depth_m": rep_val,
                    }
                })

        if not features:
            features.append({
                "type": "Feature",
                "geometry": {"type": "MultiPolygon", "coordinates": []},
                "properties": {"max_depth_m": 0.0}
            })

        extent_geojson_path = out_dir / "flood_extent.geojson"
        geojson_doc = {
            "type": "FeatureCollection",
            "features": features,
        }
        with open(extent_geojson_path, "w", encoding="utf-8") as f:
            json.dump(geojson_doc, f)

        # 5. Generate 4D time-step extent features for animation playback
        timeline_extents = {}
        if "depths" in data and len(data["depths"]) > 0:
            for s_idx, d_arr in enumerate(data["depths"]):
                s_features = []
                for tier_name, t_low, t_high, rep_val in tiers:
                    s_polys = []
                    for i in range(ny):
                        for j in range(nx):
                            d = d_arr[i, j]
                            if t_low <= d < t_high or (t_high >= 1000.0 and d >= t_low):
                                c_xmin = xmin + j * ((xmax - xmin) / nx)
                                c_xmax = c_xmin + ((xmax - xmin) / nx)
                                c_ymax = ymax - i * ((ymax - ymin) / ny)
                                c_ymin = c_ymax - ((ymax - ymin) / ny)
                                s_polys.append(box(c_xmin, c_ymin, c_xmax, c_ymax))
                    if s_polys:
                        s_geom = unary_union(s_polys)
                        try:
                            s_geom = s_geom.buffer(0.0012, quad_segs=4).buffer(-0.0012, quad_segs=4).simplify(0.0003, preserve_topology=True)
                        except Exception:
                            pass
                        s_features.append({
                            "type": "Feature",
                            "geometry": s_geom.__geo_interface__,
                            "properties": {
                                "step": s_idx,
                                "zone": tier_name,
                                "max_depth_m": rep_val,
                            }
                        })
                timeline_extents[str(s_idx)] = {
                    "type": "FeatureCollection",
                    "features": s_features,
                }

        with open(out_dir / "timeline_extents.json", "w", encoding="utf-8") as f:
            json.dump(timeline_extents, f)

        # 6. Write summary.json
        summary = {
            "simulation_id": scenario.project_id,
            "status": "completed",
            "solver": self.name,
            "crs": crs,
            "bounds": [xmin, ymin, xmax, ymax],
            "max_depth_m": float(np.max(max_depth)),
            "max_velocity_ms": float(np.max(max_velocity)),
            "peak_flooded_area_km2": float(np.count_nonzero(max_depth > thresh) * ((xmax - xmin) / nx) * ((ymax - ymin) / ny) / 1e6),
            "files": {
                "max_depth_tif": str(max_depth_path),
                "max_velocity_tif": str(max_vel_path),
                "arrival_time_tif": str(arrival_path),
                "flood_extent_geojson": str(extent_geojson_path),
            }
        }
        with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        return summary
