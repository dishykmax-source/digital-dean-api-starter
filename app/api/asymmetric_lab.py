"""Read-only Practice 03 asymmetric benchmark endpoint."""
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from app.schemas.asymmetric_report import BenchmarkResponse

router = APIRouter(prefix="/lab/crypto", tags=["asymmetric-crypto-lab"])
REPORT_PATH = Path(__file__).resolve().parents[2] / "results" / "practice-03" / "report.json"
UNAVAILABLE = "Benchmark results unavailable"

@router.get("/asymmetric-benchmark-results", response_model=BenchmarkResponse)
def asymmetric_benchmark_results():
    if not REPORT_PATH.is_file():
        raise HTTPException(status_code=404, detail=UNAVAILABLE)
    try:
        data = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        # Variant 3: summary is calculated from the stored data, never from a new benchmark.
        data["summary"] = {
            "key_profiles_count": len(data["key_generation"]),
            "results_count": len(data["results"]),
            "checks_count": len(data["checks"]),
            "all_checks_passed": all(c["passed"] for c in data["checks"]),
        }
        response = BenchmarkResponse.model_validate(data)
        return response
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=UNAVAILABLE) from exc
