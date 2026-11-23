import math
import pytest
from mai_solver.hand_solver import (
    SolverConfig,
    TrellisNode,
    expand_trellis,
)
from mai_solver.chart_objects import (
    NoteEvent,
    NoteType,
    TimedNoteGroup,
)


@pytest.fixture
def default_config():
    return SolverConfig()


def make_tap(time_ms: float, button: int, pos: tuple[float, float]) -> NoteEvent:
    return NoteEvent(
        time_ms=time_ms,
        note_type=NoteType.TAP,
        button=button,
        circle_coord=[pos],
    )


def make_hold(time_ms: float, button: int, pos: tuple[float, float], duration_ms: float) -> NoteEvent:
    return NoteEvent(
        time_ms=time_ms,
        note_type=NoteType.HOLD,
        button=button,
        circle_coord=[pos],
        hold_duration_ms=duration_ms,
    )


# ==============================================================================
# Single Note Expansion Tests
# ==============================================================================

class TestTrellisExpansionSingleNote:
    def test_single_tap_generates_two_candidates(self, default_config):
        """A single tap note should branch into 2 candidates: LH plays or RH plays."""
        prev = TrellisNode(
            left_hand_pos=(-0.5, 0.5),
            right_hand_pos=(0.5, 0.5),
            total_score=1.0,
        )
        note_pos = (0.0, 1.0)
        group = TimedNoteGroup(100.0, [make_tap(100.0, 1, note_pos)])

        cands = expand_trellis(default_config, prev, 0.0, 3, group)
        assert len(cands) == 2

        # Candidate 1: Left hand moves to note, Right hand stays
        cand_lh = next(c for c in cands if c.left_used)
        assert cand_lh.left_hand_pos == pytest.approx(note_pos)
        assert cand_lh.right_hand_pos == pytest.approx(prev.right_hand_pos)
        assert not cand_lh.right_used
        assert cand_lh.prev_node == 3
        assert cand_lh.total_score > 1.0

        # Candidate 2: Right hand moves to note, Left hand stays
        cand_rh = next(c for c in cands if c.right_used)
        assert cand_rh.right_hand_pos == pytest.approx(note_pos)
        assert cand_rh.left_hand_pos == pytest.approx(prev.left_hand_pos)
        assert not cand_rh.left_used
        assert cand_rh.prev_node == 3
        assert cand_rh.total_score > 1.0

    def test_single_hold_sets_lock_timestamp(self, default_config):
        """Playing a HOLD note must update lock_until for that hand."""
        prev = TrellisNode(
            left_hand_pos=(-0.5, 0.5),
            right_hand_pos=(0.5, 0.5),
            total_score=0.0,
        )
        group = TimedNoteGroup(100.0, [make_hold(100.0, 1, (0.0, 1.0), duration_ms=250.0)])

        cands = expand_trellis(default_config, prev, 0.0, 0, group)
        assert len(cands) == 2

        cand_lh = next(c for c in cands if c.left_used)
        assert cand_lh.lock_until_left == pytest.approx(350.0)  # 100 + 250
        assert cand_lh.lock_until_right == pytest.approx(0.0)

        cand_rh = next(c for c in cands if c.right_used)
        assert cand_rh.lock_until_right == pytest.approx(350.0)
        assert cand_rh.lock_until_left == pytest.approx(0.0)

    def test_single_tap_resets_lock_to_zero(self, default_config):
        """Tapping a note should have lock_until set to 0.0, not locked into the future."""
        prev = TrellisNode(
            left_hand_pos=(-0.5, 0.5),
            right_hand_pos=(0.5, 0.5),
            total_score=0.0,
        )
        group = TimedNoteGroup(200.0, [make_tap(200.0, 1, (0.0, 1.0))])

        cands = expand_trellis(default_config, prev, 100.0, 0, group)
        assert len(cands) == 2

        for c in cands:
            if c.left_used:
                assert c.lock_until_left == 0.0
            if c.right_used:
                assert c.lock_until_right == 0.0


