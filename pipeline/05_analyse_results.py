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
# # WeatherBench 2 Evaluation — Bavaria Dev
#
# RMSE and ACC vs. lead time for Pangu-Weather forecasts evaluated
# against ERA5 over Bavaria (Q1 2020, 1.5° grid).
#
# Metrics were produced by `weatherbench2.evaluation.evaluate_in_memory`.
# RMSE is derived here as sqrt(MSE).

# %%
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
from wbgcp.paths import ProjPaths
from wbgcp.config import ExperimentConfig

paths = ProjPaths()
paths.ensure_directories()
cfg = ExperimentConfig.from_yaml(paths.project_path / "configs/bavaria_dev.yaml")

results = xr.open_dataset(paths.evaluation_nc(cfg.id))
print(results)

# %% [markdown]
# ## Prepare metrics
#
# `evaluate_in_memory` outputs MSE directly; RMSE is sqrt(MSE).

# %%
region = cfg.region.name
mse = results.sel(metric="mse", region=region)
acc = results.sel(metric="acc", region=region)
rmse = mse ** 0.5

# Convert lead_time to hours for plotting
lead_hours = results.lead_time / np.timedelta64(1, "h")

# Surface variables have no level dim; pressure-level vars do
surface_vars = cfg.variables.surface
pl_vars = [f"{v.name}" for v in cfg.variables.pressure_level]  # e.g. "geopotential"
pl_levels = {v.name: v.levels for v in cfg.variables.pressure_level}

# %% [markdown]
# ## RMSE vs Lead Time

# %%
all_vars = surface_vars + pl_vars
fig, axes = plt.subplots(1, len(all_vars), figsize=(7 * len(all_vars), 4), squeeze=False)

for ax, var in zip(axes[0], all_vars):
    if var in pl_vars:
        for lv in pl_levels[var]:
            ax.plot(lead_hours, rmse[var].sel(level=lv), marker="o", markersize=3,
                    label=f"{lv} hPa")
        ax.legend(fontsize=8)
    else:
        ax.plot(lead_hours, rmse[var], marker="o", markersize=3)
    ax.set_title(var.replace("_", " "))
    ax.set_xlabel("Lead time (hours)")
    ax.set_ylabel("RMSE")
    ax.grid(True, alpha=0.3)

fig.suptitle(f"{cfg.model_name.title()} — {region.title()} Q1 2020")
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
    if var in pl_vars:
        for lv in pl_levels[var]:
            ax.plot(lead_hours, acc[var].sel(level=lv), marker="o", markersize=3,
                    label=f"{lv} hPa")
        ax.legend(fontsize=8)
    else:
        ax.plot(lead_hours, acc[var], marker="o", markersize=3, color="C1")
    ax.axhline(0.6, color="gray", linestyle="--", linewidth=0.8, label="ACC = 0.6")
    ax.set_ylim(-0.1, 1.05)
    ax.set_title(var.replace("_", " "))
    ax.set_xlabel("Lead time (hours)")
    ax.set_ylabel("ACC")
    ax.grid(True, alpha=0.3)

fig.suptitle(f"{cfg.model_name.title()} — {region.title()} Q1 2020")
fig.tight_layout()
fig.savefig(paths.images_path / "05_acc_lead_time.png", dpi=150, bbox_inches="tight")
plt.show()

# %% [markdown]
# ```{figure} ../../output/images/05_acc_lead_time.png
# :name: fig-05-acc
# ACC vs. lead time. The dashed line marks the ACC = 0.6 skill threshold.
# ```
