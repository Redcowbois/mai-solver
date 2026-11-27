cmake_minimum_required(VERSION 3.18)
project(mai-solver LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# If pybind11 is not found, check the local virtual environment
if(NOT pybind11_FOUND AND NOT DEFINED pybind11_DIR)
    list(APPEND CMAKE_PREFIX_PATH
        "${CMAKE_CURRENT_SOURCE_DIR}/.venv/Lib/site-packages/pybind11/share/cmake/pybind11"
        "${CMAKE_CURRENT_SOURCE_DIR}/.venv/lib/site-packages/pybind11/share/cmake/pybind11"
    )
endif()

find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(mai_solver
    src/hand_solver/bindings.cpp
    src/hand_solver/solver.cpp
)

target_include_directories(mai_solver PRIVATE src/hand_solver)

install(TARGETS mai_solver DESTINATION .)
