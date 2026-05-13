# WeatherBench GCP

Evaluate numerical weather prediction models against ERA5 reanalysis using the
[WeatherBench 2](https://sites.research.google/weatherbench/) metrics and the
public Google Cloud Storage datasets. The pipeline downloads regional subsets,
computes deterministic skill scores (RMSE, ACC), and publishes results as a
[MyST](https://mystmd.org/) Jupyter Book.

## Quick start

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

uv sync
snakemake -n           # dry-run — see what would execute
snakemake -j4          # run full pipeline (parallelises extraction steps)
```

## Configuration

All experiment parameters live in `configs/bavaria_dev.yaml`:

| Field | Purpose |
|-------|---------|
| `experiment.id` | Unique run ID used to name result files |
| `region` | Lat/lon bounding box for the spatial subset |
| `period.start/end` | Forecast init-time range |
| `period.max_lead_hours` | Maximum forecast lead time (drives the obs coverage buffer) |
| `model.name` | Forecast model key (must match a key under `sources`) |
| `variables` | Surface and pressure-level variables to extract and evaluate |
| `sources` | GCS paths for ERA5, climatology, and each model's zarr store |

Changing any of these fields produces new artifact IDs; Snakemake will
re-run only the affected rules automatically.

## Pipeline

```
extract_observations ─┐
extract_climatology  ──┼─▶ evaluate ─▶ analyse_results
extract_forecast     ─┘
```

| Rule | Script | Output |
|------|--------|--------|
| `extract_observations` | `pipeline/01_extract_observations.py` | `data/downloads/observations/<id>/` |
| `extract_climatology` | `pipeline/02_extract_climatology.py` | `data/downloads/climatology/<region>/` |
| `extract_forecast` | `pipeline/03_extract_forecast.py` | `data/downloads/forecasts/<id>/` |
| `evaluate` | `pipeline/04_evaluate.py` | `data/processed/evaluations/<id>/deterministic.nc` |
| `analyse_results` | `pipeline/05_analyse_results.py` | `book/notebooks/05_analyse_results.ipynb`, `output/images/` |

Data artifacts are Zarr stores on disk. Snakemake tracks `metadata.json`
files as output stamps — delete one to force re-extraction of that artifact.

Observations are extracted for `period.start` → `period.end + 1 day + max_lead_hours`
so that every forecast valid time (init + lead) has a matching truth entry.

## Data sources

All data is read anonymously from the
[WeatherBench 2 public GCS bucket](https://console.cloud.google.com/storage/browser/weatherbench2).

| Dataset | GCS path |
|---------|----------|
| ERA5 (6-hourly) | `gs://weatherbench2/datasets/era5/1959-2022-6h-240x121_equiangular_with_poles_conservative.zarr` |
| ERA5 climatology | `gs://weatherbench2/datasets/era5-hourly-climatology/1990-2019_6h_240x121_equiangular_with_poles_conservative.zarr` |
| Pangu-Weather | `gs://weatherbench2/datasets/pangu/2018-2022_0012_240x121_equiangular_with_poles_conservative.zarr` |

## Project layout

```
weather-bench-gcp/
├── wbgcp/                   # Python package
│   ├── config.py            # ExperimentConfig dataclass
│   ├── metadata.py          # Artifact provenance helpers
│   └── paths.py             # Centralized path resolution
├── pipeline/                # Pipeline scripts (numbered by stage)
├── configs/                 # Experiment YAML configs
│   └── bavaria_dev.yaml     # Bavaria / Q1-2020 / Pangu dev run
├── book/                    # MyST book source
│   ├── notebooks/           # Executed notebooks (Snakemake output)
│   └── myst.yml             # TOC and site settings
├── data/                    # Git-ignored data (managed by Snakemake)
├── output/images/           # Figures (tracked in git)
└── Snakefile                # Pipeline DAG
```

## Common Snakemake commands

| Command | Effect |
|---------|--------|
| `snakemake -n` | Dry run — show what would execute |
| `snakemake -j4` | Run pipeline with 4 parallel jobs |
| `snakemake -R extract_observations` | Force-re-run one rule |
| `snakemake --forceall` | Re-run everything unconditionally |
| `snakemake <file>` | Build one specific output file |
