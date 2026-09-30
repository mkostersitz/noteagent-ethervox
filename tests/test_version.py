"""Tests for version reporting and cross-file version consistency."""

import plistlib
import re
from pathlib import Path

from noteagent import __version__, get_version

REPO_ROOT = Path(__file__).resolve().parents[1]


def _pyproject_version() -> str:
    text = (REPO_ROOT / "pyproject.toml").read_text()
    return re.search(r'^version = "([^"]+)"', text, re.MULTILINE).group(1)


def test_get_version_matches_package_version():
    assert get_version() == __version__


def test_package_version_matches_pyproject():
    assert __version__ == _pyproject_version()


def test_package_version_matches_macos_app():
    with open(REPO_ROOT / "apps/macos/NoteAgent/Info.plist", "rb") as fh:
        plist = plistlib.load(fh)
    assert plist["CFBundleShortVersionString"] == __version__

    pbxproj = (REPO_ROOT / "apps/macos/NoteAgent.xcodeproj/project.pbxproj").read_text()
    marketing = set(re.findall(r"MARKETING_VERSION = ([^;]+);", pbxproj))
    assert marketing == {__version__}
