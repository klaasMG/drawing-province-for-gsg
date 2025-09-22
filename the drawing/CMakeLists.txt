cmake_minimum_required(VERSION 3.10)
project(MyArrayProject)

set(CMAKE_CXX_STANDARD 23)

# Vind Python development headers en libraries
find_package(Python3 COMPONENTS Development REQUIRED)

# Zorg dat Python include directories erbij staan
include_directories(${Python3_INCLUDE_DIRS})

# Zorg dat pybind11 headers erbij staan (pas pad aan indien nodig!)
# Als je pybind11 via pip hebt: site-packages/pybind11/include
# Voorbeeld voor Windows: C:/Users/<user>/AppData/Local/Programs/Python/Python311/Lib/site-packages/pybind11/include
include_directories(${Python3_SITEARCH}/site-packages/pybind11/include)
include_directories(build-cmake)

# Maak de Python module als shared library
add_library(mijnmodule SHARED
        build-cmake/array.cpp
        build-cmake/array.h
)

# Link met Python library
target_link_libraries(mijnmodule PRIVATE ${Python3_LIBRARIES})

# Output naam: .pyd voor Windows, .so voor Linux
set_target_properties(mijnmodule PROPERTIES
        PREFIX ""
        SUFFIX ".pyd"
)

