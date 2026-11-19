import math
import pytest
from mai_solver.hand_solver import (
    SolverConfig,
    TrellisNode,
    transition_cost,
    crossover_penalty,
    jack_penalty,
)


@pytest.fixture
def default_config():
    return SolverConfig()


# ==============================================================================
# crossover_penalty tests
# ==============================================================================

class TestCrossoverPenalty:
    def test_no_crossover_normal_hands(self, default_config):
        """Left hand strictly left of right hand should yield zero penalty."""
        node = TrellisNode(left_hand_pos=(-0.5, 0.2), right_hand_pos=(0.5, 0.2))
        cost = crossover_penalty(node, default_config)
        assert cost == 0.0

    def test_same_horizontal_position_no_penalty(self, default_config):
        """Both hands sharing the exact same horizontal coordinate should yield zero penalty."""
        node = TrellisNode(left_hand_pos=(0.0, 0.5), right_hand_pos=(0.0, -0.5))
        cost = crossover_penalty(node, default_config)
        assert cost == 0.0

    def test_crossover_quadratic_scaling(self, default_config):
        """When left hand is to the right of right hand, penalty is weight_crossover * (x_diff)^2."""
        # x_left = 0.4, x_right = 0.1 -> x_diff = 0.3
        node = TrellisNode(left_hand_pos=(0.4, 0.0), right_hand_pos=(0.1, 0.0))
        cost = crossover_penalty(node, default_config)

        expected = default_config.weight_crossover * (0.3 ** 2)
        assert cost == pytest.approx(expected, rel=1e-5)

    def test_crossover_ignores_vertical_distance(self, default_config):
        """Penalty should depend only on horizontal crossover, independent of y-coordinate."""
        node1 = TrellisNode(left_hand_pos=(0.3, 0.8), right_hand_pos=(-0.1, 0.8))
        node2 = TrellisNode(left_hand_pos=(0.3, -0.9), right_hand_pos=(-0.1, 0.7))

        cost1 = crossover_penalty(node1, default_config)
        cost2 = crossover_penalty(node2, default_config)

        assert cost1 == pytest.approx(cost2, rel=1e-5)
        assert cost1 > 0.0

    def test_weight_crossover_scaling(self):
        """Custom weight_crossover scales the resulting penalty proportionally."""
        cfg1 = SolverConfig()
        cfg1.weight_crossover = 2.0

        cfg2 = SolverConfig()
        cfg2.weight_crossover = 6.0

        node = TrellisNode(left_hand_pos=(0.5, 0.0), right_hand_pos=(0.0, 0.0))
        cost1 = crossover_penalty(node, cfg1)
        cost2 = crossover_penalty(node, cfg2)

        assert cost2 == pytest.approx(cost1 * 3.0, rel=1e-5)


# ==============================================================================
# jack_penalty tests
# ==============================================================================

