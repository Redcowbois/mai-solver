import pytest
from mai_solver.chart_objects import (
    NoteEvent,
    NoteType,
    TimedNoteGroup,
)
from mai_solver.hand_solver import (
    HandAction,
    HandPlacement,
    KinematicData,
    SolverConfig,
    SolverOutput,
    compute_kinematics,
    solve,
    solver,
)

# Standard maimai button positions on the unit circle (R = 1.0)
# Button 2 (right): (0.9239, 0.3827), Button 7 (left): (-0.9239, 0.3827)
POS_BTN2 = (0.9239, 0.3827)
POS_BTN7 = (-0.9239, 0.3827)
POS_BTN1 = (0.3827, 0.9239)
POS_BTN8 = (-0.3827, 0.9239)


@pytest.fixture
def default_config():
    cfg = SolverConfig()
    cfg.left_hand_pos = POS_BTN7
    cfg.right_hand_pos = POS_BTN2
    return cfg


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
# 1. Basic Solver Invocations and Edge Cases
# ==============================================================================

class TestSolverBasics:
    def test_empty_chart_returns_empty_output(self, default_config):
        """Solving an empty chart should return non-crashing empty SolverOutput."""
        res = solve([], default_config)
        assert isinstance(res, SolverOutput)
        assert len(res.hand_placements) == 0

    def test_solve_argument_order_overloads(self, default_config):
        """Verify that solve(chart, config), solve(config, chart), and solve(chart) work."""
        group = TimedNoteGroup(100.0, [make_tap(100.0, 7, POS_BTN7)])
        chart = [group]

        res1 = solve(chart, default_config)
        res2 = solve(default_config, chart)
        res3 = solve(chart)  # default config

        assert isinstance(res1, SolverOutput)
        assert isinstance(res2, SolverOutput)
        assert isinstance(res3, SolverOutput)


# ==============================================================================
# 2. Single Note Routing and Natural Hand Placement
# ==============================================================================

class TestSolverSingleNotes:
    def test_single_tap_left_hand_preferred(self, default_config):
        """A single tap right next to the initial left hand position should be taken by LH."""
        group = TimedNoteGroup(300.0, [make_tap(300.0, 7, POS_BTN7)])
        res = solve([group], default_config)

        assert res.is_feasible is True
        assert len(res.hand_placements) == 1
        placement = res.hand_placements[0]
        assert placement.time == pytest.approx(300.0)
        assert placement.left_action == HandAction.TAP
        assert placement.right_action == HandAction.IDLE

    def test_single_tap_right_hand_preferred(self, default_config):
        """A single tap right next to the initial right hand position should be taken by RH."""
        group = TimedNoteGroup(300.0, [make_tap(300.0, 2, POS_BTN2)])
        res = solve([group], default_config)

        assert res.is_feasible is True
        assert len(res.hand_placements) == 1
        placement = res.hand_placements[0]
        assert placement.time == pytest.approx(300.0)
        assert placement.right_action == HandAction.TAP
        assert placement.left_action == HandAction.IDLE

    def test_chronological_hand_placement_order(self, default_config):
        """Backtracked placements must be ordered chronologically t_0 -> t_N."""
        chart = [
            TimedNoteGroup(100.0, [make_tap(100.0, 7, POS_BTN7)]),
            TimedNoteGroup(300.0, [make_tap(300.0, 2, POS_BTN2)]),
            TimedNoteGroup(500.0, [make_tap(500.0, 7, POS_BTN7)]),
        ]
        res = solve(chart, default_config)

        assert res.is_feasible is True
        times = [p.time for p in res.hand_placements]
        assert times == sorted(times)
        assert times == [100.0, 300.0, 500.0]


# ==============================================================================
# 3. Chords (Simultaneous Notes)
# ==============================================================================

class TestSolverChords:
    def test_two_note_chord_natural_distribution(self, default_config):
        """Simultaneous notes on button 7 (left) and button 2 (right) should assign LH to 7 and RH to 2."""
        chord = TimedNoteGroup(
            200.0,
            [
                make_tap(200.0, 7, POS_BTN7),
                make_tap(200.0, 2, POS_BTN2),
            ],
        )
        res = solve([chord], default_config)

        assert res.is_feasible is True
        assert len(res.hand_placements) == 1
        p = res.hand_placements[0]
        assert p.left_action == HandAction.TAP
        assert p.right_action == HandAction.TAP
        # Avoid crossover: LH x <= RH x
        assert p.left_hand_pos[0] <= p.right_hand_pos[0]


# ==============================================================================
# 4. Hold Notes and Lockout Constraints
# ==============================================================================

