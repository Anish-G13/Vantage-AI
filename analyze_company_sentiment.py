"""Optional legacy sentiment helper using the supported Google Gen AI SDK.

The dashboard does not call this helper. Its call_gemini interface is retained;
output is AI interpretation, not sourced competitive research.
"""

import json

import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, ConfigDict, Field

from vantage.config import settings
from vantage.research import clean_json, response_text


class SentimentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sentiment: str = Field(min_length=1, max_length=1500)
    risks: list[str] = Field(max_length=20)
    recommendation: str | list[str]


def _ensure_genai() -> bool:
    if not settings().api_key:
        st.error("The owner must configure a server-side Gemini API key to use this helper.")
        return False
    return True


def call_gemini(prompt: str) -> dict | None:
    if not _ensure_genai():
        return None
    if not isinstance(prompt, str) or not 1 <= len(prompt) <= 20_000:
        st.error("Enter a prompt of 1–20,000 characters.")
        return None
    config = settings()
    try:
        with genai.Client(
            api_key=config.api_key,
            http_options=types.HttpOptions(
                timeout=40_000, retry_options=types.HttpRetryOptions(attempts=1)
            ),
        ) as client:
            response = client.models.generate_content(
                model=config.model,
                contents=prompt,
                config={
                    "system_instruction": "Return a concise AI interpretation with sentiment, risks, and recommendation. Do not invent sources or outcomes.",
                    "response_mime_type": "application/json",
                    "response_json_schema": SentimentResult.model_json_schema(),
                    "max_output_tokens": 3000,
                },
            )
        return SentimentResult.model_validate(
            json.loads(clean_json(response_text(response)[0]))
        ).model_dump()
    except ValueError:
        st.error("The AI answer did not match the sentiment schema.")
    except Exception:
        st.error(
            "The AI service could not complete the request. Check configuration or retry later."
        )
    return None
