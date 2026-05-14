# ---
# jupytext:
#   text_representation:
#     format_name: percent
# kernelspec:
#   display_name: Python 3
#   language: python
#   name: python3
# ---

# %% [markdown]
# # WeatherBench 2 Evaluation — Europe 2022
#
# RMSE and ACC vs. lead time for Pangu-Weather forecasts evaluated
# against ERA5 over Europe (full year 2022, 240x121 grid).
# Variables: Z500 (geopotential at 500 hPa, m²/s²) and 2 m temperature (K).
#
# Metrics were produced by `weatherbench2.evaluation.evaluate_in_memory`.
# RMSE is derived here as sqrt(MSE).

# %%
import fsspec
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
from wbgcp.paths import ProjPaths
from wbgcp.config import ExperimentConfig

paths = ProjPaths()
paths.ensure_directories()
cfg = ExperimentConfig.from_yaml(paths.project_path / "configs/europe_2022_v1.yaml")

results = xr.open_dataset(paths.evaluation_nc(cfg.id))
print(results)

# Load WB2 pre-computed reference for Pangu vs ERA5, 240x121 grid, 2022
_WB2_REF_PATH = (
    "gs://weatherbench2/benchmark_results/pangu_vs_era5_240x121_2022.nc"
)
with fsspec.open(_WB2_REF_PATH, "rb") as _f:
    wb2_ref = xr.open_dataset(_f).load()
print("\nWB2 reference loaded:", wb2_ref)

# %% [markdown]
# ## Prepare metrics
#
# `evaluate_in_memory` outputs MSE and ACC directly; RMSE is sqrt(MSE).
#
# **Note — known latitude-weighting issue:** our zarr artifacts contain only
# the pre-extracted Europe subregion.  WeatherBench 2's `get_lat_weights`
# assumes a full global latitude array; when called on the subregion it
# extends cell boundaries to ±90°, giving the edge latitudes (36 °N, 75 °N)
# incorrect area weights.  As a result our RMSE is ~30 % lower than the WB2
# reference.  Fix: store full-resolution (240 × 121) data in the zarr
# artifacts and let `evaluate_in_memory` handle regional slicing.

# %%
region = cfg.region.name
mse = results.sel(metric="mse", region=region)
acc = results.sel(metric="acc", region=region)
rmse = mse ** 0.5

# Convert lead_time to hours for plotting
lead_hours = results.lead_time / np.timedelta64(1, "h")

# WB2 reference lead times are stored as integer hours
wb2_lead_hours = wb2_ref.lead_time.values.astype(float)

# Surface variables have no level dim; pressure-level vars do
surface_vars = cfg.variables.surface
pl_vars = [v.name for v in cfg.variables.pressure_level]
pl_levels = {v.name: v.levels for v in cfg.variables.pressure_level}
all_vars = surface_vars + pl_vars

UNITS = {"2m_temperature": "K", "geopotential": "m²/s²"}

# %% [markdown]
# ## RMSE vs Lead Time

# %%
fig, axes = plt.subplots(1, len(all_vars), figsize=(7 * len(all_vars), 4), squeeze=False)

for ax, var in zip(axes[0], all_vars):
    unit = UNITS.get(var, "")
    # WB2 reference variable name convention
    wb2_var = f"rmse.{var}"
    if var in pl_vars:
        for lv in pl_levels[var]:
            ax.plot(lead_hours, rmse[var].sel(level=lv), marker="o", markersize=3,
                    label=f"{lv} hPa (ours)")
            if wb2_var in wb2_ref and "europe" in wb2_ref.region:
                ax.plot(wb2_lead_hours,
                        wb2_ref[wb2_var].sel(region="europe", level=lv),
                        marker="x", markersize=3, linestyle="--",
                        label=f"{lv} hPa (WB2 ref)")
        ax.legend(fontsize=8)
    else:
        ax.plot(lead_hours, rmse[var], marker="o", markersize=3, label="ours")
        if wb2_var in wb2_ref and "europe" in wb2_ref.region:
            ax.plot(wb2_lead_hours,
                    wb2_ref[wb2_var].sel(region="europe"),
                    marker="x", markersize=3, linestyle="--", label="WB2 ref")
        ax.legend(fontsize=8)
    ax.set_title(var.replace("_", " "))
    ax.set_xlabel("Lead time (hours)")
    ax.set_ylabel(f"RMSE [{unit}]")
    ax.grid(True, alpha=0.3)

fig.suptitle(f"{cfg.model_name.title()} — {region.title()} 2022")
fig.tight_layout()
fig.savefig(paths.images_path / "05_rmse_lead_time.png", dpi=150, bbox_inches="tight")
plt.show()

# %% [markdown]
# ```{figure} ../../output/images/05_rmse_lead_time.png
# :name: fig-05-rmse
# RMSE vs. lead time for each evaluated variable. Lower is better.
# ```

# %% [markdown]
# ## ACC vs Lead Time

# %%
fig, axes = plt.subplots(1, len(all_vars), figsize=(7 * len(all_vars), 4), squeeze=False)

for ax, var in zip(axes[0], all_vars):
    wb2_var = f"acc.{var}"
    if var in pl_vars:
        for lv in pl_levels[var]:
            ax.plot(lead_hours, acc[var].sel(level=lv), marker="o", markersize=3,
                    label=f"{lv} hPa (ours)")
            if wb2_var in wb2_ref and "europe" in wb2_ref.region:
                ax.plot(wb2_lead_hours,
                        wb2_ref[wb2_var].sel(region="europe", level=lv),
                        marker="x", markersize=3, linestyle="--",
                        label=f"{lv} hPa (WB2 ref)")
        ax.legend(fontsize=8)
    else:
        ax.plot(lead_hours, acc[var], marker="o", markersize=3, color="C1", label="ours")
        if wb2_var in wb2_ref and "europe" in wb2_ref.region:
            ax.plot(wb2_lead_hours,
                    wb2_ref[wb2_var].sel(region="europe"),
                    marker="x", markersize=3, linestyle="--", color="C1",
                    label="WB2 ref")
        ax.legend(fontsize=8)
    ax.axhline(0.6, color="gray", linestyle="--", linewidth=0.8, label="ACC = 0.6")
    ax.set_ylim(-0.1, 1.05)
    ax.set_title(var.replace("_", " "))
    ax.set_xlabel("Lead time (hours)")
    ax.set_ylabel("ACC")
    ax.grid(True, alpha=0.3)

fig.suptitle(f"{cfg.model_name.title()} — {region.title()} 2022")
fig.tight_layout()
fig.savefig(paths.images_path / "05_acc_lead_time.png", dpi=150, bbox_inches="tight")
plt.show()

# %% [markdown]
# ```{figure} ../../output/images/05_acc_lead_time.png
# :name: fig-05-acc
# ACC vs. lead time. The dashed line marks the ACC = 0.6 skill threshold.
# ```
