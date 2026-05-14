"""Extract forecast subset from WeatherBench 2.

Reads the specified model's forecast Zarr store from the public WB2 GCS bucket.

WB2 forecast structure: (time=init_time, prediction_timedelta, latitude, longitude)
Forecasts initialized at 00 and 12 UTC; lead times up to 240h in 6h steps.

Usage:
    uv run python pipeline/03_extract_forecast.py configs/bavaria_dev.yaml
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

zarr_path = paths.artifact_zarr("forecasts", cfg.forecast_artifact_id)
metadata_path = paths.artifact_metadata("forecasts", cfg.forecast_artifact_id)
zarr_path.parent.mkdir(parents=True, exist_ok=True)

# --- Open remote dataset ------------------------------------------------------
model_source = cfg.sources.for_model(cfg.model_name)
print(f"Opening {cfg.model_name} forecasts from: {model_source}")
fs = gcsfs.GCSFileSystem(token="anon")
store = fs.get_mapper(model_source)
ds_full = xr.open_zarr(store, consolidated=True)
print(f"\nFull forecast structure:\n{ds_full}\n")

# --- Select region and period -------------------------------------------------
# WB2 forecast datasets use 'time' for init time and 'prediction_timedelta'
# (integer hours) for lead time.
r = cfg.region
# Normalize longitude to -180..180 if source uses 0..360 convention.
if ds_full.longitude.values.max() > 180:
    ds_full = ds_full.assign_coords(
        longitude=((ds_full.longitude + 180) % 360 - 180)
    ).sortby("longitude")
ds = ds_full.sortby("latitude").sel(
    latitude=slice(r.lat_min, r.lat_max),
    longitude=slice(r.lon_min, r.lon_max),
    time=slice(cfg.period.start, cfg.period.end),
)

pl_map = cfg.variables.pressure_level_map
all_pl_levels = [lv for levels in pl_map.values() for lv in levels]

datasets = []
if cfg.variables.surface:
    datasets.append(ds[cfg.variables.surface])
if pl_map:
    datasets.append(ds[list(pl_map.keys())].sel(level=all_pl_levels))

ds_subset = xr.merge(datasets)
# Convert prediction_timedelta from integer hours to timedelta64 so WB2's
# schema.apply_time_conventions correctly computes valid_time = init + lead.
ds_subset = ds_subset.assign_coords(
    prediction_timedelta=pd.to_timedelta(ds_subset.prediction_timedelta.values, unit="h")
)
# Rechunk to uniform chunks and drop inherited encoding from the global source.
ds_subset = ds_subset.chunk(-1)
for var in list(ds_subset.data_vars) + list(ds_subset.coords):
    ds_subset[var].encoding = {}

init_times = pd.DatetimeIndex(ds_subset.time.values)
leads = ds_subset.prediction_timedelta.values  # timedelta64
lead_hours = [int(pd.Timedelta(lt).total_seconds() / 3600) for lt in leads]
print(f"Subset shape: {dict(ds_subset.dims)}")
print(f"Init times: {init_times[0]} → {init_times[-1]}  ({len(init_times)} runs)")
print(f"Lead times: {lead_hours[0]}h → {lead_hours[-1]}h  ({len(leads)} steps)")

# --- Save ---------------------------------------------------------------------
print(f"Saving to {zarr_path} ...")
ds_subset.to_zarr(str(zarr_path), mode="w")

meta.write(
    metadata_path,
    artifact_type="forecast",
    artifact_id=cfg.forecast_artifact_id,
    model=cfg.model_name,
    source=model_source,
    region=vars(r),
    period=vars(cfg.period),
    variables=list(ds_subset.data_vars),
    shape=dict(ds_subset.dims),
    n_init_times=len(init_times),
    lead_time_hours=lead_hours,
    data_path=str(zarr_path),
)
print("Done.")