# ==============================================================================
# Double Note (Simultaneous / Chords) Expansion Tests
# ==============================================================================

class TestTrellisExpansionDoubleNote:
    def test_simultaneous_notes_uncrossed_vs_crossed(self, default_config):
        """Two simultaneous notes branch into uncrossed and crossed candidate assignments."""
        prev = TrellisNode(
            left_hand_pos=(-0.8, 0.0),
            right_hand_pos=(0.8, 0.0),
            total_score=0.0,
        )
        p0 = (-0.7, 0.7)
        p1 = (0.7, 0.7)
        group = TimedNoteGroup(100.0, [
            make_tap(100.0, 8, p0),
            make_tap(100.0, 2, p1),
        ])

        cands = expand_trellis(default_config, prev, 0.0, 1, group)
        assert len(cands) == 2

        for c in cands:
            assert c.left_used and c.right_used
            assert c.prev_node == 1

        # Uncrossed: LH at p0 (left), RH at p1 (right)
        uncrossed = next(c for c in cands if c.left_hand_pos[0] < c.right_hand_pos[0])
        assert uncrossed.left_hand_pos == pytest.approx(p0)
        assert uncrossed.right_hand_pos == pytest.approx(p1)

        # Crossed: LH at p1 (right), RH at p0 (left)
        crossed = next(c for c in cands if c.left_hand_pos[0] > c.right_hand_pos[0])
        assert crossed.left_hand_pos == pytest.approx(p1)
        assert crossed.right_hand_pos == pytest.approx(p0)

        # Crossed assignment must score strictly higher due to crossover penalty
        assert crossed.total_score > uncrossed.total_score

    def test_double_hold_sets_both_locks(self, default_config):
        """Two simultaneous HOLD notes must update lock_until for both hands correctly."""
        prev = TrellisNode(
            left_hand_pos=(-0.5, 0.0),
            right_hand_pos=(0.5, 0.0),
            total_score=0.0,
        )
        p0 = (-0.5, 0.5)
        p1 = (0.5, 0.5)
        # Note1 duration = 200ms (expires at 300ms)
        # Note2 duration = 400ms (expires at 500ms)
        group = TimedNoteGroup(100.0, [
            make_hold(100.0, 8, p0, duration_ms=200.0),
            make_hold(100.0, 2, p1, duration_ms=400.0),
        ])

        cands = expand_trellis(default_config, prev, 0.0, 0, group)
        assert len(cands) == 2

        # Option 1: LH -> note1 (lock 300), RH -> note2 (lock 500)
        opt1 = next(c for c in cands if c.left_hand_pos == pytest.approx(p0))
        assert opt1.lock_until_left == pytest.approx(300.0)
        assert opt1.lock_until_right == pytest.approx(500.0)

        # Option 2: LH -> note2 (lock 500), RH -> note1 (lock 300)
        opt2 = next(c for c in cands if c.left_hand_pos == pytest.approx(p1))
        assert opt2.lock_until_left == pytest.approx(500.0)
        assert opt2.lock_until_right == pytest.approx(300.0)

    def test_mixed_hold_and_tap_simultaneous(self, default_config):
        """One HOLD note and one TAP note simultaneous sets lock for the holding hand only."""
        prev = TrellisNode(
            left_hand_pos=(-0.5, 0.0),
            right_hand_pos=(0.5, 0.0),
            total_score=0.0,
        )
        p0 = (-0.5, 0.5)
        p1 = (0.5, 0.5)
        # Note1 is HOLD (300ms, expires at 400ms), Note2 is TAP
        group = TimedNoteGroup(100.0, [
            make_hold(100.0, 8, p0, duration_ms=300.0),
            make_tap(100.0, 2, p1),
        ])

        cands = expand_trellis(default_config, prev, 0.0, 0, group)
        assert len(cands) == 2

        # Option 1: LH plays HOLD, RH plays TAP
        opt1 = next(c for c in cands if c.left_hand_pos == pytest.approx(p0))
        assert opt1.lock_until_left == pytest.approx(400.0)
        assert opt1.lock_until_right == pytest.approx(0.0)

        # Option 2: LH plays TAP, RH plays HOLD
        opt2 = next(c for c in cands if c.left_hand_pos == pytest.approx(p1))
        assert opt2.lock_until_left == pytest.approx(0.0)
        assert opt2.lock_until_right == pytest.approx(400.0)


