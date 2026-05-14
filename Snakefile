# Snakefile — WeatherBench 2 evaluation pipeline
#
# The config file drives all paths; changing it (region, period, model)
# produces new artifact IDs and Snakemake will re-run the affected rules.
#
# Common commands:
#   snakemake -n              dry-run
#   snakemake -j4             run pipeline
#   snakemake -R extract_observations   force-re-run one rule
#   snakemake --forceall      re-run everything

import yaml

# ---------------------------------------------------------------------------
# Load experiment config to derive output paths
# ---------------------------------------------------------------------------

CONFIG = "configs/europe_2022_v1.yaml"

with open(CONFIG) as _f:
    _cfg = yaml.safe_load(_f)

_EXPERIMENT_ID = _cfg["experiment"]["id"]
_REGION        = _cfg["region"]["name"]
_PERIOD_ID     = f"{_cfg['period']['start']}_{_cfg['period']['end']}"
_MODEL         = _cfg["model"]["name"]

# Artifact root paths (data lives alongside these metadata.json files)
_OBS_META      = f"data/downloads/observations/{_REGION}_{_PERIOD_ID}/metadata.json"
_CLIM_META     = f"data/downloads/climatology/{_REGION}/metadata.json"
_FC_META       = f"data/downloads/forecasts/{_MODEL}_{_REGION}_{_PERIOD_ID}/metadata.json"

# Final outputs
_METRICS       = f"data/processed/evaluations/{_EXPERIMENT_ID}/deterministic.nc"
_NOTEBOOK      = f"book/notebooks/05_analyse_results.ipynb"

ANALYSIS_NOTEBOOKS = [_NOTEBOOK]

# ---------------------------------------------------------------------------
# Default target
# ---------------------------------------------------------------------------

rule all:
    input:
        ANALYSIS_NOTEBOOKS

# ---------------------------------------------------------------------------
# Data extraction rules
#
# Snakemake tracks the metadata.json as the output stamp; the data.zarr
# directory is written alongside it by each script.
# Delete a metadata.json to force re-extraction of that artifact.
# ---------------------------------------------------------------------------

rule extract_observations:
    input:
        config = CONFIG,
    output:
        _OBS_META,
    shell:
        "uv run python pipeline/01_extract_observations.py {input.config}"

rule extract_climatology:
    input:
        config = CONFIG,
    output:
        _CLIM_META,
    shell:
        "uv run python pipeline/02_extract_climatology.py {input.config}"

rule extract_forecast:
    input:
        config = CONFIG,
    output:
        _FC_META,
    shell:
        "uv run python pipeline/03_extract_forecast.py {input.config}"

# ---------------------------------------------------------------------------
# Evaluation rule
# ---------------------------------------------------------------------------

rule evaluate:
    input:
        config   = CONFIG,
        obs      = _OBS_META,
        clim     = _CLIM_META,
        forecast = _FC_META,
    output:
        _METRICS,
    shell:
        "uv run python pipeline/04_evaluate.py {input.config}"

# ---------------------------------------------------------------------------
# Analysis notebook rule
# ---------------------------------------------------------------------------

rule analyse_results:
    input:
        script  = "pipeline/05_analyse_results.py",
        metrics = _METRICS,
    output:
        notebook = _NOTEBOOK,
        img_rmse = "output/images/05_rmse_lead_time.png",
    shell:
        """
        MPLBACKEND=Agg uv run jupytext --to notebook --execute \
            --set-kernel python3 \
            --output {output.notebook} {input.script} && \
        uv run python -c "
import nbformat
nb = nbformat.read('{output.notebook}', as_version=4)
nb.cells = [c for c in nb.cells
            if not (c.cell_type == 'raw' and 'jupytext' in c.source)]
nbformat.write(nb, '{output.notebook}')
"
        """
