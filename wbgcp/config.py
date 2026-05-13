"""Experiment configuration loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Region:
    name: str
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float


@dataclass
class Period:
    start: str           # ISO date, e.g. "2020-01-01"
    end: str             # ISO date, e.g. "2020-03-31" (forecast init-time range)
    max_lead_hours: int = 240  # max forecast lead; obs cover end + this buffer


@dataclass
class PressureLevelVar:
    name: str
    levels: list[int]


@dataclass
class Variables:
    surface: list[str]
    pressure_level: list[PressureLevelVar]

    @property
    def all_names(self) -> list[str]:
        return list(self.surface) + [v.name for v in self.pressure_level]

    @property
    def pressure_level_map(self) -> dict[str, list[int]]:
        return {v.name: v.levels for v in self.pressure_level}


@dataclass
class Sources:
    era5: str
    climatology: str
    pangu: str

    def for_model(self, model_name: str) -> str:
        return getattr(self, model_name)


@dataclass
class ExperimentConfig:
    id: str
    description: str
    region: Region
    period: Period
    model_name: str
    variables: Variables
    metrics: list[str]
    sources: Sources

    @classmethod
    def from_yaml(cls, path: Path | str) -> ExperimentConfig:
        with open(path) as f:
            raw = yaml.safe_load(f)
        return cls(
            id=raw["experiment"]["id"],
            description=raw["experiment"]["description"],
            region=Region(**raw["region"]),
            period=Period(**raw["period"]),
            model_name=raw["model"]["name"],
            variables=Variables(
                surface=raw["variables"]["surface"],
                pressure_level=[
                    PressureLevelVar(name=v["name"], levels=v["levels"])
                    for v in raw["variables"]["pressure_level"]
                ],
            ),
            metrics=raw["metrics"],
            sources=Sources(**raw["sources"]),
        )

    @property
    def period_id(self) -> str:
        return f"{self.period.start}_{self.period.end}"

    @property
    def obs_artifact_id(self) -> str:
        return f"{self.region.name}_{self.period_id}"

    @property
    def forecast_artifact_id(self) -> str:
        return f"{self.model_name}_{self.region.name}_{self.period_id}"

    @property
    def clim_artifact_id(self) -> str:
        # Climatology covers the full annual cycle — not tied to a period
        return self.region.name
