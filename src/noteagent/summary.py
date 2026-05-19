"""LLM-powered summarization via EtherVox LLM backend."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from noteagent.models import Transcript

SUMMARY_PROMPTS = {
    "general": "Summarize the following transcript concisely, highlighting key points:",
    "meeting": (
        "Summarize this meeting transcript. Include:\n"
        "- Attendees mentioned\n"
        "- Key discussion points\n"
        "- Decisions made\n"
        "- Action items with owners\n"
    ),
    "lecture": (
        "Summarize this lecture transcript. Include:\n"
        "- Main topic and subtopics\n"
        "- Key concepts explained\n"
        "- Important definitions\n"
        "- Questions raised\n"
    ),
}


def summarize(
    transcript: Transcript,
    style: str = "general",
    provider: str = "ethervox",
    config=None,
) -> str:
    """Generate a summary from a transcript using EtherVox LLM."""
    prompt = _build_prompt(transcript, style)
    return _summarize_ethervox(prompt, config=config)


def _build_prompt(transcript: Transcript, style: str) -> str:
    system_prompt = SUMMARY_PROMPTS.get(style, SUMMARY_PROMPTS["general"])
    text = transcript.full_text
    max_chars = 30000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[... transcript truncated ...]"
    return f"{system_prompt}\n\n---\n\n{text}"


def _get_default_model_path() -> str:
    """Find a GGUF model in the configured cache directory."""
    cache_dir = Path(
        os.environ.get("NOTEAGENT_MODEL_DIR", "~/.cache/noteagent/models")
    ).expanduser()
    for pattern in ("*.gguf", "*.bin"):
        matches = list(cache_dir.glob(pattern))
        if matches:
            return str(matches[0])
    return ""


def _summarize_ethervox(prompt: str, config=None) -> str:
    """Use the EtherVox LLM backend to generate a summary."""
    from noteagent.ethervox.llm import EtherVoxLLM

    try:
        llm_backend = getattr(config, "llm_backend", "local") if config else "local"
        language = getattr(config, "language", "en") if config else "en"

        if llm_backend == "openai":
            api_key = getattr(config, "llm_api_key", "") if config else ""
            base_url = getattr(config, "llm_api_base_url", "https://api.openai.com/v1") if config else "https://api.openai.com/v1"
            llm = EtherVoxLLM.from_openai(api_key=api_key, base_url=base_url)
        else:
            model_path = getattr(config, "llm_model_path", "") if config else ""
            if not model_path:
                model_path = _get_default_model_path()
            llm = EtherVoxLLM(model_path=model_path)

        result = llm.generate(prompt, language=language)
        return result if result else "[Summary generation returned empty response]"
    except ImportError as e:
        return f"[EtherVox LLM unavailable: {e}]"
    except Exception as e:  # noqa: BLE001
        return f"[Summary generation failed: {e}]"
