#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <iostream>
#include "chart_objects.h"

namespace py = pybind11;

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