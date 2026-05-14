"""Run deterministic evaluation using WeatherBench 2's evaluate_in_memory.

Reads the three local Zarr artifacts (observations, climatology, forecast)
and writes a results NetCDF via the official WB2 evaluation pipeline.
RMSE is derived in post-processing as sqrt(MSE) in the analysis notebook.

Usage:
    uv run python pipeline/04_evaluate.py configs/bavaria_dev.yaml
"""

import dataclasses
import sys
from pathlib import Path

import numpy as np
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from weatherbench2 import config as wb2config
from weatherbench2.evaluation import evaluate_in_memory
from weatherbench2.metrics import ACC, MSE
from weatherbench2.regions import Region, SliceRegion


@dataclasses.dataclass
class UniformGridRegion(Region):
    """SliceRegion with correct area weights for a uniform latitude grid.

    WB2's get_lat_weights extends cell bounds to ±90° regardless of the
    input array, which gives wrong weights when data is pre-extracted to a
    spatial subregion.  This class recomputes bounds from the actual grid
    step so results match WB2's full-grid evaluation exactly for all
    non-polar interior points.
    """

    lat_slice: slice = dataclasses.field(default_factory=lambda: slice(None))
    lon_slice: slice = dataclasses.field(default_factory=lambda: slice(None))
    grid_step_deg: float = 1.5  # source grid spacing in degrees

    def apply(self, dataset, weights):
        ds = dataset.sel(latitude=self.lat_slice, longitude=self.lon_slice)
        lat_rad = np.deg2rad(ds.latitude.values)
        half = np.deg2rad(self.grid_step_deg / 2)
        areas = np.sin(lat_rad + half) - np.sin(lat_rad - half)
        w = xr.DataArray(
            areas / areas.mean(),
            dims=["latitude"],
            coords={"latitude": ds.latitude},
        )
        return ds, w

from wbgcp.config import ExperimentConfig
from wbgcp.paths import ProjPaths
import wbgcp.metadata as meta

CONFIG_PATH = sys.argv[1] if len(sys.argv) > 1 else "configs/bavaria_dev.yaml"

cfg = ExperimentConfig.from_yaml(CONFIG_PATH)
paths = ProjPaths()

# --- Load local climatology artifact -----------------------------------------
climatology = xr.open_zarr(str(paths.artifact_zarr("climatology", cfg.clim_artifact_id)))

# --- Configure WB2 evaluation -------------------------------------------------
eval_path = paths.evaluation_path(cfg.id)
eval_path.mkdir(parents=True, exist_ok=True)

r = cfg.region
pl_levels = [lv for v in cfg.variables.pressure_level for lv in v.levels] or None

data_config = wb2config.Data(
    selection=wb2config.Selection(
        variables=cfg.variables.all_names,
        levels=pl_levels,
        time_slice=slice(cfg.period.start, cfg.period.end),
    ),
    paths=wb2config.Paths(
        forecast=str(paths.artifact_zarr("forecasts", cfg.forecast_artifact_id)),
        obs=str(paths.artifact_zarr("observations", cfg.obs_artifact_id)),
        output_dir=str(eval_path),
    ),
)

eval_configs = {
    "deterministic": wb2config.Eval(
        metrics={
            "mse": MSE(),
            "acc": ACC(climatology=climatology),
        },
        regions={
            cfg.region.name: UniformGridRegion(
                lat_slice=slice(r.lat_min, r.lat_max),
                lon_slice=slice(r.lon_min, r.lon_max),
            ),
        },
    )
}

# --- Run evaluation -----------------------------------------------------------
print("Running evaluate_in_memory ...")
print(f"  Forecast : {data_config.paths.forecast}")
print(f"  Obs      : {data_config.paths.obs}")
print(f"  Output   : {eval_path}/deterministic.nc")

evaluate_in_memory(data_config, eval_configs)

meta.write(
    eval_path / "metadata.json",
    experiment_id=cfg.id,
    description=cfg.description,
    obs_artifact=cfg.obs_artifact_id,
    clim_artifact=cfg.clim_artifact_id,
    forecast_artifact=cfg.forecast_artifact_id,
    variables=cfg.variables.all_names,
    metrics=["mse", "acc"],
    output=str(eval_path / "deterministic.nc"),
)
print("Done.")
