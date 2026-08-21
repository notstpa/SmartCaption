"""Tests that saved preferences come back meaning the same thing.

These drive the real window offscreen rather than testing pure functions,
because the bugs they guard against are signal-ordering mistakes in widget
construction -- a value written into a widget before its signal was connected,
so nothing downstream ever hears about it. No pure-function test can see that.

Run with:  python -m pytest tests/ -q
"""

import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytest.importorskip("PyQt6")

from PyQt6.QtCore import QSettings  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

import main  # noqa: E402


# Never the developer's real profile: these tests write preferences, and they
# run on the same machine the app runs on.
PROBE_SCOPE = "SmartCaptionTestProbe"

# Everything the preset dropdown stands for. A preset that restores its name
# but not these is the bug this file exists for.
PRESET_DERIVED = (
    "pause_threshold",
    "max_subtitle_duration",
    "vad_silence_ms",
    "break_on_punctuation_immediate",
    "max_words_per_subtitle",
    "max_chars_per_line",
    "gap_fill",
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    app.setApplicationName(PROBE_SCOPE)
    app.setOrganizationName(PROBE_SCOPE)
    return app


@pytest.fixture
def probe_settings(monkeypatch):
    monkeypatch.setattr(main, "APP_NAME", PROBE_SCOPE)
    settings = QSettings(PROBE_SCOPE, PROBE_SCOPE)
    settings.clear()
    settings.sync()
    yield settings
    settings.clear()
    settings.sync()


def open_window():
    window = main.WhisperApp()
    # Keep the app's real log file out of the test run.
    window._log_file_path = None
    return window


def preset_state(window):
    return {name: getattr(window, name).get() for name in PRESET_DERIVED}


def test_preset_survives_a_restart(qapp, probe_settings):
    first = open_window()
    first.preset_menu.setCurrentText("TikTok")
    saved = preset_state(first)

    # Pinned to the preset table, so this fails if TikTok stops meaning TikTok.
    assert saved == {
        "pause_threshold": 0.5,
        "max_subtitle_duration": 2.0,
        "vad_silence_ms": 500,
        "break_on_punctuation_immediate": True,
        "max_words_per_subtitle": "2",
        "max_chars_per_line": "20",
        "gap_fill": True,
    }

    first.save_settings()

    second = open_window()
    assert second.preset_menu.currentText() == "TikTok"
    assert preset_state(second) == saved


def test_hand_edits_made_after_a_preset_are_not_lost(qapp, probe_settings):
    first = open_window()
    first.preset_menu.setCurrentText("TikTok")
    first.max_words_entry.setText("5")
    first.save_settings()

    second = open_window()
    assert second.max_words_per_subtitle.get() == "5"
    assert second.max_words_entry.text() == "5"


def test_subtitle_scale_reaches_the_renderer(qapp, probe_settings):
    first = open_window()
    first._scale_slider.setValue(150)
    first.save_settings()

    second = open_window()
    assert second._scale_slider.value() == 150
    assert second._scale_value_label.text() == "150%"
    # The value the painter actually uses, not just the one on display.
    assert second._preview_widget.scale_percent == 150


def test_vad_filter_survives_a_restart(qapp, probe_settings):
    first = open_window()
    assert first.vad_filter.get() is True
    first.vad_filter.set(False)
    first.save_settings()

    second = open_window()
    assert second.vad_filter.get() is False
    assert second.get_subtitle_settings()["vad_filter"] is False


def test_default_model_is_the_recommended_one(qapp, probe_settings):
    """A fresh install must default to the model the guide recommends.

    Benchmarked against hand-made captions on gameplay audio, the previous
    default (small, with the voice filter on) missed 55 of 126 words --
    50.8% WER against 14.3% for large-v3-turbo. See benchmark/.
    """
    window = open_window()
    assert window.model_name.get() == "large-v3-turbo"
    recommended = [window.model_menu.itemText(i)
                   for i in range(window.model_menu.count())
                   if "(Recommended)" in window.model_menu.itemText(i)]
    assert len(recommended) == 1
    assert "large-v3-turbo" in recommended[0]


def test_vocabulary_hints_reach_the_transcriber(qapp, probe_settings):
    first = open_window()
    first.vocabulary_entry.setText("defib, extract, backstab")
    assert first.get_subtitle_settings()["initial_prompt"] == "defib, extract, backstab"
    first.save_settings()

    second = open_window()
    assert second.vocabulary_entry.text() == "defib, extract, backstab"


def test_blank_vocabulary_is_sent_as_none(qapp, probe_settings):
    # An empty string would still be tokenized and fed to the decoder as a
    # prompt; only None means "no prompt".
    window = open_window()
    window.vocabulary_entry.setText("   ")
    assert window.get_subtitle_settings()["initial_prompt"] is None