class TestJackPenalty:
    def test_left_hand_single_jack(self, default_config):
        """Same left hand tapping the exact same position within jack_window should incur penalty."""
        pos = (-0.92, 0.38)
        prev = TrellisNode(left_hand_pos=pos, right_hand_pos=(0.92, 0.38), left_used=True)
        curr = TrellisNode(left_hand_pos=pos, right_hand_pos=(0.92, 0.38), left_used=True)

        prev_t = 0.0
        curr_t = 50.0  # dt = 50ms <= 150ms jack_window
        cost = jack_penalty(prev, curr, prev_t, curr_t, default_config)

        dt = curr_t - prev_t
        expected_intensity = (default_config.jack_window - dt) / default_config.jack_window
        expected_cost = default_config.weight_jack * 1 * expected_intensity

        assert cost == pytest.approx(expected_cost, rel=1e-5)

    def test_right_hand_single_jack(self, default_config):
        """Same right hand tapping the exact same position within jack_window should incur penalty."""
        pos = (0.92, 0.38)
        prev = TrellisNode(left_hand_pos=(-0.92, 0.38), right_hand_pos=pos, right_used=True)
        curr = TrellisNode(left_hand_pos=(-0.92, 0.38), right_hand_pos=pos, right_used=True)

        prev_t = 100.0
        curr_t = 160.0  # dt = 60ms <= 150ms
        cost = jack_penalty(prev, curr, prev_t, curr_t, default_config)

        dt = curr_t - prev_t
        expected_intensity = (default_config.jack_window - dt) / default_config.jack_window
        expected_cost = default_config.weight_jack * 1 * expected_intensity

        assert cost == pytest.approx(expected_cost, rel=1e-5)

    def test_double_jack_both_hands(self, default_config):
        """Both hands repeating taps at their respective positions should incur 2x jack count."""
        lh_pos = (-0.5, 0.5)
        rh_pos = (0.5, 0.5)
        prev = TrellisNode(left_hand_pos=lh_pos, right_hand_pos=rh_pos, left_used=True, right_used=True)
        curr = TrellisNode(left_hand_pos=lh_pos, right_hand_pos=rh_pos, left_used=True, right_used=True)

        cost = jack_penalty(prev, curr, 0.0, 75.0, default_config)

        dt = 75.0
        expected_intensity = (default_config.jack_window - dt) / default_config.jack_window
        expected_cost = default_config.weight_jack * 2 * expected_intensity

        assert cost == pytest.approx(expected_cost, rel=1e-5)

    def test_outside_jack_window_zero_penalty(self, default_config):
        """Taps further apart than jack_window should incur zero penalty."""
        pos = (-0.92, 0.38)
        prev = TrellisNode(left_hand_pos=pos, right_hand_pos=(0.92, 0.38), left_used=True)
        curr = TrellisNode(left_hand_pos=pos, right_hand_pos=(0.92, 0.38), left_used=True)

        # dt = 200ms > 150ms
        cost = jack_penalty(prev, curr, 0.0, 200.0, default_config)
        assert cost == 0.0

    def test_different_positions_not_a_jack(self, default_config):
        """Moving to a different button/position within jack_window is a stream, not a jack."""
        prev = TrellisNode(left_hand_pos=(-0.92, 0.38), right_hand_pos=(0.92, 0.38), left_used=True)
        curr = TrellisNode(left_hand_pos=(-0.38, 0.92), right_hand_pos=(0.92, 0.38), left_used=True)

        cost = jack_penalty(prev, curr, 0.0, 50.0, default_config)
        assert cost == 0.0

    def test_idle_hands_not_penalized(self, default_config):
        """An idle hand sitting in the same spot should never be counted as a jack."""
        pos = (-0.92, 0.38)
        # Neither used
        prev = TrellisNode(left_hand_pos=pos, right_hand_pos=(0.92, 0.38), left_used=False)
        curr = TrellisNode(left_hand_pos=pos, right_hand_pos=(0.92, 0.38), left_used=False)
        assert jack_penalty(prev, curr, 0.0, 50.0, default_config) == 0.0

        # Used in prev, not in curr
        prev.left_used = True
        curr.left_used = False
        assert jack_penalty(prev, curr, 0.0, 50.0, default_config) == 0.0

    def test_non_positive_dt_zero_penalty(self, default_config):
        """Non-positive dt (dt <= 0) should return 0."""
        pos = (-0.92, 0.38)
        prev = TrellisNode(left_hand_pos=pos, right_hand_pos=(0.92, 0.38), left_used=True)
        curr = TrellisNode(left_hand_pos=pos, right_hand_pos=(0.92, 0.38), left_used=True)

        assert jack_penalty(prev, curr, 100.0, 100.0, default_config) == 0.0
        assert jack_penalty(prev, curr, 100.0, 50.0, default_config) == 0.0


# ==============================================================================
# transition_cost tests
# ==============================================================================

