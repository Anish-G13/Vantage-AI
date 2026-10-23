import pytest
from pydantic import ValidationError

from vantage.models import Assessment, Discovery, Feature, ResearchRequest, safe_source_url


def test_normalized_input_and_fingerprint():
    a = ResearchRequest(product="  Acme   CRM ", competitors=["Rival"])
    b = ResearchRequest(product="acme crm", competitors=["rival"])
    assert a.product == "Acme CRM" and a.fingerprint() == b.fingerprint()


@pytest.mark.parametrize(
    "product,competitors",
    [
        ("A", ["Rival"]),
        ("Valid", []),
        ("Valid", ["valid"]),
        ("Bad\nName", ["Rival"]),
        ("X" * 81, ["Rival"]),
        ("Ａｃｍｅ", ["Acme"]),
    ],
)
def test_bad_names_and_duplicate_products(product, competitors):
    with pytest.raises(ValidationError):
        ResearchRequest(product=product, competitors=competitors)


def test_five_distinct_features_required():
    with pytest.raises(ValidationError):
        ResearchRequest(product="Acme", competitors=["Rival"], custom_features=["Same"] * 5)
    with pytest.raises(ValidationError):
        Discovery(
            category="Category", features=[Feature(name="One", description="Description.")] * 5
        )


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "file:///etc/passwd",
        "http://example.com",
        "https://localhost/a",
        "https://127.0.0.1",
        "https://10.0.0.1",
        "https://169.254.169.254/",
        "https://[::1]/a",
        "https://user:password@example.com",
        "https://example.com:8080",
        "https://service.internal/a",
    ],
)
def test_unsafe_source_urls(url):
    with pytest.raises(ValueError):
        safe_source_url(url)


def test_ai_cannot_have_rating_without_evidence():
    with pytest.raises(ValidationError):
        Assessment(rating="Yes", basis="Source-backed", explanation="Unsupported rating.")


def test_extra_model_fields_are_rejected():
    with pytest.raises(ValidationError):
        Feature(
            name="Valid",
            description="Valid description.",
            fabricated_sources=["https://example.com"],
        )
