"""Persistent application security settings."""

from typing import Literal

from pydantic import (
    BaseModel,
    Field,
)

NetworkAccessMode = Literal[
    "public_only",
    "public_and_loopback",
    "private_networks",
]


class NetworkSafetySettings(BaseModel):
    """Network target validation and access controls."""

    access_mode: NetworkAccessMode = "public_and_loopback"

    resolve_hostnames: bool = True

    dns_resolution_timeout_seconds: float = Field(
        default=3.0,
        ge=0.5,
        le=15.0,
    )

    max_resolved_addresses: int = Field(
        default=16,
        ge=1,
        le=128,
    )

    allow_link_local: bool = False
    allow_multicast: bool = False
    allow_reserved: bool = False


class ExecutionSettings(BaseModel):
    """Controlled HTTP execution limits."""

    default_timeout_seconds: float = Field(
        default=10.0,
        ge=1.0,
        le=30.0,
    )

    max_request_bytes: int = Field(
        default=(1 * 1024 * 1024),
        ge=1024,
        le=(10 * 1024 * 1024),
    )

    max_response_bytes: int = Field(
        default=(4 * 1024 * 1024),
        ge=1024,
        le=(32 * 1024 * 1024),
    )

    rate_limit_requests: int = Field(
        default=30,
        ge=1,
        le=1000,
    )

    rate_limit_window_seconds: float = Field(
        default=60.0,
        ge=1.0,
        le=3600.0,
    )

    max_parallel_requests: int = Field(
        default=4,
        ge=1,
        le=32,
    )


class EvidenceSettings(BaseModel):
    """Scan and report evidence limits."""

    body_excerpt_characters: int = Field(
        default=(16 * 1024),
        ge=0,
        le=(64 * 1024),
    )

    store_response_headers: bool = True

    max_scan_bytes: int = Field(
        default=(16 * 1024 * 1024),
        ge=(1024 * 1024),
        le=(128 * 1024 * 1024),
    )

    max_report_bytes: int = Field(
        default=(32 * 1024 * 1024),
        ge=(1024 * 1024),
        le=(256 * 1024 * 1024),
    )

    scan_retention_keep_latest: int = Field(
        default=50,
        ge=1,
        le=500,
    )


class AuditSettings(BaseModel):
    """Local audit-event configuration."""

    enabled: bool = True

    retention_days: int = Field(
        default=180,
        ge=1,
        le=3650,
    )

    max_events: int = Field(
        default=10000,
        ge=100,
        le=100000,
    )


class ApplicationSettings(BaseModel):
    """Complete AccessMatrix application settings."""

    version: Literal[1] = 1

    network: NetworkSafetySettings = Field(default_factory=(NetworkSafetySettings))

    execution: ExecutionSettings = Field(default_factory=(ExecutionSettings))

    evidence: EvidenceSettings = Field(default_factory=(EvidenceSettings))

    audit: AuditSettings = Field(default_factory=(AuditSettings))
