from typing import Literal
from pydantic import BaseModel, ConfigDict

class KeyGenerationResult(BaseModel):
    profile: str
    series_ns: list[float]
    median_ns: float
    iqr_ns: float

class BenchmarkResult(BaseModel):
    profile: str
    operation: Literal["encrypt", "decrypt"]
    payload_bytes: int
    series_mean_ns: list[float]
    median_ns: float
    iqr_ns: float
    ciphertext_bytes: int
    throughput_mib_s: float | None

class CheckResult(BaseModel):
    name: str
    profile: str
    passed: bool
    detail: str = ""

class Summary(BaseModel):
    key_profiles_count: int
    results_count: int
    checks_count: int
    all_checks_passed: bool

class BenchmarkResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    run_id: str
    environment: dict
    parameters: dict
    key_generation: list[KeyGenerationResult]
    results: list[BenchmarkResult]
    checks: list[CheckResult]
    summary: Summary
