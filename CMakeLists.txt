cmake_minimum_required(VERSION 3.18)
project(mai-solver LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)

find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(my_module src/hand_solver/example.cpp)

install(TARGETS my_module DESTINATION .)