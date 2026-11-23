#include "solver.hpp"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <algorithm>
#include <cmath>
#include <deque>
#include <iostream>
#include <limits>
#include <vector>

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

  // calculate movement effort: normalized by physical speed ceiling (v / v_max)^2
  float total_move_sq = left_move_sq + right_move_sq;
  float effort = total_move_sq / max_dist_sq;

  return config.weight_velocity * effort;
}

float crossover_penalty(const TrellisNode& curr, const SolverConfig& config) noexcept {
  // no penalty if left hand is left of right hand
  if (curr.left_hand_pos.first <= curr.right_hand_pos.first) {
    return 0;
  }

  // normalize crossover depth by cabinet diameter (2.0)
  float x_diff = (curr.left_hand_pos.first - curr.right_hand_pos.first) / 2.0f;

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

  // normalize delta t against rapid-stream threshold (jack_window)
  float intensity = std::max(0.0f, 1.0f - dt / config.jack_window);

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
  // lambda to remove redundant code
  auto add_if_valid = [&nodes_next](float cost, TrellisNode& new_node) {
    if (cost < std::numeric_limits<float>::infinity()) {
      new_node.total_score += cost;
      nodes_next.push_back(new_node);
    }
  };

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
      add_if_valid(cost, left_node);
    }

    // right hand node
    if (prev.lock_until_right - EPSILON <= note.time_ms) {
      TrellisNode right_node =
          TrellisNode(prev.left_hand_pos, std::pair{note.circle_coord[0].first, note.circle_coord[0].second},
                      prev.total_score, prev.lock_until_left, lock, prev_idx, false, true);

      float cost = compute_total_cost(prev, right_node, prev_t, note.time_ms, config);
      add_if_valid(cost, right_node);
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
      add_if_valid(cost, left_note1_node);

      TrellisNode right_note1_node = TrellisNode(std::pair{note2.circle_coord[0].first, note2.circle_coord[0].second},
                                                 std::pair{note1.circle_coord[0].first, note1.circle_coord[0].second},
                                                 prev.total_score, lock2, lock1, prev_idx, true, true);
      float cost1 = compute_total_cost(prev, right_note1_node, prev_t, note1.time_ms, config);
      add_if_valid(cost1, right_note1_node);
    }

  } else {
    std::cout << "WARNING: More than 2 notes at " << note_group.time_ms << "ms.\n";
  }
}

SolverOutput solver(const SolverConfig& config, const std::vector<TimedNoteGroup>& chart) {
  if (chart.empty()) {
    return SolverOutput{};  // return empty output
  }

  std::vector<std::pair<float, std::vector<TrellisNode>>> history = {};
  TrellisNode root = TrellisNode(config.left_hand_pos, config.right_hand_pos);
  float prev_t = chart[0].time_ms <= 0.0f ? chart[0].time_ms - 1000.0f : 0.0f;
  history.push_back({prev_t, {root}});

  // forward pass
  for (int i = 0; i < chart.size(); i++) {
    std::vector<TrellisNode> beam = {};

    // expand step
    for (int j = 0; j < history[i].second.size(); j++) {
      expand_trellis(config, history[i].second[j], prev_t, j, chart[i], beam);
    }

    // exit if invalid
    if (beam.empty()) {
      return SolverOutput{false, {}, {}};
    }

    // prune step
    if (beam.size() > config.beam_width) {
      std::partial_sort(beam.begin(), beam.begin() + config.beam_width, beam.end());
      beam.resize(config.beam_width);
    }

    prev_t = chart[i].time_ms;
    history.push_back({chart[i].time_ms, std::move(beam)});
  }

  // backwards pass
  std::deque<HandPlacement> solution = {};
  const auto& last_beam = history.back().second;
  int prev_idx = std::distance(last_beam.begin(), std::min_element(last_beam.begin(), last_beam.end()));

  for (int i = history.size() - 1; i > 0; i--) {
    float time = history[i].first;
    const auto& beam = history[i].second;
    const TrellisNode& optimal_path = beam[prev_idx];
    prev_idx = optimal_path.prev_node;

    auto assign_action = [time](float lock_until, bool used) {
      if (lock_until > time) {
        return HandAction::HOLD;
      } else if (used) {
        return HandAction::TAP;
      } else {
        return HandAction::IDLE;
      }
    };

    HandAction left_action = assign_action(optimal_path.lock_until_left, optimal_path.left_used);
    HandAction right_action = assign_action(optimal_path.lock_until_right, optimal_path.right_used);
    HandPlacement cur_pos =
        HandPlacement(time, optimal_path.right_hand_pos, optimal_path.left_hand_pos, right_action, left_action);
    solution.push_front(cur_pos);
  }

  KinematicData data = compute_kinematics(solution, config);

  return SolverOutput{true, solution, data};
}

