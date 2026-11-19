#include "solver.hpp"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <iostream>
#include <limits>

#include "chart_objects.hpp"

const float EPSILON = 0.5;

float transition_cost(const TrellisNode& prev, const TrellisNode& curr, float prev_t, float curr_t,
                      const SolverConfig& config) noexcept {
  float dt = curr_t - prev_t;

  if (dt <= 0) {
    // guard against out of order
    return std::numeric_limits<float>::infinity();
  } else if (curr.left_used and prev.lock_until_left - EPSILON > curr_t) {
    // invalid state: using left hand while its still locked
    return std::numeric_limits<float>::infinity();
  } else if (curr.right_used and prev.lock_until_right - EPSILON > curr_t) {
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

float jack_penalty(const TrellisNode& prev, const TrellisNode& curr, float prev_t, float curr_t,
                   const SolverConfig& config) noexcept {
  float dt = curr_t - prev_t;
  if (dt <= 0) {
    return 0;
  }
  int jack = 0;

  float l_dx = curr.left_hand_pos.first - prev.left_hand_pos.first;
  float l_dy = curr.left_hand_pos.second - prev.left_hand_pos.second;
  bool is_same_pos_left = (l_dx * l_dx + l_dy * l_dy) < 1e-4f;
  if (is_same_pos_left && prev.left_used && curr.left_used && dt <= config.jack_window) {
    jack += 1;
  }

  float r_dx = curr.right_hand_pos.first - prev.right_hand_pos.first;
  float r_dy = curr.right_hand_pos.second - prev.right_hand_pos.second;
  bool is_same_pos_right = (r_dx * r_dx + r_dy * r_dy) < 1e-4f;
  if (is_same_pos_right && prev.right_used && curr.right_used && dt <= config.jack_window) {
    jack += 1;
  }

  float intensity = (config.jack_window - dt) / config.jack_window;

  return config.weight_jack * jack * intensity;
}

float compute_total_cost(const TrellisNode& prev, const TrellisNode& curr, float prev_t, float curr_t,
                         const SolverConfig& config) noexcept {
  float transition_c = transition_cost(prev, curr, prev_t, curr_t, config);
  float crossover_c = crossover_penalty(curr, config);
  float jack_c = jack_penalty(prev, curr, prev_t, curr_t, config);

  return transition_c + crossover_c + jack_c;
}

void expand_trellis(const SolverConfig& config, const TrellisNode& prev, float prev_t, int16_t prev_idx,
                    const TimedNoteGroup& note_group, std::vector<TrellisNode>& nodes_next) {
  // assume that there are at most 2 objects in TimeNoteGroup
  if (note_group.notes.size() == 0) {
    return;
  } else if (note_group.notes.size() == 1) {
    const NoteEvent& note = note_group.notes[0];
    float lock = note.note_type == NoteType::HOLD ? note.time_ms + note.hold_duration_ms : 0.0f;

    // left hand node
    if (prev.lock_until_left - EPSILON <= note.time_ms) {
      TrellisNode left_node =
          TrellisNode(std::pair{note.circle_coord[0].first, note.circle_coord[0].second}, prev.right_hand_pos,
                      prev.total_score, lock, prev.lock_until_right, prev_idx, true, false);

      float cost = compute_total_cost(prev, left_node, prev_t, note.time_ms, config);
      if (cost < std::numeric_limits<float>::infinity()) {
        left_node.total_score += cost;
        nodes_next.push_back(left_node);
      }
    }

    // right hand node
    if (prev.lock_until_right - EPSILON <= note.time_ms) {
      TrellisNode right_node =
          TrellisNode(prev.left_hand_pos, std::pair{note.circle_coord[0].first, note.circle_coord[0].second},
                      prev.total_score, prev.lock_until_left, lock, prev_idx, false, true);

      float cost = compute_total_cost(prev, right_node, prev_t, note.time_ms, config);
      if (cost < std::numeric_limits<float>::infinity()) {
        right_node.total_score += cost;
        nodes_next.push_back(right_node);
      }
    }
  } else if (note_group.notes.size() == 2) {
    const NoteEvent& note1 = note_group.notes[0];
    float lock1 = note1.note_type == NoteType::HOLD ? note1.time_ms + note1.hold_duration_ms : 0.0f;
    const NoteEvent& note2 = note_group.notes[1];
    float lock2 = note2.note_type == NoteType::HOLD ? note2.time_ms + note2.hold_duration_ms : 0.0f;

    // if left and right aren't locked
    if (prev.lock_until_right - EPSILON <= note1.time_ms && prev.lock_until_left - EPSILON <= note1.time_ms) {
      TrellisNode left_note1_node = TrellisNode(std::pair{note1.circle_coord[0].first, note1.circle_coord[0].second},
                                                std::pair{note2.circle_coord[0].first, note2.circle_coord[0].second},
                                                prev.total_score, lock1, lock2, prev_idx, true, true);

      float cost = compute_total_cost(prev, left_note1_node, prev_t, note1.time_ms, config);
      if (cost < std::numeric_limits<float>::infinity()) {
        left_note1_node.total_score += cost;
        nodes_next.push_back(left_note1_node);
      }

      TrellisNode right_note1_node = TrellisNode(std::pair{note2.circle_coord[0].first, note2.circle_coord[0].second},
                                                 std::pair{note1.circle_coord[0].first, note1.circle_coord[0].second},
                                                 prev.total_score, lock2, lock1, prev_idx, true, true);
      float cost1 = compute_total_cost(prev, right_note1_node, prev_t, note1.time_ms, config);
      if (cost1 < std::numeric_limits<float>::infinity()) {
        right_note1_node.total_score += cost1;
        nodes_next.push_back(right_note1_node);
      }
    }

  } else {
    std::cout << "WARNING: More than 2 notes at " << note_group.time_ms << "ms.\n";
  }
}