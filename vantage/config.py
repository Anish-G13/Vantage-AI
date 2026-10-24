"""Read only explicit application settings. Never render or log credentials."""

import os
from dataclasses import dataclass, field

import streamlit as st

from .research import DEFAULT_MODEL


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    model: str = DEFAULT_MODEL
    max_hourly_calls: int = 60


def setting(name: str, fallback: str = "") -> str:
    try:
        value = st.secrets.get(name, os.environ.get(name, fallback))
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        value = os.environ.get(name, fallback)
    return str(value).strip()


def settings() -> Settings:
    try:
        limit = min(500, max(1, int(setting("MAX_HOURLY_AI_CALLS", "60"))))
    except ValueError:
        limit = 60
    return Settings(
        api_key=setting("GOOGLE_API_KEY") or setting("GEMINI_API_KEY"),
        model=setting("GEMINI_MODEL", DEFAULT_MODEL),
        max_hourly_calls=limit,
    )
