"""Tests for SmartCaption's subtitle text and timing pipeline.

These cover the pure functions in main.py -- no Qt, no app state -- which is
where the caption correctness rules actually live.

Run with:  python -m pytest tests/ -q
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import (  # noqa: E402
    MAX_CHARS_PER_SECOND,
    MAX_GAP_FILL,
    MAX_SUBTITLE_LINES,
    MIN_SUBTITLE_DURATION,
    apply_gap_fill,
    censor_word,
    format_srt_timestamp,
    join_words,
    normalize_subtitle_text,
    normalize_subtitle_timings,
    split_segment_text,
    wrap_subtitle_lines,
    wrap_text_to_lines,
)


BASE_SETTINGS = {
    "max_chars": 42,
    "max_words": 8,
    "max_subtitle_duration": 3.2,
    "remove_punctuation": False,
    "text_case": "Normal",
    "censor_profanity": False,
}


def settings(**overrides):
    return {**BASE_SETTINGS, **overrides}


def seg(start, end, text):
    return {"start": start, "end": end, "text": text}


class Word:
    """Stand-in for faster-whisper's word object."""

    def __init__(self, word, start, end):
        self.word = word
        self.start = start
        self.end = end


# ── wrapping ──

def test_wrap_respects_max_chars():
    lines = wrap_text_to_lines("the quick brown fox jumps over the lazy dog", 20)
    assert all(len(line) <= 20 for line in lines)
    assert " ".join(lines) == "the quick brown fox jumps over the lazy dog"


def test_wrap_empty_text_returns_no_lines():
    assert wrap_text_to_lines("", 42) == []
    assert wrap_text_to_lines("   ", 42) == []


def test_word_longer_than_limit_still_emitted():
    # Better an over-long line than a dropped word.
    lines = wrap_text_to_lines("supercalifragilisticexpialidocious", 10)
    assert lines == ["supercalifragilisticexpialidocious"]


def test_wrap_text_does_not_apply_case_or_censoring():
    # This is what lets manual edits be re-wrapped without being re-transformed.
    assert wrap_text_to_lines("Damn It", 42) == ["Damn It"]


# ── text normalization ──

def test_uppercase_and_lowercase():
    assert normalize_subtitle_text("Hello There", settings(text_case="UPPERCASE")) == "HELLO THERE"
    assert normalize_subtitle_text("Hello There", settings(text_case="lowercase")) == "hello there"


def test_remove_punctuation():
    out = normalize_subtitle_text("Hi, there! Really?", settings(remove_punctuation=True))
    assert out == "Hi there Really"


def test_whitespace_is_collapsed():
    assert normalize_subtitle_text("a   b \n c", settings()) == "a b c"


# ── profanity censoring ──

@pytest.mark.parametrize("word,expected", [
    ("fuck", "f***"),
    ("fucking,", "f******,"),      # trailing punctuation preserved
    ("damn.", "d***."),
    ('"shit"', '"s***"'),          # wrapping quotes preserved
    ("motherfucker", "m***********"),
    ("Fucking", "F******"),        # case of first letter preserved
])
def test_censor_masks_word_but_keeps_punctuation(word, expected):
    assert censor_word(word) == expected


@pytest.mark.parametrize("word", ["assassin", "classy", "bassist", "hello", "grass"])
def test_censor_does_not_match_substrings(word):
    assert censor_word(word) == word


def test_censoring_applied_through_wrap():
    out = wrap_subtitle_lines("what the fuck", settings(censor_profanity=True))
    assert out == ["what the f***"]


# ── minimum duration and reading speed ──

def test_short_subtitle_extended_to_minimum():
    out, _ = normalize_subtitle_timings([seg(0.0, 0.05, "No")])
    assert out[0]["end"] - out[0]["start"] == pytest.approx(MIN_SUBTITLE_DURATION)


def test_extension_never_overlaps_next_subtitle():
    out, _ = normalize_subtitle_timings([
        seg(0.0, 0.05, "No"),
        seg(0.5, 0.6, "Yes"),
        seg(5.0, 5.1, "Ok"),
    ])
    for current, following in zip(out, out[1:]):
        assert current["end"] <= following["start"]


def test_long_line_gets_reading_time():
    text = "x" * 60  # 60 chars needs 3s at 20 cps
    out, _ = normalize_subtitle_timings([seg(0.0, 0.1, text)])
    assert out[0]["end"] == pytest.approx(60 / MAX_CHARS_PER_SECOND)


