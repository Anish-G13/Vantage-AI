import json
from types import SimpleNamespace

import pytest

from vantage.demo import demonstration
from vantage.models import ResearchRequest, cell_id


def fake_response(text, metadata=None):
    return SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(parts=[SimpleNamespace(text=text, thought=False)]),
                grounding_metadata=metadata,
            )
        ]
    )


@pytest.fixture
def demo():
    return demonstration()


@pytest.fixture
def request_data():
    return ResearchRequest(product="Primary Product", competitors=["Rival Product"])


@pytest.fixture
def discovery_response(demo):
    return fake_response(demo.discovery.model_dump_json())


@pytest.fixture
def grounded_fixture(request_data):
    cells = {
        cell_id(p, f): {
            "rating": "Yes",
            "basis": "Fact",
            "explanation": f"Product {p} feature {f} is explicitly documented for the paid team plan.",
        }
        for p in range(2)
        for f in range(5)
    }
    text = json.dumps({"assessments": cells})
    claim = cells["p0_f0"]["explanation"]
    start = text.index(claim)
    metadata = {
        "grounding_chunks": [
            {"web": {"uri": "https://docs.example.com/features", "title": "Synthetic test source"}}
        ],
        "grounding_supports": [
            {
                "segment": {
                    "text": claim,
                    "start_index": start,
                    "end_index": start + len(claim),
                    "part_index": 0,
                },
                "grounding_chunk_indices": [0],
            }
        ],
        "search_entry_point": {"rendered_content": "<div>Test search attribution</div>"},
    }
    return text, metadata
