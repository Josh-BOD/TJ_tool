"""Pydantic models for the Campaign Builder worker server."""

from pydantic import BaseModel
from typing import Optional


class CreateJobRequest(BaseModel):
    csv_content: str
    dry_run: bool = False
    filename: str = "campaign_builder_input.csv"


class JobResponse(BaseModel):
    job_id: str
    status: str  # pending, running, completed, failed, cancelled
    campaigns_created: int = 0
    total_campaigns: int = 0
    log_lines: list[str] = []
    error: Optional[str] = None


class HealthResponse(BaseModel):
    hostname: str
    active_jobs: int
    available_ad_csvs: dict[str, list[str]]


class AdCsvListResponse(BaseModel):
    csv_files: dict[str, list[str]]