def test_reading_time_uses_longest_line_not_total():
    # Wrapped lines are read together, so total chars would overstate the need.
    out, _ = normalize_subtitle_timings([seg(0.0, 0.1, "x" * 20 + "\n" + "y" * 20)])
    assert out[0]["end"] == pytest.approx(20 / MAX_CHARS_PER_SECOND)


def test_existing_long_duration_is_left_alone():
    out, _ = normalize_subtitle_timings([seg(0.0, 8.0, "Hi")])
    assert out[0]["end"] == 8.0


def test_overlapping_input_is_pushed_apart():
    out, _ = normalize_subtitle_timings([seg(0.0, 5.0, "a"), seg(2.0, 6.0, "b")])
    assert out[1]["start"] >= out[0]["end"]


def test_empty_input():
    assert normalize_subtitle_timings([]) == ([], [])


def test_large_gap_is_reported():
    _, warnings = normalize_subtitle_timings([seg(0.0, 1.0, "a"), seg(30.0, 31.0, "b")])
    assert warnings == [2]


def test_no_warning_for_small_gap():
    _, warnings = normalize_subtitle_timings([seg(0.0, 1.0, "a"), seg(2.0, 3.0, "b")])
    assert warnings == []


# ── gap fill ──

def test_gap_fill_bridges_short_gap():
    out = apply_gap_fill([seg(0.0, 1.0, "a"), seg(1.5, 2.0, "b")])
    assert out[0]["end"] == 1.5


def test_gap_fill_does_not_bridge_long_silence():
    # A musical break must not leave the previous caption frozen on screen.
    out = apply_gap_fill([seg(0.0, 1.0, "a"), seg(45.0, 46.0, "b")])
    assert out[0]["end"] == 1.0


def test_gap_fill_boundary_is_inclusive():
    out = apply_gap_fill([seg(0.0, 1.0, "a"), seg(1.0 + MAX_GAP_FILL, 5.0, "b")])
    assert out[0]["end"] == 1.0 + MAX_GAP_FILL


def test_gap_fill_leaves_last_segment_alone():
    out = apply_gap_fill([seg(0.0, 1.0, "a"), seg(1.2, 2.0, "b")])
    assert out[-1]["end"] == 2.0


def test_gap_fill_noop_for_single_segment():
    single = [seg(0.0, 1.0, "a")]
    assert apply_gap_fill(single) == single


# ── segment splitting ──

def test_long_segment_never_exceeds_line_budget():
    parts = split_segment_text("word " * 60, 0.0, 30.0, settings())
    assert len(parts) > 1
    for part in parts:
        assert len(part["text"].split("\n")) <= MAX_SUBTITLE_LINES


def test_split_preserves_segment_bounds():
    parts = split_segment_text("word " * 60, 4.0, 34.0, settings())
    assert parts[0]["start"] == 4.0
    assert parts[-1]["end"] == 34.0


def test_split_timings_are_monotonic():
    parts = split_segment_text("word " * 60, 0.0, 30.0, settings())
    for current, following in zip(parts, parts[1:]):
        assert current["end"] <= following["start"] + 1e-9


def test_short_segment_stays_single():
    parts = split_segment_text("Just a short line.", 1.0, 2.0, settings())
    assert len(parts) == 1
    assert parts[0]["start"] == 1.0 and parts[0]["end"] == 2.0


def test_empty_segment_produces_nothing():
    assert split_segment_text("", 0.0, 1.0, settings()) == []


def test_zero_duration_segment_does_not_crash():
    parts = split_segment_text("word " * 60, 5.0, 5.0, settings())
    assert all(p["start"] == 5.0 and p["end"] == 5.0 for p in parts)


# ── SRT formatting ──

@pytest.mark.parametrize("seconds,expected", [
    (0.0, "00:00:00,000"),
    (1.5, "00:00:01,500"),
    (61.25, "00:01:01,250"),
    (3661.001, "01:01:01,001"),
])
def test_srt_timestamp_format(seconds, expected):
    assert format_srt_timestamp(seconds) == expected


# ── word joining ──

def test_join_words_preserves_whisper_spacing():
    words = [Word(" Hello", 0.0, 0.5), Word(" world", 0.5, 1.0)]
    assert join_words(words) == "Hello world"


# ── end-to-end invariants ──

