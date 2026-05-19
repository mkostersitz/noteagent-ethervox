"""Tests for LLM summarization via EtherVoxLLM."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from noteagent.models import Transcript, TranscriptSegment
from noteagent.summary import _build_prompt, summarize, SUMMARY_PROMPTS


@pytest.fixture()
def sample_transcript():
    return Transcript(
        segments=[
            TranscriptSegment(start=0.0, end=2.0, text="Hello everyone"),
            TranscriptSegment(start=2.0, end=4.0, text="Today we'll discuss the project roadmap"),
            TranscriptSegment(start=4.0, end=6.0, text="First item is the authentication system"),
        ],
        language="en",
        model="base.en",
    )


def test_build_prompt_general_style(sample_transcript):
    prompt = _build_prompt(sample_transcript, "general")
    assert SUMMARY_PROMPTS["general"] in prompt
    assert "Hello everyone" in prompt
    assert "Today we'll discuss the project roadmap" in prompt
    assert "First item is the authentication system" in prompt


def test_build_prompt_meeting_style(sample_transcript):
    prompt = _build_prompt(sample_transcript, "meeting")
    assert SUMMARY_PROMPTS["meeting"] in prompt
    assert "Attendees" in prompt or "meeting" in prompt.lower()


def test_build_prompt_lecture_style(sample_transcript):
    prompt = _build_prompt(sample_transcript, "lecture")
    assert SUMMARY_PROMPTS["lecture"] in prompt
    assert "topic" in prompt.lower() or "concepts" in prompt.lower()


def test_build_prompt_truncates_long_transcript():
    long_text = "word " * 10000
    long_transcript = Transcript(
        segments=[TranscriptSegment(start=0.0, end=100.0, text=long_text)],
        language="en",
        model="base.en",
    )
    prompt = _build_prompt(long_transcript, "general")
    assert len(prompt) <= 30100
    assert "[... transcript truncated ...]" in prompt


def test_build_prompt_unknown_style_defaults_to_general(sample_transcript):
    prompt = _build_prompt(sample_transcript, "unknown-style")
    assert SUMMARY_PROMPTS["general"] in prompt


def test_summarize_uses_ethervox_llm_by_default(sample_transcript):
    """summarize() should route through EtherVoxLLM when provider='ethervox'."""
    fake_llm = MagicMock()
    fake_llm.generate.return_value = "EtherVox summary"
    with patch("noteagent.summary.EtherVoxLLM", return_value=fake_llm):
        result = summarize(sample_transcript, style="general", provider="ethervox")
    assert result == "EtherVox summary"
    fake_llm.generate.assert_called_once()
    prompt_used = fake_llm.generate.call_args[0][0]
    assert SUMMARY_PROMPTS["general"] in prompt_used
    assert sample_transcript.full_text in prompt_used


def test_summarize_meeting_style(sample_transcript):
    fake_llm = MagicMock()
    fake_llm.generate.return_value = "Meeting notes"
    with patch("noteagent.summary.EtherVoxLLM", return_value=fake_llm):
        result = summarize(sample_transcript, style="meeting", provider="ethervox")
    assert result == "Meeting notes"
    prompt_used = fake_llm.generate.call_args[0][0]
    assert "Attendees" in prompt_used or "meeting" in prompt_used.lower()


def test_summarize_lecture_style(sample_transcript):
    fake_llm = MagicMock()
    fake_llm.generate.return_value = "Lecture summary"
    with patch("noteagent.summary.EtherVoxLLM", return_value=fake_llm):
        result = summarize(sample_transcript, style="lecture", provider="ethervox")
    assert result == "Lecture summary"


def test_summarize_openai_backend_uses_from_openai(sample_transcript):
    """When llm_backend='openai', summarize() calls EtherVoxLLM.from_openai()."""
    fake_llm = MagicMock()
    fake_llm.generate.return_value = "OpenAI summary"
    with patch("noteagent.summary.EtherVoxLLM") as mock_cls:
        mock_cls.from_openai.return_value = fake_llm
        result = summarize(
            sample_transcript,
            provider="ethervox",
            config={"llm_backend": "openai", "llm_api_key": "sk-test"},
        )
    mock_cls.from_openai.assert_called_once()
    assert result == "OpenAI summary"


def test_summarize_unknown_provider_raises(sample_transcript):
    with pytest.raises(ValueError, match="Unknown summary provider"):
        summarize(sample_transcript, provider="unknown-provider")


def test_summary_prompts_defined():
    assert "general" in SUMMARY_PROMPTS
    assert "meeting" in SUMMARY_PROMPTS
    assert "lecture" in SUMMARY_PROMPTS
    assert len(SUMMARY_PROMPTS["general"]) > 0
    assert len(SUMMARY_PROMPTS["meeting"]) > 0
    assert len(SUMMARY_PROMPTS["lecture"]) > 0


def test_summary_prompt_contains_key_elements():
    meeting_prompt = SUMMARY_PROMPTS["meeting"]
    assert "attendee" in meeting_prompt.lower() or "action" in meeting_prompt.lower()
    lecture_prompt = SUMMARY_PROMPTS["lecture"]
    assert "topic" in lecture_prompt.lower() or "concept" in lecture_prompt.lower()