KinematicData compute_kinematics(const std::deque<HandPlacement>& solution, const SolverConfig& config) {
  if (solution.empty()) {
    return KinematicData{};
  }

  KinematicData data;
  data.is_feasible = true;

  double total_velocity = 0.0;
  int velocity_samples = 0;
  double peak_vel = 0.0;
  double crossover_duration = 0.0;
  int left_actions = 0;
  int right_actions = 0;
  int jack_count = 0;
  int hold_overlap = 0;

  for (size_t i = 0; i < solution.size(); ++i) {
    const auto& cur = solution[i];

    // hand actions
    if (cur.left_action == HandAction::TAP || cur.left_action == HandAction::HOLD) {
      left_actions++;
    }
    if (cur.right_action == HandAction::TAP || cur.right_action == HandAction::HOLD) {
      right_actions++;
    }

    // simultaneous hold overlap
    if (cur.left_action == HandAction::HOLD && cur.right_action == HandAction::HOLD) {
      hold_overlap++;
    }

    // transition metrics to next placement
    if (i + 1 < solution.size()) {
      const auto& next = solution[i + 1];
      double dt = next.time - cur.time;

      if (dt > 0.0) {
        // crossover duration
        if (cur.left_hand_pos.first > cur.right_hand_pos.first) {
          crossover_duration += dt;
        }

        // velocity
        double l_dx = next.left_hand_pos.first - cur.left_hand_pos.first;
        double l_dy = next.left_hand_pos.second - cur.left_hand_pos.second;
        double l_dist = std::sqrt(l_dx * l_dx + l_dy * l_dy);
        double l_vel = l_dist / dt;

        double r_dx = next.right_hand_pos.first - cur.right_hand_pos.first;
        double r_dy = next.right_hand_pos.second - cur.right_hand_pos.second;
        double r_dist = std::sqrt(r_dx * r_dx + r_dy * r_dy);
        double r_vel = r_dist / dt;

        total_velocity += l_vel + r_vel;
        velocity_samples += 2;
        peak_vel = std::max(peak_vel, std::max(l_vel, r_vel));

        // jack detection
        if (dt <= config.jack_window) {
          if (cur.left_action != HandAction::IDLE && next.left_action != HandAction::IDLE) {
            if ((l_dx * l_dx + l_dy * l_dy) < 1e-4) {
              jack_count++;
            }
          }
          if (cur.right_action != HandAction::IDLE && next.right_action != HandAction::IDLE) {
            if ((r_dx * r_dx + r_dy * r_dy) < 1e-4) {
              jack_count++;
            }
          }
        }
      }
    }
  }

  // mean and peak velocity
  data.mean_velocity = velocity_samples > 0 ? (total_velocity / velocity_samples) : 0.0;
  data.peak_velocity = peak_vel;

  // crossover duration percentage
  double total_duration = solution.back().time - solution.front().time;
  data.crossover_duration_pct = (total_duration > 0.0) ? (crossover_duration / total_duration) * 100.0 : 0.0;

  // hand balance
  int total_actions = left_actions + right_actions;
  data.hand_balance = total_actions > 0 ? (static_cast<double>(left_actions) / total_actions) : 0.5;

  data.jack_count = jack_count;
  data.hold_overlap_count = hold_overlap;

  // peak rolling NPS (1000ms sliding window)
  double peak_nps = 0.0;
  size_t left_win = 0;
  int current_window_notes = 0;
  for (size_t right_win = 0; right_win < solution.size(); ++right_win) {
    int notes_at_r = (solution[right_win].left_action != HandAction::IDLE ? 1 : 0) +
                     (solution[right_win].right_action != HandAction::IDLE ? 1 : 0);
    current_window_notes += notes_at_r;

    while (solution[right_win].time - solution[left_win].time > 1000.0) {
      int notes_at_l = (solution[left_win].left_action != HandAction::IDLE ? 1 : 0) +
                       (solution[left_win].right_action != HandAction::IDLE ? 1 : 0);
      current_window_notes -= notes_at_l;
      left_win++;
    }

    double window_duration = std::max(1.0, (solution[right_win].time - solution[left_win].time) / 1000.0);
    double cur_nps = current_window_notes / window_duration;
    peak_nps = std::max(peak_nps, cur_nps);
  }
  data.peak_rolling_nps = peak_nps;

  return data;
}
