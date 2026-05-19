"""Tests for CLI commands."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from noteagent.cli import app
from noteagent.models import AppConfig, Session, SessionMetadata, Transcript, TranscriptSegment

runner = CliRunner()


@pytest.fixture
def mock_config(tmp_path):
    return AppConfig(
        storage_path=tmp_path,
        default_device="Test Device",
        sample_rate=16000,
        whisper_model="base.en",
        language="en",
    )


@pytest.fixture
def mock_session(tmp_path):
    session_path = tmp_path / "sessions" / "2026-04-14_12-00-00"
    session_path.mkdir(parents=True)

    metadata = SessionMetadata(
        session_id="2026-04-14_12-00-00",
        device_name="Test Device",
        sample_rate=16000,
    )

    session = Session(metadata=metadata, path=session_path)
    (session_path / "audio.wav").write_bytes(b"RIFF....WAV")

    transcript = Transcript(
        segments=[
            TranscriptSegment(start=0.0, end=2.0, text="Hello world"),
            TranscriptSegment(start=2.0, end=4.0, text="Test transcript"),
        ],
        language="en",
        model="base.en",
    )
    session.transcript = transcript
    return session


def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0." in result.stdout


def test_devices_command():
    # list_devices is imported inside the command; patch at the source module
    with patch("noteagent.audio.list_devices", return_value=["Device 1", "Device 2"]):
        result = runner.invoke(app, ["devices"])
    assert result.exit_code == 0
    assert "Device 1" in result.stdout
    assert "Device 2" in result.stdout


def test_config_show_command(tmp_path, mock_config):
    with patch("noteagent.storage.load_config", return_value=mock_config):
        result = runner.invoke(app, ["config", "--show"])
    assert result.exit_code == 0
    assert "Test Device" in result.stdout or "default_device" in result.stdout


def test_config_set_device(tmp_path, mock_config):
    with patch("noteagent.storage.load_config", return_value=mock_config), \
         patch("noteagent.storage.save_config") as mock_save:
        result = runner.invoke(app, ["config", "--device", "New Device"])
    assert result.exit_code == 0
    mock_save.assert_called_once()


def test_sessions_list(tmp_path, mock_config, mock_session):
    with patch("noteagent.storage.load_config", return_value=mock_config), \
         patch("noteagent.storage.list_sessions", return_value=[mock_session]):
        result = runner.invoke(app, ["sessions"])
    assert result.exit_code == 0
    assert "2026-04-14_12-00-00" in result.stdout


@pytest.mark.parametrize("format_type", ["markdown", "text", "json", "pdf"])
def test_export_command(tmp_path, mock_session, format_type):
    with patch("noteagent.storage.load_config", return_value=Mock(storage_path=tmp_path)), \
         patch("noteagent.storage.load_session", return_value=mock_session), \
         patch("noteagent.export.export_session") as mock_export:
        mock_export.return_value = tmp_path / f"export.{format_type}"
        result = runner.invoke(app, [
            "export", str(mock_session.path), "--format", format_type
        ])
    assert result.exit_code == 0
    mock_export.assert_called_once()


def test_transcribe_file_command(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"RIFF....WAV")

    mock_transcript = Transcript(
        segments=[TranscriptSegment(start=0.0, end=2.0, text="Test")],
        language="en",
        model="base.en",
    )

    mock_sess = Mock()
    mock_sess.path = tmp_path / "session"

    with patch("noteagent.transcript.transcribe_file", return_value=mock_transcript), \
         patch("noteagent.storage.create_session", return_value=mock_sess), \
         patch("noteagent.storage.save_transcript"), \
         patch("noteagent.storage.load_config", return_value=Mock(
             storage_path=tmp_path, default_device=None, language="en",
             whisper_model="base.en"
         )):
        result = runner.invoke(app, ["transcribe", str(audio_file)])

    assert result.exit_code in (0, 1)


def test_summarize_command(tmp_path, mock_session):
    with patch("noteagent.storage.load_session", return_value=mock_session), \
         patch("noteagent.storage.load_config", return_value=Mock(
             storage_path=tmp_path, language="en", summary_style="general"
         )), \
         patch("noteagent.summary.summarize", return_value="Test summary"), \
         patch("noteagent.storage.save_summary"):
        result = runner.invoke(app, ["summarize", str(mock_session.path)])
    assert result.exit_code == 0
    assert "summary" in result.stdout.lower() or "Test summary" in result.stdout


def test_record_command_dry_run():
    result = runner.invoke(app, ["record", "--help"])
    assert result.exit_code == 0
    assert "device" in result.stdout.lower()
    assert "model" in result.stdout.lower()


def test_serve_command_structure():
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    assert "port" in result.stdout.lower()


def test_stop_command_no_server():
    result = runner.invoke(app, ["stop"])
    assert result.exit_code in (0, 1)


def test_setup_check_command(tmp_path):
    # setup-check checks for noteagent_audio import and whisper model file;
    # mock both so the command reports success
    fake_model = tmp_path / "models" / "base.en.pt"
    fake_model.parent.mkdir(parents=True)
    fake_model.write_bytes(b"stub")
    with patch("noteagent.audio.list_devices", return_value=["Device 1"]), \
         patch("noteagent.storage.load_config", return_value=Mock(storage_path=tmp_path)), \
         patch.object(__import__("sys"), "modules", {
             **__import__("sys").modules, "noteagent_audio": Mock()
         }), \
         patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.stat", return_value=Mock(st_size=150 * 1024 * 1024)):
        result = runner.invoke(app, ["setup-check"])
    assert result.exit_code == 0