class TestTransitionCost:
    def test_stationary_hands_zero_effort(self, default_config):
        """If hands do not move, movement effort should be zero."""
        node = TrellisNode(left_hand_pos=(-0.5, 0.0), right_hand_pos=(0.5, 0.0))
        cost = transition_cost(node, node, 0.0, 100.0, default_config)
        assert cost == 0.0

    def test_normal_movement_cost(self, default_config):
        """Normal movement below v_max computes weight_velocity * (d_left^2 + d_right^2) / dt."""
        prev = TrellisNode(left_hand_pos=(-0.5, 0.0), right_hand_pos=(0.5, 0.0))
        curr = TrellisNode(left_hand_pos=(-0.4, 0.0), right_hand_pos=(0.5, 0.1))

        # dx_l = 0.1, dy_l = 0.0 -> dist_sq_l = 0.01
        # dx_r = 0.0, dy_r = 0.1 -> dist_sq_r = 0.01
        # dt = 100.0 -> effort = (0.01 + 0.01) / 100.0 = 0.0002
        prev_t = 0.0
        curr_t = 100.0
        cost = transition_cost(prev, curr, prev_t, curr_t, default_config)

        expected = default_config.weight_velocity * (0.02 / 100.0)
        assert cost == pytest.approx(expected, rel=1e-5)

    def test_velocity_limit_left_hand(self, default_config):
        """Moving left hand faster than v_max returns infinity."""
        prev = TrellisNode(left_hand_pos=(-0.9, 0.0), right_hand_pos=(0.5, 0.0))
        curr = TrellisNode(left_hand_pos=(0.9, 0.0), right_hand_pos=(0.5, 0.0))

        # Distance = 1.8 in 10ms -> velocity = 0.18 >> v_max (0.035)
        cost = transition_cost(prev, curr, 0.0, 10.0, default_config)
        assert math.isinf(cost)

    def test_velocity_limit_right_hand(self, default_config):
        """Moving right hand faster than v_max returns infinity."""
        prev = TrellisNode(left_hand_pos=(-0.5, 0.0), right_hand_pos=(0.0, 0.0))
        curr = TrellisNode(left_hand_pos=(-0.5, 0.0), right_hand_pos=(1.0, 0.0))

        # Distance = 1.0 in 10ms -> velocity = 0.1 >> v_max (0.035)
        cost = transition_cost(prev, curr, 0.0, 10.0, default_config)
        assert math.isinf(cost)

    def test_hold_lock_left_hand_violation(self, default_config):
        """Using left hand while it is still locked in a hold note returns infinity."""
        prev = TrellisNode(left_hand_pos=(-0.5, 0.0), right_hand_pos=(0.5, 0.0), lock_until_left=200.0)
        curr = TrellisNode(left_hand_pos=(-0.5, 0.0), right_hand_pos=(0.5, 0.0), left_used=True)

        # curr_t = 100ms < lock_until_left (200ms) - EPSILON
        cost = transition_cost(prev, curr, 0.0, 100.0, default_config)
        assert math.isinf(cost)

    def test_hold_lock_right_hand_violation(self, default_config):
        """Using right hand while it is still locked in a hold note returns infinity."""
        prev = TrellisNode(left_hand_pos=(-0.5, 0.0), right_hand_pos=(0.5, 0.0), lock_until_right=200.0)
        curr = TrellisNode(left_hand_pos=(-0.5, 0.0), right_hand_pos=(0.5, 0.0), right_used=True)

        # curr_t = 100ms < lock_until_right (200ms) - EPSILON
        cost = transition_cost(prev, curr, 0.0, 100.0, default_config)
        assert math.isinf(cost)

    def test_hold_lock_expired_allows_action(self, default_config):
        """Once lock timestamp passes, the hand can be used without infinity penalty."""
        prev = TrellisNode(left_hand_pos=(-0.5, 0.0), right_hand_pos=(0.5, 0.0), lock_until_left=200.0)
        curr = TrellisNode(left_hand_pos=(-0.5, 0.0), right_hand_pos=(0.5, 0.0), left_used=True)

        # curr_t = 250ms > lock_until_left (200ms)
        cost = transition_cost(prev, curr, 200.0, 250.0, default_config)
        assert not math.isinf(cost)
        assert cost == 0.0

    def test_out_of_order_negative_or_zero_dt(self, default_config):
        """Out of order or simultaneous timestamps (dt <= 0) return infinity."""
        node = TrellisNode(left_hand_pos=(-0.5, 0.0), right_hand_pos=(0.5, 0.0))

        assert math.isinf(transition_cost(node, node, 100.0, 100.0, default_config))
        assert math.isinf(transition_cost(node, node, 100.0, 50.0, default_config))
