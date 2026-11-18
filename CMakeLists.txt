cmake_minimum_required(VERSION 3.18)
project(mai-solver LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)

find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(mai_solver src/hand_solver/bindings.cpp)

install (TARGETS mai_solver DESTINATION .)