# ==============================================================================
# Pruning & Feasibility Tests
# ==============================================================================

class TestTrellisExpansionPruning:
    def test_prunes_candidate_violating_vmax_single(self, default_config):
        """Single-note candidate requiring speed > v_max must be pruned immediately."""
        prev = TrellisNode(
            left_hand_pos=(-0.9, 0.0),
            right_hand_pos=(0.9, 0.0),
            total_score=0.0,
        )
        group = TimedNoteGroup(5.0, [make_tap(5.0, 3, (0.9, 0.0))])

        cands = expand_trellis(default_config, prev, 0.0, 0, group)

        # LH cannot reach in 5ms; only RH (already at 0.9, 0.0) can hit it
        assert len(cands) == 1
        assert cands[0].right_used
        assert not cands[0].left_used

    def test_prunes_crossed_candidate_on_double_note_exceeding_vmax(self, default_config):
        """In a double note, if the crossed candidate requires moving faster than v_max, only uncrossed survives."""
        # LH is at (-0.8, 0), RH is at (0.8, 0)
        prev = TrellisNode(
            left_hand_pos=(-0.8, 0.0),
            right_hand_pos=(0.8, 0.0),
            total_score=0.0,
        )
        # 5ms dt: Uncrossed move is 0.05 distance (easy), Crossed move is 1.55 distance (v >> v_max)
        p0 = (-0.75, 0.0)
        p1 = (0.75, 0.0)
        group = TimedNoteGroup(5.0, [
            make_tap(5.0, 8, p0),
            make_tap(5.0, 2, p1),
        ])

        cands = expand_trellis(default_config, prev, 0.0, 0, group)

        # Crossed assignment cannot be reached in 5ms; only uncrossed survives
        assert len(cands) == 1
        assert cands[0].left_hand_pos == pytest.approx(p0)
        assert cands[0].right_hand_pos == pytest.approx(p1)

    def test_prunes_single_note_when_hand_is_locked(self, default_config):
        """Candidates attempting to use a hand locked in a hold note must be pruned."""
        prev = TrellisNode(
            left_hand_pos=(-0.5, 0.5),
            right_hand_pos=(0.5, 0.5),
            lock_until_left=500.0,  # Left hand locked until 500ms
            total_score=0.0,
        )
        group = TimedNoteGroup(200.0, [make_tap(200.0, 8, (-0.5, 0.5))])

        cands = expand_trellis(default_config, prev, 100.0, 0, group)

        # LH is locked, so only RH candidate survives
        assert len(cands) == 1
        assert cands[0].right_used
        assert not cands[0].left_used
        assert cands[0].lock_until_left == pytest.approx(500.0)

    def test_double_note_pruning_if_left_hand_locked(self, default_config):
        """Two notes require two hands; if left hand is locked, zero candidates can be created."""
        prev = TrellisNode(
            left_hand_pos=(-0.5, 0.0),
            right_hand_pos=(0.5, 0.0),
            lock_until_left=500.0,  # LH locked until 500ms
            total_score=0.0,
        )
        group = TimedNoteGroup(200.0, [
            make_tap(200.0, 8, (-0.5, 0.5)),
            make_tap(200.0, 2, (0.5, 0.5)),
        ])

        cands = expand_trellis(default_config, prev, 100.0, 0, group)
        assert len(cands) == 0

    def test_double_note_pruning_if_right_hand_locked(self, default_config):
        """Two notes require two hands; if right hand is locked, zero candidates can be created."""
        prev = TrellisNode(
            left_hand_pos=(-0.5, 0.0),
            right_hand_pos=(0.5, 0.0),
            lock_until_right=500.0,  # RH locked until 500ms
            total_score=0.0,
        )
        group = TimedNoteGroup(200.0, [
            make_tap(200.0, 8, (-0.5, 0.5)),
            make_tap(200.0, 2, (0.5, 0.5)),
        ])

        cands = expand_trellis(default_config, prev, 100.0, 0, group)
        assert len(cands) == 0

    def test_all_infeasible_returns_empty_list(self, default_config):
        """If neither hand can validly reach the note, empty list is returned."""
        prev = TrellisNode(
            left_hand_pos=(-0.9, 0.0),
            right_hand_pos=(-0.8, 0.0),
            lock_until_left=500.0,
            lock_until_right=500.0,
            total_score=0.0,
        )
        group = TimedNoteGroup(100.0, [make_tap(100.0, 3, (0.9, 0.0))])

        cands = expand_trellis(default_config, prev, 50.0, 0, group)
        assert len(cands) == 0


