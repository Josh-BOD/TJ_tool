"""Pydantic models for the campaign scraper service."""

from typing import Optional
from pydantic import BaseModel


class ScrapeRequest(BaseModel):
    campaign_id: str
    account_id: Optional[str] = None
    webhook_url: Optional[str] = None
    priority: int = 10  # lower = higher priority (1=create, 2=update, 3=scrape)


class UpdateRequest(BaseModel):
    campaign_id: str
    fields: dict
    dry_run: bool = False
    account_id: Optional[str] = None
    webhook_url: Optional[str] = None
    priority: int = 5  # lower = higher priority


class JobStatusResponse(BaseModel):
    job_id: str
    status: str  # pending, running, completed, failed, cancelled
    job_type: str = "scrape"
    campaign_id: str = ""
    result: Optional[dict] = None
    ads: Optional[list] = None
    error: Optional[str] = None
    log_lines: list[str] = []


class HealthResponse(BaseModel):
    hostname: str
    active_jobs: int
    authenticated: bool
    pool_disabled: bool = False
    pool_disabled_reason: str = ""
    queued_jobs: int = 0


class WebhookPayload(BaseModel):
    job_id: str
    campaign_id: str
    status: str
    job_type: str = "scrape"
    result: Optional[dict] = None
    ads: Optional[list] = None
    error: Optional[str] = None