class TestSolverHolds:
    def test_hold_note_action(self, default_config):
        """A hold note should register HandAction.HOLD for the active hand."""
        hold_group = TimedNoteGroup(
            150.0,
            [make_hold(150.0, 7, POS_BTN7, duration_ms=400.0)],
        )
        res = solve([hold_group], default_config)

        assert res.is_feasible is True
        assert len(res.hand_placements) == 1
        p = res.hand_placements[0]
        assert p.left_action == HandAction.HOLD

    def test_hold_locks_hand_forcing_other_hand(self, default_config):
        """While LH is holding button 7, an incoming note must be taken by RH."""
        chart = [
            TimedNoteGroup(100.0, [make_hold(100.0, 7, POS_BTN7, duration_ms=500.0)]),
            TimedNoteGroup(200.0, [make_tap(200.0, 8, POS_BTN8)]),
        ]
        res = solve(chart, default_config)

        assert res.is_feasible is True
        assert len(res.hand_placements) == 2
        p2 = res.hand_placements[1]
        # Left hand is still locked in hold, so right hand must take button 8
        assert p2.right_action == HandAction.TAP


# ==============================================================================
# 5. Feasibility and Speed Limits
# ==============================================================================

class TestSolverFeasibility:
    def test_excessive_speed_jump_infeasible(self, default_config):
        """If a note jump requires speed greater than v_max for all valid hand assignments, is_feasible is False."""
        strict_config = SolverConfig()
        strict_config.v_max = 0.00001
        strict_config.left_hand_pos = POS_BTN7
        strict_config.right_hand_pos = POS_BTN2

        # A jump across the screen in 1ms
        chart = [
            TimedNoteGroup(10.0, [make_tap(10.0, 7, POS_BTN7)]),
            TimedNoteGroup(11.0, [make_tap(11.0, 3, (0.9239, -0.3827))]),
        ]
        res = solve(chart, strict_config)
        assert res.is_feasible is False


# ==============================================================================
# 6. KinematicData Metric Computation
# ==============================================================================

class TestComputeKinematics:
    def test_empty_solution_kinematics(self, default_config):
        """Empty placements should yield default KinematicData with is_feasible=False."""
        data = compute_kinematics([], default_config)
        assert isinstance(data, KinematicData)
        assert data.is_feasible is False
        assert data.mean_velocity == 0.0
        assert data.peak_velocity == 0.0

    def test_hand_balance_calculation(self, default_config):
        """One LH tap and one RH tap should result in a 0.5 (50%) hand balance."""
        placements = [
            HandPlacement(100.0, POS_BTN2, POS_BTN7, HandAction.IDLE, HandAction.TAP),
            HandPlacement(200.0, POS_BTN2, POS_BTN7, HandAction.TAP, HandAction.IDLE),
        ]
        data = compute_kinematics(placements, default_config)
        assert data.is_feasible is True
        assert data.hand_balance == pytest.approx(0.5)

    def test_crossover_duration_pct(self, default_config):
        """When LH is to the right of RH for the entire transition, crossover pct is 100%."""
        # Frame 1 at 100ms: LH at x=0.5, RH at x=-0.5 (crossover: x_L > x_R)
        # Frame 2 at 200ms: end of chart
        placements = [
            HandPlacement(100.0, (-0.5, 0.0), (0.5, 0.0), HandAction.TAP, HandAction.TAP),
            HandPlacement(200.0, (-0.5, 0.0), (0.5, 0.0), HandAction.TAP, HandAction.TAP),
        ]
        data = compute_kinematics(placements, default_config)
        assert data.crossover_duration_pct == pytest.approx(100.0)

    def test_jack_count_detection(self, default_config):
        """Rapid same-hand tap on the same button within jack_window should increment jack_count."""
        # RH taps at POS_BTN2 at 100ms and again at 180ms (dt = 80ms <= jack_window of 150ms)
        placements = [
            HandPlacement(100.0, POS_BTN2, POS_BTN7, HandAction.TAP, HandAction.IDLE),
            HandPlacement(180.0, POS_BTN2, POS_BTN7, HandAction.TAP, HandAction.IDLE),
        ]
        data = compute_kinematics(placements, default_config)
        assert data.jack_count == 1

    def test_hold_overlap_detection(self, default_config):
        """Frames where both hands sustain a HOLD simultaneously increment hold_overlap_count."""
        placements = [
            HandPlacement(100.0, POS_BTN2, POS_BTN7, HandAction.HOLD, HandAction.HOLD),
            HandPlacement(200.0, POS_BTN2, POS_BTN7, HandAction.TAP, HandAction.IDLE),
        ]
        data = compute_kinematics(placements, default_config)
        assert data.hold_overlap_count == 1

