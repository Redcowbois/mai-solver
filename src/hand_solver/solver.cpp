#include "solver.hpp"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <cmath>
#include <limits>

#include "chart_objects.hpp"

const float EPSILON = 0.5;

float transition_cost(const TrellisNode& prev,
                      const TrellisNode& curr,
                      float prev_t,
                      float curr_t,
                      const SolverConfig& config) noexcept {
  float dt = curr_t - prev_t;

  if (dt <= 0) {
    // guard against out of order
    return std::numeric_limits<float>::infinity();
  } else if (curr.was_left_used and prev.lock_until_left - EPSILON > curr_t) {
    // invalid state: using left hand while its still locked
    return std::numeric_limits<float>::infinity();
  } else if (curr.was_right_used and prev.lock_until_right - EPSILON > curr_t) {
    // invalid state: using right hand while its still locked
    return std::numeric_limits<float>::infinity();
  }

  float left_dx = curr.left_hand_pos.first - prev.left_hand_pos.first;
  float left_dy = curr.left_hand_pos.second - prev.left_hand_pos.second;
  float right_dx = curr.right_hand_pos.first - prev.right_hand_pos.first;
  float right_dy = curr.right_hand_pos.second - prev.right_hand_pos.second;
  float left_move_sq = left_dx * left_dx + left_dy * left_dy;
  float right_move_sq = right_dx * right_dx + right_dy * right_dy;
  float max_dist_sq = config.v_max * config.v_max * dt * dt;

  if (left_move_sq > max_dist_sq) {
    // left hand too fast
    return std::numeric_limits<float>::infinity();
  } else if (right_move_sq > max_dist_sq) {
    // right hand too fast
    return std::numeric_limits<float>::infinity();
  }

  // calculate movement effort
  float total_move_sq = left_move_sq + right_move_sq;
  float effort = total_move_sq / dt;

  return config.weight_velocity * effort;
}

float crossover_penalty(const TrellisNode& curr, const SolverConfig& config) noexcept {
  // no penalty if left hand is left of right hand
  if (curr.left_hand_pos.first <= curr.right_hand_pos.first) {
    return 0;
  }

  float x_diff = curr.left_hand_pos.first - curr.right_hand_pos.first;

  return config.weight_crossover * x_diff * x_diff;
}

float jack_penalty(const TrellisNode& prev,
                   const TrellisNode& curr,
                   float prev_t,
                   float curr_t,
                   const SolverConfig& config) noexcept {
  float dt = curr_t - prev_t;
  if (dt <= 0) {
    return 0;
  }
  int jack = 0;

  float l_dx = curr.left_hand_pos.first - prev.left_hand_pos.first;
  float l_dy = curr.left_hand_pos.second - prev.left_hand_pos.second;
  bool is_same_pos_left = (l_dx * l_dx + l_dy * l_dy) < 1e-4f;
  if (is_same_pos_left && prev.was_left_used && curr.was_left_used && dt <= config.jack_window) {
    jack += 1;
  }

  float r_dx = curr.right_hand_pos.first - prev.right_hand_pos.first;
  float r_dy = curr.right_hand_pos.second - prev.right_hand_pos.second;
  bool is_same_pos_right = (r_dx * r_dx + r_dy * r_dy) < 1e-4f;
  if (is_same_pos_right && prev.was_right_used && curr.was_right_used && dt <= config.jack_window) {
    jack += 1;
  }

  float intensity = (config.jack_window - dt) / config.jack_window;

  return config.weight_jack * jack * intensity;
}