#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <iostream>
#include <string>
#include <vector>
#include <utility>
#include <sstream>
#include <iomanip>

namespace py = pybind11;

//type of note
enum class NoteType {
    TAP = 1,
    HOLD = 2
};

// specific note on the chart
class NoteEvent {
public:
    double time_ms;
    NoteType note_type;
    int button;
    std::vector<std::pair<double, double>> circle_coord;
    bool is_break;
    bool is_ex;
    double hold_duration_ms;

    NoteEvent(double time, NoteType type, int button, const std::vector<std::pair<double, double>> &circle_coord, bool is_break = false, bool is_ex = false, double hold_duration_ms = 0.0): 
        time_ms(time), note_type(type), button(button), circle_coord(circle_coord), is_break(is_break), is_ex(is_ex), hold_duration_ms(hold_duration_ms) {}
};

// all notes at a specific time stamp
class TimedNoteGroup {
public:
    double time_ms;
    std::vector<NoteEvent> notes;

    TimedNoteGroup(double time_ms, const std::vector<NoteEvent> &notes = {}): 
        time_ms(time_ms), notes(notes) {}
    
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

int test(int a) {
    std::cout << a << std::endl;
    return a;
}


PYBIND11_MODULE(chart_objects, m) {
    m.doc() = "Representations for objects in simai chart";
    m.def("test", &test, "Test function", py::arg("a"));

    py::enum_<NoteType>(m, "NoteType")
        .value("TAP", NoteType::TAP)
        .value("HOLD", NoteType::HOLD)
        .export_values();

    py::class_<NoteEvent>(m, "NoteEvent")
        .def(py::init<double, NoteType, int, const std::vector<std::pair<double, double>> &, bool, bool, double>(),
            "Constructor for NoteEvent", 
            py::arg("time_ms"), 
            py::arg("note_type"), 
            py::arg("button"), 
            py::arg("circle_coord"), 
            py::arg("is_break") = false, 
            py::arg("is_ex") = false, 
            py::arg("hold_duration_ms") = 0.0)
        .def_readwrite("time_ms", &NoteEvent::time_ms)
        .def_readwrite("note_type", &NoteEvent::note_type)
        .def_readwrite("button", &NoteEvent::button)
        .def_readwrite("circle_coord", &NoteEvent::circle_coord)
        .def_readwrite("is_break", &NoteEvent::is_break)
        .def_readwrite("is_ex", &NoteEvent::is_ex)
        .def_readwrite("hold_duration_ms", &NoteEvent::hold_duration_ms);

    py::class_<TimedNoteGroup>(m, "TimedNoteGroup")
        .def(py::init<double, const std::vector<NoteEvent> &>(),
            "Constructor for TimedNoteGroup", 
            py::arg("time_ms"), 
            py::arg("notes") = std::vector<NoteEvent>())
        .def_readwrite("time_ms", &TimedNoteGroup::time_ms)
        .def_readwrite("notes", &TimedNoteGroup::notes)
        .def("add_note", &TimedNoteGroup::add_note, "Add a note to the group", py::arg("note"))
        .def("repr", &TimedNoteGroup::repr, "Get a string representation of the note group")
        .def("__repr__", &TimedNoteGroup::repr);
}