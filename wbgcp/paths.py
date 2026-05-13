"""Project paths configuration.

All paths are resolved relative to the project root, making scripts runnable
from any working directory.
"""

from pathlib import Path


class ProjPaths:
    def __init__(self):
        self._pkg_path = Path(__file__).resolve().parent
        self._project_path = self._pkg_path.parent

    # ------------------------------------------------------------------ #
    # Top-level directories                                                #
    # ------------------------------------------------------------------ #

    @property
    def project_path(self) -> Path:
        return self._project_path

    @property
    def pkg_path(self) -> Path:
        return self._pkg_path

    @property
    def pipeline_path(self) -> Path:
        return self._project_path / "pipeline"

    # ------------------------------------------------------------------ #
    # Data directories                                                     #
    # ------------------------------------------------------------------ #

    @property
    def data_path(self) -> Path:
        return self._project_path / "data"

    @property
    def downloads_path(self) -> Path:
        return self.data_path / "downloads"

    @property
    def processed_data_path(self) -> Path:
        return self.data_path / "processed"

    # ------------------------------------------------------------------ #
    # Output directories                                                   #
    # ------------------------------------------------------------------ #

    @property
    def output_path(self) -> Path:
        return self._project_path / "output"

    @property
    def images_path(self) -> Path:
        return self.output_path / "images"

    @property
    def reports_path(self) -> Path:
        return self.output_path / "reports"

    # ------------------------------------------------------------------ #
    # Data artifact paths                                                  #
    #                                                                      #
    # Artifacts are keyed by (type, artifact_id).                         #
    # artifact_id is derived from ExperimentConfig properties:            #
    #   obs/forecast: {region}_{period_start}_{period_end}                #
    #   climatology:  {region}                                             #
    # ------------------------------------------------------------------ #

    def artifact_path(self, artifact_type: str, artifact_id: str) -> Path:
        """Root directory for a data artifact."""
        return self.downloads_path / artifact_type / artifact_id

    def artifact_zarr(self, artifact_type: str, artifact_id: str) -> Path:
        """Zarr store path inside an artifact directory."""
        return self.artifact_path(artifact_type, artifact_id) / "data.zarr"

    def artifact_metadata(self, artifact_type: str, artifact_id: str) -> Path:
        """Provenance metadata file for an artifact (tracked by Snakemake)."""
        return self.artifact_path(artifact_type, artifact_id) / "metadata.json"

    # ------------------------------------------------------------------ #
    # Evaluation output paths                                              #
    # ------------------------------------------------------------------ #

    def evaluation_path(self, experiment_id: str) -> Path:
        """Root directory for evaluation outputs."""
        return self.processed_data_path / "evaluations" / experiment_id

    def evaluation_nc(self, experiment_id: str, eval_name: str = "deterministic") -> Path:
        """Results NetCDF produced by evaluate_in_memory."""
        return self.evaluation_path(experiment_id) / f"{eval_name}.nc"

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def ensure_directories(self) -> None:
        """Create all standard directories if they do not yet exist."""
        for d in [self.downloads_path, self.processed_data_path,
                  self.images_path, self.reports_path]:
            d.mkdir(parents=True, exist_ok=True)
