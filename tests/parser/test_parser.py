from pathlib import Path
import pytest
from simai_parser import parse_maidata_file, parse_chart, write_processed_chart
from tokens import NoteType
from geometry_transformation import (
    _calculate_theta_pos,
    RADII,
    BUTTON_ANGLES,
    PRECOMPUTED_PERIMETER_CANDIDATES,
)
import math


class TestMaidataFileParsing:
    """Tests for parse_maidata_file handling metadata, levels, and format quirks."""

    def test_parse_maidata_file_happy_path(self, tmp_path: Path):
        maidata_content = (
            "&title=Test Song\n"
            "&artist=Test Artist\n"
            "&first=0.5\n"
            "&lv_1=5\n"
            "&lv_5=12+\n"
            "&inote_1=(120){4}1,2,3,4,\n"
            "&inote_5=(150){4}1/5,E\n"
        )
        test_file = tmp_path / "maidata_test.txt"
        test_file.write_text(maidata_content, encoding="utf-8")

        result = parse_maidata_file(test_file)

        assert result["metadata"]["title"] == "Test Song"
        assert result["metadata"]["artist"] == "Test Artist"
        assert result["metadata"]["first"] == "0.5"
        assert result["levels"][1] == "5"
        assert result["levels"][5] == "12+"
        assert 1 in result["charts"]
        assert 5 in result["charts"]

    def test_parse_maidata_with_crlf_and_trailing_whitespace(self, tmp_path: Path):
        """Ensure Windows-style CRLF line breaks and whitespace around values are handled."""
        maidata_content = (
            "&title=  Spaced Song  \r\n"
            "&artist=Spaced Artist\r\n"
            "&lv_2= 7 \r\n"
            "&inote_2=\r\n(130){4}1,2,3,4,\r\n"
        )
        test_file = tmp_path / "crlf_test.txt"
        test_file.write_text(maidata_content, encoding="utf-8")

        result = parse_maidata_file(test_file)
        assert result["metadata"]["title"] == "Spaced Song"
        assert result["levels"][2] == "7"
        assert "(130){4}1,2,3,4," in result["charts"][2]

    def test_parse_maidata_empty_or_missing_sections(self, tmp_path: Path):
        """Ensure file without charts or levels doesn't raise errors."""
        maidata_content = "&title=Empty Song\n&artist=Nobody\n"
        test_file = tmp_path / "empty_test.txt"
        test_file.write_text(maidata_content, encoding="utf-8")

        result = parse_maidata_file(test_file)
        assert result["metadata"]["title"] == "Empty Song"
        assert result["levels"] == {}
        assert result["charts"] == {}


