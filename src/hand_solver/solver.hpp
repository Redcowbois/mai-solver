#pragma once

#include <cstdint>
#include <deque>
#include <limits>
#include <utility>
#include <vector>

#include "chart_objects.hpp"

// Note: everything is in miliseconds (ms)

// class for solver settings
class SolverConfig {
 public:
  int beam_width{32};
  float v_max{0.035};  // note: unit is in unit^2/ms
  float weight_velocity{1.0};
  float weight_crossover{4.0};
  float weight_jack{5.0};
  float jack_window{150};  // ms
  std::pair<float, float> left_hand_pos{-0.9239, 0.3827};
  std::pair<float, float> right_hand_pos{0.9239, 0.3827};

  SolverConfig() = default;
};

// enum for hand actions
enum class HandAction { IDLE, TAP, HOLD };

// class for the optimal hand placements
class HandPlacement {
 public:
  double time{0.0};
  std::pair<double, double> right_hand_pos{0.0, 0.0};
  std::pair<double, double> left_hand_pos{0.0, 0.0};
  HandAction right_action{HandAction::IDLE};
  HandAction left_action{HandAction::IDLE};

  HandPlacement() = default;

  HandPlacement(double time_ms, const std::pair<double, double>& rh_pos, const std::pair<double, double>& lh_pos,
                HandAction right_a, HandAction left_a)
      : time(time_ms), right_hand_pos(rh_pos), left_hand_pos(lh_pos), right_action(right_a), left_action(left_a) {}
};

// class for solved kinematic data
class KinematicData {
 public:
  bool is_feasible{false};
  double mean_velocity{0.0};
  double peak_velocity{0.0};
  double crossover_duration_pct{0.0};
  double hand_balance{0.0};
  int jack_count{0};
  int hold_overlap_count{0};
  double peak_rolling_nps{0.0};

  KinematicData() = default;

  KinematicData(double mean_vel, double peak_vel, double crossover_dur, double hand_bal, int jack_c, int h_over_c,
                double peak_roll_nps)
      : mean_velocity(mean_vel),
        peak_velocity(peak_vel),
        crossover_duration_pct(crossover_dur),
        hand_balance(hand_bal),
        jack_count(jack_c),
        hold_overlap_count(h_over_c),
        peak_rolling_nps(peak_roll_nps) {}
};

// class for solver output
class SolverOutput {
 public:
  bool is_feasible;
  std::deque<HandPlacement> hand_placements{};
  KinematicData kinematic_data{};

  SolverOutput() = default;

  SolverOutput(bool is_feas, const std::deque<HandPlacement>& hand_p, const KinematicData& kinematic_d)
      : is_feasible(is_feas), hand_placements(hand_p), kinematic_data(kinematic_d) {}
};

struct TrellisNode {
  std::pair<float, float> left_hand_pos{0.0f, 0.0f};
  std::pair<float, float> right_hand_pos{0.0f, 0.0f};
  float total_score{std::numeric_limits<float>::infinity()};
  float lock_until_left{0.0f};
  float lock_until_right{0.0f};
  int16_t prev_node{-1};
  bool left_used{false};
  bool right_used{false};

  TrellisNode() = default;

  TrellisNode(const std::pair<float, float>& lh_pos, const std::pair<float, float>& rh_pos, float score = 0,
              float lock_l = 0.0f, float lock_r = 0.0f, int16_t prev = -1, bool left_used = false,
              bool right_used = false)
      : left_hand_pos(lh_pos),
        right_hand_pos(rh_pos),
        total_score(score),
        lock_until_left(lock_l),
        lock_until_right(lock_r),
        prev_node(prev),
        left_used(left_used),
        right_used(right_used) {}

  bool operator<(const TrellisNode& other) const noexcept { return total_score < other.total_score; }
};

float transition_cost(const TrellisNode& prev, const TrellisNode& curr, float prev_t, float curr_t,
                      const SolverConfig& config) noexcept;

float crossover_penalty(const TrellisNode& curr, const SolverConfig& config) noexcept;

float jack_penalty(const TrellisNode& prev, const TrellisNode& curr, float prev_t, float curr_t,
                   const SolverConfig& config) noexcept;

void expand_trellis(const SolverConfig& config, const TrellisNode& prev, float prev_t, int16_t prev_idx,
                    const TimedNoteGroup& notes, std::vector<TrellisNode>& nodes_next);

inline std::vector<TrellisNode> expand_trellis(const SolverConfig& config, const TrellisNode& prev, float prev_t,
                                               int16_t prev_idx, const TimedNoteGroup& notes) {
  std::vector<TrellisNode> nodes_next;
  expand_trellis(config, prev, prev_t, prev_idx, notes, nodes_next);
  return nodes_next;
}

KinematicData compute_kinematics(const std::deque<HandPlacement>& solution, const SolverConfig& config);

SolverOutput solver(const SolverConfig& config, const std::vector<TimedNoteGroup>& chart);
