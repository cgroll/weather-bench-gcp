"""Extract climatology subset from WeatherBench 2.

The WB2 climatology represents 1990-2019 mean values for each hour of each
day of year — no period selection needed, the full annual cycle is stored.

Usage:
    uv run python pipeline/02_extract_climatology.py configs/bavaria_dev.yaml
"""

import sys
from pathlib import Path

import gcsfs
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wbgcp.config import ExperimentConfig
from wbgcp.paths import ProjPaths
import wbgcp.metadata as meta

CONFIG_PATH = sys.argv[1] if len(sys.argv) > 1 else "configs/bavaria_dev.yaml"

cfg = ExperimentConfig.from_yaml(CONFIG_PATH)
paths = ProjPaths()

zarr_path = paths.artifact_zarr("climatology", cfg.clim_artifact_id)
metadata_path = paths.artifact_metadata("climatology", cfg.clim_artifact_id)
zarr_path.parent.mkdir(parents=True, exist_ok=True)

# --- Open remote dataset ------------------------------------------------------
print(f"Opening climatology from: {cfg.sources.climatology}")
fs = gcsfs.GCSFileSystem(token="anon")
store = fs.get_mapper(cfg.sources.climatology)
ds_full = xr.open_zarr(store, consolidated=True)
print(f"\nFull climatology structure:\n{ds_full}\n")

# --- Select region and variables ----------------------------------------------
r = cfg.region
ds = ds_full.sortby("latitude").sel(
    latitude=slice(r.lat_min, r.lat_max),
    longitude=slice(r.lon_min, r.lon_max),
)

pl_map = cfg.variables.pressure_level_map
all_pl_levels = [lv for levels in pl_map.values() for lv in levels]

datasets = []
if cfg.variables.surface:
    datasets.append(ds[cfg.variables.surface])
if pl_map:
    datasets.append(ds[list(pl_map.keys())].sel(level=all_pl_levels))

ds_subset = xr.merge(datasets)
print(f"Subset shape: {dict(ds_subset.dims)}")

# --- Save ---------------------------------------------------------------------
print(f"Saving to {zarr_path} ...")
ds_subset.to_zarr(str(zarr_path), mode="w")

meta.write(
    metadata_path,
    artifact_type="climatology",
    artifact_id=cfg.clim_artifact_id,
    source=cfg.sources.climatology,
    region=vars(r),
    variables=list(ds_subset.data_vars),
    shape=dict(ds_subset.dims),
    data_path=str(zarr_path),
)
print("Done.")