class TestChartParsing:
    """Tests for parse_chart timeline progression, state changes, and edge cases."""

    def test_parse_chart_happy_path(self):
        """Test full mix of BPM, subdivisions, modifiers, holds, simultaneous notes, and skipped slides."""
        chart_str = "(120){4}1b,2x/8,3h[4:1],{8}1-5[4:1],4,E"
        groups = parse_chart(chart_str)

        assert len(groups) == 4

        # Group 0: @0ms -> [1b]
        g0 = groups[0]
        assert g0.time_ms == pytest.approx(0.0)
        assert len(g0.notes) == 1
        assert g0.notes[0].button == 1
        assert g0.notes[0].note_type == NoteType.TAP
        assert g0.notes[0].is_break is True
        assert g0.notes[0].is_ex is False
        assert len(g0.notes[0].circle_coord) == 2

        # Group 1: @500ms -> [2x, 8]
        g1 = groups[1]
        assert g1.time_ms == pytest.approx(500.0)
        assert len(g1.notes) == 2
        n_2x = next(n for n in g1.notes if n.button == 2)
        n_8 = next(n for n in g1.notes if n.button == 8)
        assert n_2x.is_ex is True
        assert n_8.is_ex is False

        # Group 2: @1000ms -> [3h(500ms)]
        g2 = groups[2]
        assert g2.time_ms == pytest.approx(1000.0)
        assert len(g2.notes) == 1
        assert g2.notes[0].button == 3
        assert g2.notes[0].note_type == NoteType.HOLD
        assert g2.notes[0].hold_duration_ms == pytest.approx(500.0)

        # Group 3: @1750ms -> [4] (slide at 1500ms is skipped, 250ms eighth note step)
        g3 = groups[3]
        assert g3.time_ms == pytest.approx(1750.0)
        assert len(g3.notes) == 1
        assert g3.notes[0].button == 4

    def test_consecutive_commas_as_rests(self):
        """Verify consecutive commas advance time without adding empty groups."""
        # At 120 BPM with {4}, 1 beat = 500ms.
        # Slot 0 @0ms: note 1
        # Comma 1: moves to 500ms (empty rest)
        # Comma 2: moves to 1000ms (empty rest)
        # Slot 3 @1000ms: note 2
        chart_str = "(120){4}1,,,2,E"
        groups = parse_chart(chart_str)

        assert len(groups) == 2
        assert groups[0].time_ms == pytest.approx(0.0)
        assert groups[0].notes[0].button == 1

        assert groups[1].time_ms == pytest.approx(1500.0)
        assert groups[1].notes[0].button == 2

    def test_dynamic_bpm_and_subdivision_changes(self):
        """Verify mid-stream tempo and subdivision changes take effect immediately."""
        # (120){4} -> 500ms per step
        # 1, @0ms -> next is 500ms
        # (240){8} -> 240 BPM eighth notes: (60000 / 240) * (4 / 8) = 250 * 0.5 = 125ms per step
        # 2, @500ms -> next is 500 + 125 = 625ms
        # 3, @625ms
        chart_str = "(120){4}1,(240){8}2,3,E"
        groups = parse_chart(chart_str)

        assert len(groups) == 3
        assert groups[0].time_ms == pytest.approx(0.0)
        assert groups[1].time_ms == pytest.approx(500.0)
        assert groups[2].time_ms == pytest.approx(625.0)

    def test_multi_simultaneous_mixed_notes(self):
        """Verify simultaneous group containing tap, hold, and break/ex."""
        # 3 simultaneous notes: 1 (tap), 2h[4:1] (hold), 3bx (break+ex tap)
        chart_str = "(120){4}1/2h[4:1]/3bx,E"
        groups = parse_chart(chart_str)

        assert len(groups) == 1
        group = groups[0]
        assert len(group.notes) == 3

        buttons = {n.button: n for n in group.notes}
        assert buttons[1].note_type == NoteType.TAP
        assert buttons[2].note_type == NoteType.HOLD
        assert buttons[2].hold_duration_ms == pytest.approx(500.0)
        assert buttons[3].is_break is True
        assert buttons[3].is_ex is True

    def test_unsupported_all_filtered_produces_empty_result(self):
        """Chart consisting only of slides and touch notes should yield 0 note groups."""
        chart_str = "(120){4}1-5[4:1],C,B2,2>6[1:1],E"
        groups = parse_chart(chart_str)
        assert len(groups) == 0

    def test_whitespace_and_newline_tolerance(self):
        """Simai charts often have linebreaks and indentation."""
        chart_str = """
        (120) {4}
        1 ,
        2 / 3 ,
        E
        """
        groups = parse_chart(chart_str)
        assert len(groups) == 2
        assert groups[0].time_ms == pytest.approx(0.0)
        assert groups[1].time_ms == pytest.approx(500.0)
        assert len(groups[1].notes) == 2

    def test_note_immediately_preceding_e_without_trailing_comma(self):
        """A note flush should occur if E terminates the chart without a trailing comma."""
        chart_str = "(120){4}1,2E"
        groups = parse_chart(chart_str)
        assert len(groups) == 2
        assert groups[1].notes[0].button == 2


class TestWriteProcessedChart:
    """Tests for file writing functionality."""

    def test_write_processed_chart_happy_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("simai_parser.Path", lambda p: tmp_path / p if p == "data/processed" else Path(p))
        (tmp_path / "data" / "processed").mkdir(parents=True, exist_ok=True)

        chart_str = "(120){4}1,2,E"
        groups = parse_chart(chart_str)

        filename = "test_output.txt"
        write_processed_chart(groups, filename)

        output_file = tmp_path / "data" / "processed" / filename
        assert output_file.exists()

        lines = output_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
        assert lines[0].startswith("@0.0ms [1]")
        assert lines[1].startswith("@500.0ms [2]")


