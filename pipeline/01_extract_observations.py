"""Extract ERA5 observation subset from WeatherBench 2.

Reads the public WB2 ERA5 Zarr store (anonymous GCS access) and writes
a local Zarr artifact for the configured region and period.

Usage:
    uv run python pipeline/01_extract_observations.py configs/bavaria_dev.yaml
"""

import sys
from pathlib import Path

import gcsfs
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wbgcp.config import ExperimentConfig
from wbgcp.paths import ProjPaths
import wbgcp.metadata as meta

CONFIG_PATH = sys.argv[1] if len(sys.argv) > 1 else "configs/bavaria_dev.yaml"

cfg = ExperimentConfig.from_yaml(CONFIG_PATH)
paths = ProjPaths()

zarr_path = paths.artifact_zarr("observations", cfg.obs_artifact_id)
metadata_path = paths.artifact_metadata("observations", cfg.obs_artifact_id)
zarr_path.parent.mkdir(parents=True, exist_ok=True)

# --- Open remote dataset ------------------------------------------------------
print(f"Opening ERA5 from: {cfg.sources.era5}")
fs = gcsfs.GCSFileSystem(token="anon")
store = fs.get_mapper(cfg.sources.era5)
ds_full = xr.open_zarr(store, consolidated=True)
print(f"\nFull dataset structure:\n{ds_full}\n")

# --- Select region and period -------------------------------------------------
# Obs must cover all forecast valid times: extend end by max_lead_hours so the
# WB2 evaluator can align truth to every (init_time + lead_time) step.
r = cfg.region
obs_end = (
    pd.Timestamp(cfg.period.end)
    + pd.Timedelta(days=1)           # cover inits at any hour of the last day
    + pd.Timedelta(hours=cfg.period.max_lead_hours)
).isoformat()
ds = ds_full.sortby("latitude").sel(
    latitude=slice(r.lat_min, r.lat_max),
    longitude=slice(r.lon_min, r.lon_max),
    time=slice(cfg.period.start, obs_end),
)

pl_map = cfg.variables.pressure_level_map
all_pl_levels = [lv for levels in pl_map.values() for lv in levels]

datasets = []
if cfg.variables.surface:
    datasets.append(ds[cfg.variables.surface])
if pl_map:
    datasets.append(ds[list(pl_map.keys())].sel(level=all_pl_levels))

ds_subset = xr.merge(datasets)
# Rechunk to uniform chunks and drop inherited encoding from the global source.
# The subset is small enough that a single chunk per dim is fine and avoids
# the Zarr "non-uniform chunks" error caused by partial boundary chunks.
ds_subset = ds_subset.chunk(-1)
for var in list(ds_subset.data_vars) + list(ds_subset.coords):
    ds_subset[var].encoding = {}

print(f"Subset shape: {dict(ds_subset.dims)}")
print(f"Time range: {ds_subset.time.values[[0, -1]]}")

# --- Save ---------------------------------------------------------------------
print(f"Saving to {zarr_path} ...")
ds_subset.to_zarr(str(zarr_path), mode="w")

meta.write(
    metadata_path,
    artifact_type="observations",
    artifact_id=cfg.obs_artifact_id,
    source=cfg.sources.era5,
    region=vars(r),
    period=vars(cfg.period),
    variables=list(ds_subset.data_vars),
    shape=dict(ds_subset.dims),
    data_path=str(zarr_path),
)
print("Done.")
