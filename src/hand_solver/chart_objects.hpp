#pragma once

#include <string>
#include <vector>
#include <utility>
#include <sstream>
#include <iomanip>

int test(int a);

// Type of note
enum class NoteType {
    TAP = 1,
    HOLD = 2
};

// Specific note on the chart
class NoteEvent {
public:
    double time_ms;
    NoteType note_type;
    int button;
    std::vector<std::pair<double, double>> circle_coord;
    bool is_break;
    bool is_ex;
    double hold_duration_ms;

    NoteEvent(double time, NoteType type, int button, 
              const std::vector<std::pair<double, double>> &circle_coord, 
              bool is_break = false, bool is_ex = false, double hold_duration_ms = 0.0)
        : time_ms(time), note_type(type), button(button), 
          circle_coord(circle_coord), is_break(is_break), is_ex(is_ex), 
          hold_duration_ms(hold_duration_ms) {}
};

// All notes at a specific timestamp
class TimedNoteGroup {
public:
    double time_ms;
    std::vector<NoteEvent> notes;

    TimedNoteGroup(double time_ms, const std::vector<NoteEvent> &notes = {})
        : time_ms(time_ms), notes(notes) {}

    void add_note(const NoteEvent &note) {
        notes.push_back(note);
    }

    std::string repr() const {
        std::vector<std::string> labels;
        for (const auto &n : notes) {
            std::string s = std::to_string(n.button);
            if (n.is_break) {
                s += "b";
            }
            if (n.is_ex) {
                s += "x";
            }
            if (n.note_type == NoteType::HOLD) {
                std::ostringstream oss;
                oss << std::fixed << std::setprecision(0) << n.hold_duration_ms;
                s += "h(" + oss.str() + "ms)";
            }
            if (!n.circle_coord.empty()) {
                std::ostringstream oss;
                oss << std::fixed << std::setprecision(2) << "(" << n.circle_coord[0].first << ", " << n.circle_coord[0].second << ")";
                s += oss.str();
            }
            labels.push_back(s);
        }

        std::ostringstream out;
        out << std::fixed << std::setprecision(1) << "@" << time_ms << "ms [";
        for (size_t i = 0; i < labels.size(); ++i) {
            if (i > 0) {
                out << "/";
            }
            out << labels[i];
        }
        out << "]";
        return out.str();
    }
};