class TestGeometryTransformation:
    """Tests for geometric transformation calculations and candidate touch positions."""

    def test_calculate_theta_pos_axes_and_cardinals(self):
        """Happy path: test standard trigonometric angles (0, 90, 180, 270 deg)."""
        # 0 rad (3 o'clock) -> (r, 0)
        assert _calculate_theta_pos(1.0, 0.0) == (1.0, 0.0)
        # pi/2 rad (12 o'clock) -> (0, r)
        assert _calculate_theta_pos(1.0, math.pi / 2) == (0.0, 1.0)
        # pi rad (9 o'clock) -> (-r, 0)
        assert _calculate_theta_pos(1.0, math.pi) == (-1.0, 0.0)
        # 3*pi/2 rad (6 o'clock) -> (0, -r)
        assert _calculate_theta_pos(1.0, 3 * math.pi / 2) == (0.0, -1.0)

    def test_calculate_theta_pos_scaling_with_radius(self):
        """Verify scaling by touch sensor radii (e.g. A, B, center C)."""
        # Radius 0 (Center touch C) always evaluates to origin (0, 0)
        assert _calculate_theta_pos(RADII["C"], math.pi / 3) == (0.0, 0.0)
        assert _calculate_theta_pos(RADII["C"], 0.0) == (0.0, 0.0)

        # Scaled radius along x-axis
        assert _calculate_theta_pos(RADII["A"], 0.0) == (0.88, 0.0)
        assert _calculate_theta_pos(RADII["B"], 0.0) == (0.72, 0.0)

    def test_button_angles_clockwise_progression(self):
        """Verify button 1 starts at upper-right (67.5 deg) and rotates clockwise."""
        # Button 1 is at 3pi/8 (67.5 degrees)
        assert BUTTON_ANGLES[1] == pytest.approx(3 * math.pi / 8)
        # Step between buttons is -pi/4 (-45 degrees clockwise)
        for k in range(1, 8):
            diff = BUTTON_ANGLES[k] - BUTTON_ANGLES[k + 1]
            assert diff == pytest.approx(math.pi / 4)

    def test_precomputed_candidates_contain_button_and_touch_contacts(self):
        """Verify each button 1-8 has exactly two candidate coords on unit and A radii."""
        assert len(PRECOMPUTED_PERIMETER_CANDIDATES) == 8
        for k in range(1, 9):
            candidates = PRECOMPUTED_PERIMETER_CANDIDATES[k]
            assert len(candidates) == 2

            button_pt, touch_pt = candidates
            # Distance from center for switch contact should be 1.0
            r_button = math.hypot(button_pt[0], button_pt[1])
            assert r_button == pytest.approx(1.0, abs=1e-3)

            # Distance from center for glass touch contact should be 0.88
            r_touch = math.hypot(touch_pt[0], touch_pt[1])
            assert r_touch == pytest.approx(0.88, abs=1e-3)

    def test_button_symmetry_opposites(self):
        """Edge case: Opposing buttons (1 and 5, 2 and 6, etc.) should be symmetric through the origin."""
        for k in range(1, 5):
            opp = k + 4
            btn_k = PRECOMPUTED_PERIMETER_CANDIDATES[k][0]
            btn_opp = PRECOMPUTED_PERIMETER_CANDIDATES[opp][0]
            assert btn_k[0] == pytest.approx(-btn_opp[0], abs=1e-4)
            assert btn_k[1] == pytest.approx(-btn_opp[1], abs=1e-4)

    def test_parsed_notes_receive_correct_geometry(self):
        """Integration: verify parsed notes in a chart receive exact precomputed candidates."""
        chart_str = "(120){4}1,5,E"
        groups = parse_chart(chart_str)
        assert len(groups) == 2

        note_1 = groups[0].notes[0]
        note_5 = groups[1].notes[0]

        assert note_1.circle_coord == PRECOMPUTED_PERIMETER_CANDIDATES[1]
        assert note_5.circle_coord == PRECOMPUTED_PERIMETER_CANDIDATES[5]