def test_pipeline_output_always_satisfies_caption_rules():
    raw = [seg(i * 0.5, i * 0.5 + 0.05, f"word{i} " * 30) for i in range(10)]
    normalized = [
        part
        for s in raw
        for part in split_segment_text(s["text"], s["start"], s["end"], settings())
    ]
    out, _ = normalize_subtitle_timings(normalized)

    for part in out:
        assert len(part["text"].split("\n")) <= MAX_SUBTITLE_LINES
        assert part["end"] >= part["start"]
    for current, following in zip(out, out[1:]):
        assert current["end"] <= following["start"], "subtitles must never overlap"


# ── timing is only ever extended, never trimmed ──

def test_normalize_never_shortens_a_subtitle():
    # Back-to-back captions have no room to grow. The gap clamp must not then
    # cut them below the speech they actually cover.
    raw = [seg(0.0, 0.5, "hello"), seg(0.5, 1.0, "there"), seg(1.0, 1.6, "friend")]
    out, _ = normalize_subtitle_timings(raw)
    for before, after in zip(raw, out):
        assert (after["end"] - after["start"]) >= (before["end"] - before["start"]) - 1e-9


def test_back_to_back_subtitle_keeps_its_full_duration():
    out, _ = normalize_subtitle_timings([seg(0.0, 0.5, "a"), seg(0.5, 1.0, "b")])
    assert out[0]["end"] == pytest.approx(0.5)   # not trimmed back to 0.46
    assert out[1]["end"] >= 1.0                  # the last one is free to grow


# ── segment splitting honours the word and duration budgets ──

def test_split_respects_max_words():
    text = " ".join(f"w{i}" for i in range(12))
    # max_subtitle_duration off, so only the word budget can force a split.
    parts = split_segment_text(
        text, 0.0, 12.0,
        settings(max_words=3, max_chars=60, max_subtitle_duration=None),
    )
    assert len(parts) == 4
    for part in parts:
        assert len(part["text"].split()) <= 3


def test_split_respects_max_subtitle_duration():
    # A single line is always emitted whole, so the cap cannot be absolute --
    # but tightening it must still produce more, shorter captions.
    text = " ".join(f"word{i}" for i in range(24))
    loose = split_segment_text(text, 0.0, 24.0, settings(max_chars=30, max_subtitle_duration=99.0))
    tight = split_segment_text(text, 0.0, 24.0, settings(max_chars=30, max_subtitle_duration=2.0))
    assert len(tight) > len(loose)


def test_split_preserves_every_word_under_a_tight_budget():
    text = " ".join(f"w{i}" for i in range(40))
    parts = split_segment_text(text, 0.0, 20.0, settings(max_words=3, max_chars=42))
    joined = " ".join(part["text"].replace("\n", " ") for part in parts)
    assert joined.split() == text.split()


def test_split_emits_an_over_budget_word_rather_than_dropping_it():
    # A word too long for max_chars cannot be split any further; it still has
    # to come out rather than being silently discarded.
    text = "supercalifragilisticexpialidocious and more"
    parts = split_segment_text(text, 0.0, 3.0, settings(max_words=1, max_chars=5))
    assert " ".join(part["text"] for part in parts).split() == text.split()


def test_split_without_budgets_still_works():
    # The pipeline calls this with a settings dict that predates both keys.
    bare = {"max_chars": 42, "remove_punctuation": False,
            "text_case": "Normal", "censor_profanity": False}
    parts = split_segment_text("word " * 60, 0.0, 30.0, bare)
    assert parts
    for part in parts:
        assert len(part["text"].split("\n")) <= MAX_SUBTITLE_LINES


# ── censoring only masks whole runs of letters ──

@pytest.mark.parametrize("word,expected", [
    ("f.u.c.k", "f.u.c.k"),     # separated letters are not the word
    ("fuck-you", "f***-you"),   # compounds mask only the profane run
    ("...", "..."),
    ("1234", "1234"),
    ("", ""),
])
def test_censor_only_masks_whole_letter_runs(word, expected):
    assert censor_word(word) == expected


# ── SRT timestamps ──

@pytest.mark.parametrize("seconds,expected", [
    (-0.5, "00:00:00,000"),     # negatives would format as "-1:59:59,500"
    (-10.0, "00:00:00,000"),
    (0.0009, "00:00:00,001"),   # rounded, not truncated away
    (1.9996, "00:00:02,000"),
])
def test_srt_timestamp_clamps_and_rounds(seconds, expected):
    assert format_srt_timestamp(seconds) == expected
