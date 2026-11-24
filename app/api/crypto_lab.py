"""Читання готового звіту вимірювань (без запуску експерименту)."""
import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

router = APIRouter(prefix="/lab/crypto", tags=["crypto-lab"])

# Фіксований шлях із конфігурації; клієнт не може його змінити.
REPORT_PATH = Path(__file__).resolve().parents[2] / "results" / "practice-02" / "report.json"
UNAVAILABLE = "Benchmark results unavailable"


class ResultRow(BaseModel):
    model_config = ConfigDict(extra="allow")
    backend: str
    algorithm: str
    size_bytes: int
    operation: str
    series_mean_ns: list[float]
    median_ns: float
    iqr_ns: float
    throughput_mib_s: float


class BenchmarkReport(BaseModel):
    model_config = ConfigDict(extra="allow")
    schema_version: Literal[1]
    run_id: str
    environment: dict
    parameters: dict
    results: list[ResultRow]


@router.get("/benchmark-results")
def benchmark_results():
    path = REPORT_PATH
    if not path.is_file():
        raise HTTPException(status_code=404, detail=UNAVAILABLE)
    try:
        report = BenchmarkReport.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        raise HTTPException(status_code=500, detail=UNAVAILABLE)
    return report.model_dump()
