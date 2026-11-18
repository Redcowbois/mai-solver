#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "chart_objects.hpp"
#include "solver.hpp"

namespace py = pybind11;

PYBIND11_MODULE(mai_solver, m) {
    m.doc() = "Utilities for chart representation and hand position solving";
    
    py::module_ m1 = m.def_submodule("chart_objects", "Representation objects for chart information");
    py::module_ m2 = m.def_submodule("hand_solver", "Tooling for hand position solving");

    // module 1: chart objects
    py::enum_<NoteType>(m1, "NoteType")
        .value("TAP", NoteType::TAP)
        .value("HOLD", NoteType::HOLD)
        .export_values();

    py::class_<NoteEvent>(m1, "NoteEvent")
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

    py::class_<TimedNoteGroup>(m1, "TimedNoteGroup")
        .def(py::init<double, const std::vector<NoteEvent> &>(),
            "Constructor for TimedNoteGroup", 
            py::arg("time_ms"), 
            py::arg("notes") = std::vector<NoteEvent>())
        .def_readwrite("time_ms", &TimedNoteGroup::time_ms)
        .def_readwrite("notes", &TimedNoteGroup::notes)
        .def("add_note", &TimedNoteGroup::add_note, "Add a note to the group", py::arg("note"))
        .def("repr", &TimedNoteGroup::repr, "Get a string representation of the note group")
        .def("__repr__", &TimedNoteGroup::repr);


    
    // module 2: hand solver 
    py::class_<SolverConfig>(m2, "SolverConfig")
        .def(py::init<>(), "Default constructor for SolverConfig")
        .def_readwrite("beam_width", &SolverConfig::beam_width)
        .def_readwrite("v_max", &SolverConfig::v_max)
        .def_readwrite("weight_velocity", &SolverConfig::weight_velocity)
        .def_readwrite("weight_crossover", &SolverConfig::weight_crossover)
        .def_readwrite("weight_jack", &SolverConfig::weight_jack)
        .def_readwrite("jack_window", &SolverConfig::jack_window)
        .def_readwrite("left_hand_pos", &SolverConfig::left_hand_pos)
        .def_readwrite("right_hand_pos", &SolverConfig::right_hand_pos);

    py::enum_<HandAction>(m2, "HandAction")
        .value("IDLE", HandAction::IDLE)
        .value("TAP", HandAction::TAP)
        .value("HOLD", HandAction::HOLD)
        .export_values();

    py::class_<HandPlacement>(m2, "HandPlacement")
        .def(py::init<>(), "Default constructor for HandPlacement")
        .def(py::init<double, 
                      const std::pair<double, double> &, 
                      const std::pair<double, double> &, 
                      HandAction, 
                      HandAction>(),
            "Constructor for HandPlacement",
            py::arg("time_ms"),
            py::arg("rh_pos"),
            py::arg("lh_pos"),
            py::arg("right_a") = HandAction::IDLE,
            py::arg("left_a") = HandAction::IDLE)
        .def_readwrite("time", &HandPlacement::time)
        .def_readwrite("right_hand_pos", &HandPlacement::right_hand_pos)
        .def_readwrite("left_hand_pos", &HandPlacement::left_hand_pos)
        .def_readwrite("right_action", &HandPlacement::right_action)
        .def_readwrite("left_action", &HandPlacement::left_action);

    py::class_<KinematicData>(m2, "KinematicData")
        .def(py::init<>(), "Default constructor for KinematicData")
        .def(py::init<bool, double, double, double, double, int, int, double>(),
            "Parameterized constructor for KinematicData",
            py::arg("is_feas"),
            py::arg("mean_vel"),
            py::arg("peak_vel"),
            py::arg("crossover_dur"),
            py::arg("hand_bal"),
            py::arg("jack_c"),
            py::arg("h_over_c"),
            py::arg("peak_roll_nps"))
        .def_readwrite("is_feasible", &KinematicData::is_feasible)
        .def_readwrite("mean_velocity", &KinematicData::mean_velocity)
        .def_readwrite("peak_velocity", &KinematicData::peak_velocity)
        .def_readwrite("crossover_duration_pct", &KinematicData::crossover_duration_pct)
        .def_readwrite("hand_balance", &KinematicData::hand_balance)
        .def_readwrite("jack_count", &KinematicData::jack_count)
        .def_readwrite("hold_overlap_count", &KinematicData::hold_overlap_count)
        .def_readwrite("peak_rolling_nps", &KinematicData::peak_rolling_nps);

    py::class_<SolverOutput>(m2, "SolverOutput")
        .def(py::init<>(), "Default constructor for SolverOutput")
        .def(py::init<const std::vector<HandPlacement> &, const KinematicData &>(),
            "Parameterized constructor for SolverOutput",
            py::arg("hand_p"),
            py::arg("kinematic_d"))
        .def_readwrite("hand_placements", &SolverOutput::hand_placements)
        .def_readwrite("kinematic_data", &SolverOutput::kinematic_data);
}