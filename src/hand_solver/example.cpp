#include <pybind11/pybind11.h>
#include <string>

namespace py = pybind11;

// 1. A standard C++ function
int add(int a, int b) {
    return a + b;
}

// 2. A standard C++ class
class Pet {
public:
    Pet(const std::string &name) : name_(name) {}

    void setName(const std::string &name) { name_ = name; }
    const std::string &getName() const { return name_; }

    std::string bark() const {
        return name_ + " says woof!";
    }

private:
    std::string name_;
};

PYBIND11_MODULE(my_module, m) {
    m.doc() = "A simple example module made with pybind11";

    // Bind the free function: def("python_name", &cpp_function, "docstring")
    m.def("add", &add, "A function that adds two numbers",
          py::arg("a"), py::arg("b"));

    // Bind the class: py::class_<CppType>(module, "PythonName")
    py::class_<Pet>(m, "Pet")
        .def(py::init<const std::string &>()) // Constructor: Pet(name)
        .def("bark", &Pet::bark)              // Method: pet.bark()
        // def_property binds getter & setter into a Python property (pet.name)
        .def_property("name", &Pet::getName, &Pet::setName);
}