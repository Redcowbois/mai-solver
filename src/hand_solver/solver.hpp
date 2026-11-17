#pragma once

#include <iostream>
#include <string>
#include <vector>
#include <utility>
#include "chart_objects.hpp"

// class for solver settings
class SolverConfig {
    public:
        int beam_width {32};
        double v_max {0.035};  // note: unit is in unit/ms
        double weight_velocity {1.0};
        double weight_crossover {4.0};
        double weight_jack {5.0};
        double jack_window {150.0};
        std::pair<double, double> left_hand_pos {-0.9239, 0.3827};
        std::pair<double, double> right_hand_pos {0.9239, 0.3827};

        SolverConfig() = default;     
};

//enum for hand actions
enum class HandAction {
    RIGHT_IDLE,
    LEFT_IDLE,
    RIGHT_HOLD,
    LEFT_HOLD,
    RIGHT_JACK,
    LEFT_JACK,
};

// class for the optimal hand placements
class HandPlacement {
    public:
        double time {0.0};
        std::pair<double, double> right_hand_pos {0.0, 0.0};
        std::pair<double, double> left_hand_pos {0.0, 0.0};
        HandAction right_action {HandAction::RIGHT_IDLE};
        HandAction left_action {HandAction::LEFT_IDLE};

        HandPlacement() = default;

        HandPlacement(double time_ms, 
                      const std::pair<double, double> &rh_pos, 
                      const std::pair<double, double> &lh_pos)
            : time(time_ms), right_hand_pos(rh_pos), left_hand_pos(lh_pos) {}
};

// class for solved kinematic data
class KinematicData {
    public:
        bool is_feasible {false};
        double mean_velocity {0.0};
        double peak_velocity {0.0};
        double crossover_duration_pct {0.0};
        double hand_balance {0.0};
        int jack_count {0};
        int hold_overlap_count {0};
        double peak_rolling_nps {0.0};

        KinematicData() = default;

        KinematicData(bool is_feas, 
                      double mean_vel, 
                      double peak_vel, 
                      double crossover_dur, 
                      double hand_bal, 
                      int jack_c, 
                      int h_over_c, 
                      double peak_roll_nps)
            : is_feasible(is_feas), 
              mean_velocity(mean_vel), 
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
        std::vector<HandPlacement> hand_placements {};
        KinematicData kinematic_data {};
    
        SolverOutput() = default;

        SolverOutput(const std::vector<HandPlacement> &hand_p, 
                     const KinematicData &kinematic_d)
            : hand_placements(hand_p), kinematic_data(kinematic_d) {}
};