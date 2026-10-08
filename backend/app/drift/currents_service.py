from __future__ import annotations

import datetime
import json
import logging
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
import numpy as np

logger = logging.getLogger("ghostnet.cmems_currents")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_file = BASE_DIR / ".env"
if env_file.exists():
    load_dotenv(env_file)

CACHE_DIR = BASE_DIR / "data"
CACHE_FILE = CACHE_DIR / "cached_cmems_currents.json"
CACHE_TTL_HOURS = 6.0


def _load_disk_cache() -> Optional[Dict[str, Any]]:
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        cached_time = datetime.datetime.fromisoformat(data.get("timestamp", "2000-01-01T00:00:00+00:00"))
        now = datetime.datetime.now(datetime.timezone.utc)
        age_hours = (now - cached_time).total_seconds() / 3600.0
        if age_hours < CACHE_TTL_HOURS:
            logger.info("[CMEMS] Using fresh disk-cached ocean currents (age: %.1f hours)", age_hours)
            return data
    except Exception as e:
        logger.warning("[CMEMS] Failed to read disk cache: %s", e)
    return None


def _save_disk_cache(payload: Dict[str, Any]) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        logger.info("[CMEMS] Successfully cached %d vectors to %s", len(payload.get("vectors", [])), CACHE_FILE)
    except Exception as e:
        logger.warning("[CMEMS] Failed to write disk cache: %s", e)


def fetch_cmems_ocean_currents(
    force_refresh: bool = False,
    subsample_step: int = 8,
) -> Dict[str, Any]:
    """
    Retrieves real-time ocean surface current velocities (uo, vo) from
    Copernicus Marine Service (CMEMS) for the Indian Ocean basin.
    """
    if not force_refresh:
        cached = _load_disk_cache()
        if cached is not None and len(cached.get("vectors", [])) > 0:
            return cached

    username = os.environ.get("CMEMS_USERNAME", "")
    password = os.environ.get("CMEMS_PASSWORD", "")

    if not username or not password:
        logger.warning("[CMEMS] Credentials missing in environment; cannot fetch live currents")
        return {"source": "unavailable", "vectors": [], "count": 0}

    try:
        import copernicusmarine

        copernicusmarine.login(username=username, password=password)

        now = datetime.datetime.now(datetime.timezone.utc)
        yesterday = now - datetime.timedelta(days=2)
        start_str = yesterday.strftime("%Y-%m-%d")

        logger.info("[CMEMS] Querying Copernicus dataset cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m from %s...", start_str)

        ds = copernicusmarine.open_dataset(
            dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m",
            variables=["uo", "vo"],
            minimum_latitude=4.0,
            maximum_latitude=23.0,
            minimum_longitude=66.0,
            maximum_longitude=92.0,
            minimum_depth=0.5,
            maximum_depth=1.5,
            start_datetime=start_str,
        )

        # Most recent timestamp & surface layer
        latest_slice = ds.isel(time=-1, depth=0)
        lats = latest_slice["latitude"].values[::subsample_step]
        lons = latest_slice["longitude"].values[::subsample_step]
        uo = latest_slice["uo"].values[::subsample_step, ::subsample_step]
        vo = latest_slice["vo"].values[::subsample_step, ::subsample_step]

        vectors: List[Dict[str, Any]] = []
        scale_factor = 0.85  # visual trajectory vector scale

        for i, lat_val in enumerate(lats):
            for j, lon_val in enumerate(lons):
                u_val = float(uo[i, j])
                v_val = float(vo[i, j])
                if np.isnan(u_val) or np.isnan(v_val):
                    continue

                speed = float(np.sqrt(u_val**2 + v_val**2))
                if speed < 0.015:
                    continue  # Filter near-zero stagnant / coastal mask cells

                lon_f = round(float(lon_val), 3)
                lat_f = round(float(lat_val), 3)

                # Determine oceanic region tag
                region = "Indian Ocean"
                if lon_f < 77.5 and lat_f >= 7.5:
                    region = "Arabian Sea"
                elif lon_f >= 78.0 and lat_f >= 7.5:
                    region = "Bay of Bengal"
                elif lat_f < 7.5:
                    region = "Equatorial Indian Ocean"

                vectors.append(
                    {
                        "from": [lon_f, lat_f],
                        "to": [
                            round(lon_f + u_val * scale_factor, 3),
                            round(lat_f + v_val * scale_factor, 3),
                        ],
                        "speed": round(speed, 3),
                        "u": round(u_val, 3),
                        "v": round(v_val, 3),
                        "region": region,
                    }
                )

        payload = {
            "source": "Copernicus Marine Service (CMEMS)",
            "dataset_id": "cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m",
            "timestamp": now.isoformat(),
            "count": len(vectors),
            "vectors": vectors,
        }

        _save_disk_cache(payload)
        return payload

    except Exception as e:
        logger.error("[CMEMS] Failed to fetch live ocean currents: %s", e)
        # If cache exists (even expired), return it as fallback
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"source": "error", "error": str(e), "vectors": [], "count": 0}
