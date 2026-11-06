import pytest
from simai_parser import _NOTE_RE, _parse_hold_duration_ms


class TestNoteRegex:
    """Tests for matching individual note fragments using _NOTE_RE."""

    @pytest.mark.parametrize("frag,expected_button,expected_mods", [
        ("1", 1, ""),
        ("8", 8, ""),
        ("2b", 2, "b"),
        ("3x", 3, "x"),
        ("4bx", 4, "bx"),
        ("5xb", 5, "xb"),
    ])
    def test_tap_notes_and_modifiers(self, frag: str, expected_button: int, expected_mods: str):
        m = _NOTE_RE.match(frag)
        assert m is not None
        assert int(m.group("button")) == expected_button
        assert (m.group("mods") or "") == expected_mods
        assert m.group("hdur") is None

    @pytest.mark.parametrize("frag,expected_button,expected_mods,expected_wait,expected_dur", [
        ("1h[4:1]", 1, "", "4", "1"),
        ("2bh[8:3]", 2, "b", "8", "3"),
        ("3xh[1:2]", 3, "x", "1", "2"),
        ("4bxh[16:5]", 4, "bx", "16", "5"),
        ("5h[2]", 5, "", None, "2"),  # Implicit subdivision
    ])
    def test_hold_notes(self, frag: str, expected_button: int, expected_mods: str, expected_wait: str | None, expected_dur: str):
        m = _NOTE_RE.match(frag)
        assert m is not None
        assert int(m.group("button")) == expected_button
        assert (m.group("mods") or "") == expected_mods
        assert m.group("hwait") == expected_wait
        assert m.group("hdur") == expected_dur

    @pytest.mark.parametrize("invalid_frag", [
        # Slide notes
        "1-5[4:1]",
        "2>6[1:1]",
        "3<7[4:1]",
        "4^8[4:1]",
        "5v1[4:1]",
        "6p2[4:1]",
        "7q3[4:1]",
        "8s4[4:1]",
        "1z5[4:1]",
        "2pp6[4:1]",
        "3qq7[4:1]",
        "4w8[4:1]",
        "1V35[4:1]",
        "4pp4[2:1]*qq4[2:1]",
        # Touch sensor zones & fireworks
        "C",
        "C1",
        "C1f",
        "A1",
        "B2",
        "D3",
        "E5",
        "E5h[1:1]",
        # Invalid buttons or out of range
        "0",
        "9",
        "A",
        "10",
        # Malformed hold syntax
        "1h",
        "1h[]",
        "1h[4:]",
        "1h[:2]",
        # Empty and non-note characters
        "",
        ",",
        "/",
        "E",
        "*",
    ])
    def test_unsupported_or_invalid_fragments_ignored(self, invalid_frag: str):
        """Verify that slides, touch notes, and malformed strings do not match as tap/hold."""
        m = _NOTE_RE.match(invalid_frag)
        assert m is None


class TestHoldDurationCalculation:
    """Tests for _parse_hold_duration_ms mathematical accuracy."""

    def test_explicit_wait_subdivision(self):
        # 120 BPM -> 1 beat (4th) = 500ms
        # wait=4, dur=1 -> 1 quarter note = 500ms
        dur = _parse_hold_duration_ms(wait_sub="4", dur_beats="1", bpm=120.0, subdivision=4)
        assert dur == pytest.approx(500.0)

        # wait=8, dur=3 -> 3 eighth notes = 3 * 250ms = 750ms
        dur = _parse_hold_duration_ms(wait_sub="8", dur_beats="3", bpm=120.0, subdivision=4)
        assert dur == pytest.approx(750.0)

    def test_implicit_subdivision_fallback(self):
        # If wait_sub is None, falls back to the active subdivision (e.g. 8)
        # 120 BPM with active subdivision 8 -> 1 step = 250ms
        # dur=2 steps = 500ms
        dur = _parse_hold_duration_ms(wait_sub=None, dur_beats="2", bpm=120.0, subdivision=8)
        assert dur == pytest.approx(500.0)

    def test_high_bpm_and_subdivision(self):
        # 240 BPM -> beat = 250ms
        # wait=16, dur=4 -> 4 16th notes = 1 quarter beat = 250ms
        dur = _parse_hold_duration_ms(wait_sub="16", dur_beats="4", bpm=240.0, subdivision=4)
        assert dur == pytest.approx(250.0)

