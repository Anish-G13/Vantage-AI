"""Strict contracts shared by research, UI, calculations, and exports."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import unicodedata
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Rating = Literal["Yes", "Partial", "No", "Unverified"]
RATINGS: tuple[str, ...] = ("Yes", "Partial", "No", "Unverified")
Basis = Literal[
    "Source-backed", "AI inference", "Insufficient evidence", "Sample data", "User override"
]


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def name_text(value: str) -> str:
    if not isinstance(value, str) or any(unicodedata.category(c).startswith("C") for c in value):
        raise ValueError("Use a product name without control characters.")
    value = " ".join(unicodedata.normalize("NFKC", value).split())
    if not 2 <= len(value) <= 80:
        raise ValueError("Product and feature names must contain 2–80 characters.")
    return value


def safe_source_url(value: str) -> str:
    """Validate a link, never fetch it. Block executable and local-network URLs."""
    p = urlsplit(value)
    host = (p.hostname or "").lower().rstrip(".")
    if (
        p.scheme != "https"
        or not host
        or p.username
        or p.password
        or p.port not in (None, 443)
        or len(value) > 4000
        or any(ord(c) < 33 for c in value)
        or host in {"localhost", "localhost.localdomain"}
        or host.endswith((".local", ".internal", ".localhost"))
    ):
        raise ValueError("Evidence links must use a public HTTPS URL.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if "." not in host:
            raise ValueError("Evidence links must use a public host.") from None
    else:
        if not address.is_global:
            raise ValueError("Private and reserved addresses are not evidence sources.")
    return value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class ResearchRequest(StrictModel):
    product: str
    competitors: list[str] = Field(min_length=1, max_length=3)
    custom_features: list[str] | None = Field(default=None, min_length=5, max_length=5)

    _product_name = field_validator("product")(name_text)

    @field_validator("competitors", "custom_features")
    @classmethod
    def clean_names(cls, values: list[str] | None) -> list[str] | None:
        return None if values is None else [name_text(v) for v in values]

    @model_validator(mode="after")
    def unique_names(self) -> ResearchRequest:
        names = [n.casefold() for n in self.products]
        if len(names) != len(set(names)):
            raise ValueError("Use distinct names for your product and every competitor.")
        if self.custom_features and len({f.casefold() for f in self.custom_features}) != 5:
            raise ValueError("Enter five distinct features, one per line.")
        return self

    @property
    def products(self) -> list[str]:
        return [self.product, *self.competitors]

    def fingerprint(self) -> str:
        payload = self.model_dump()
        payload["product"] = self.product.casefold()
        payload["competitors"] = [p.casefold() for p in self.competitors]
        if self.custom_features:
            payload["custom_features"] = [f.casefold() for f in self.custom_features]
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


class Feature(StrictModel):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=4, max_length=300)

    _name = field_validator("name")(name_text)


class Discovery(StrictModel):
    category: str = Field(min_length=2, max_length=160)
    features: list[Feature] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def distinct(self) -> Discovery:
        if len({f.name.casefold() for f in self.features}) != 5:
            raise ValueError("The five critical features must be distinct.")
        return self


class DraftAssessment(StrictModel):
    rating: Rating
    basis: Literal["Fact", "Inference", "Insufficient"]
    explanation: str = Field(min_length=8, max_length=600)

    @field_validator("explanation")
    @classmethod
    def no_model_urls(cls, text: str) -> str:
        if re.search(r"(?i)(https?://|www\.|javascript:|\]\()", text):
            raise ValueError("Model prose cannot supply citation URLs.")
        return text


class ResearchDraft(StrictModel):
    assessments: dict[str, DraftAssessment]


class Source(StrictModel):
    url: str
    title: str = Field(min_length=1, max_length=500)
    supported_text: str = Field(min_length=1, max_length=2000)

    _safe_url = field_validator("url")(safe_source_url)


class Assessment(StrictModel):
    rating: Rating
    basis: Basis
    explanation: str = Field(min_length=1, max_length=1600)
    sources: list[Source] = Field(default_factory=list, max_length=20)
    origin: Literal["AI", "Manual", "Sample", "Unassessed"] = "AI"

    @model_validator(mode="after")
    def require_evidence(self) -> Assessment:
        if self.origin == "AI" and self.rating != "Unverified":
            if not self.sources or self.basis not in ("Source-backed", "AI inference"):
                raise ValueError("An AI rating requires claim-linked grounding sources.")
        if (
            self.origin == "AI"
            and self.rating == "Unverified"
            and self.basis != "Insufficient evidence"
        ):
            raise ValueError("An unverified AI rating must state insufficient evidence.")
        return self

    @property
    def confidence(self) -> str:
        if self.origin == "Sample":
            return "Sample — not researched"
        if self.origin == "Manual":
            return "User judgment — not independently verified"
        if self.rating == "Unverified":
            return "Unknown — insufficient evidence"
        if self.basis == "AI inference":
            return "Low — interpretation of linked evidence"
        return "Moderate — claim-linked source; check scope and plan"


class Analysis(StrictModel):
    request: ResearchRequest
    discovery: Discovery
    assessments: dict[str, Assessment]
    researched_at: str
    mode: Literal["Live research", "Manual workspace", "Demonstration"]
    model: str
    notices: list[str] = Field(default_factory=list)
    search_suggestions_html: str = ""

    @model_validator(mode="after")
    def complete_grid(self) -> Analysis:
        if set(self.assessments) != set(self.cell_ids):
            raise ValueError("Every product must have exactly five assessments.")
        datetime.fromisoformat(self.researched_at)
        return self

    @property
    def cell_ids(self) -> list[str]:
        return [cell_id(p, f) for p in range(len(self.request.products)) for f in range(5)]

    @property
    def display_date(self) -> str:
        return (
            datetime.fromisoformat(self.researched_at)
            .astimezone(UTC)
            .strftime("%b %d, %Y at %H:%M UTC")
        )


def cell_id(product_index: int, feature_index: int) -> str:
    return f"p{product_index}_f{feature_index}"


class Override(StrictModel):
    rating: Rating
    note: str = Field(default="", max_length=1000)


class RoadmapAssumption(StrictModel):
    impact: int = Field(default=3, ge=1, le=5, strict=True)
    effort: int = Field(default=3, ge=1, le=5, strict=True)


class Insight(StrictModel):
    strengths: str = Field(min_length=8, max_length=1000)
    neutral_observations: str = Field(min_length=8, max_length=1000)
    critical_gaps_risks: str = Field(min_length=8, max_length=1000)

    @field_validator("strengths", "neutral_observations", "critical_gaps_risks")
    @classmethod
    def no_links(cls, value: str) -> str:
        if re.search(r"(?i)https?://|www\.", value):
            raise ValueError("Insights cannot add unverified sources.")
        return value