# ==============================================================================
# Edge Cases & Special Scenarios
# ==============================================================================

class TestTrellisExpansionEdgeCases:
    def test_empty_note_group_returns_empty_list(self, default_config):
        """An empty note group (0 notes) should yield 0 candidate nodes."""
        prev = TrellisNode(left_hand_pos=(-0.5, 0.0), right_hand_pos=(0.5, 0.0))
        group = TimedNoteGroup(100.0, [])

        cands = expand_trellis(default_config, prev, 0.0, 0, group)
        assert len(cands) == 0

    def test_more_than_two_notes_returns_empty_list(self, default_config):
        """More than 2 notes at the same timestamp cannot be hit by 2 hands, yielding 0 candidates."""
        prev = TrellisNode(left_hand_pos=(-0.5, 0.0), right_hand_pos=(0.5, 0.0))
        group = TimedNoteGroup(100.0, [
            make_tap(100.0, 1, (0.0, 1.0)),
            make_tap(100.0, 3, (1.0, 0.0)),
            make_tap(100.0, 5, (0.0, -1.0)),
        ])

        cands = expand_trellis(default_config, prev, 0.0, 0, group)
        assert len(cands) == 0

    def test_jack_penalty_reflected_in_candidate_score(self, default_config):
        """A rapid consecutive tap with the same hand incurs jack penalty in total_score."""
        lh_pos = (-0.92, 0.38)
        prev = TrellisNode(
            left_hand_pos=lh_pos,
            right_hand_pos=(0.92, 0.38),
            left_used=True,
            total_score=0.0,
        )
        # Note at the exact same location as LH at t = 80ms (dt = 80ms <= 150ms jack_window)
        # 80ms allows RH to reach as well (1.84 / 80 = 0.023 < v_max 0.035)
        group = TimedNoteGroup(80.0, [make_tap(80.0, 8, lh_pos)])

        cands = expand_trellis(default_config, prev, 0.0, 0, group)
        assert len(cands) == 2

        cand_lh = next(c for c in cands if c.left_used)
        # LH did not move, but tapped the same note rapidly -> score is purely jack penalty
        expected_jack_intensity = (default_config.jack_window - 80.0) / default_config.jack_window
        expected_jack_cost = default_config.weight_jack * expected_jack_intensity

        assert cand_lh.total_score == pytest.approx(expected_jack_cost, rel=1e-4)

    def test_in_place_list_mutation_overload(self, default_config):
        """Calling expand_trellis with an existing list populates it in-place."""
        prev = TrellisNode(left_hand_pos=(-0.5, 0.5), right_hand_pos=(0.5, 0.5), total_score=0.0)
        group = TimedNoteGroup(100.0, [make_tap(100.0, 1, (0.0, 1.0))])

        out_list = []
        expand_trellis(default_config, prev, 0.0, 7, group, out_list)

        assert len(out_list) == 2
        for c in out_list:
            assert c.prev_node == 7
