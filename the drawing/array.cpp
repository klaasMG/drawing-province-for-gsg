#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <array.h>
#include <stdexcept>

using namespace std;
void foo(pybind11::array_t<int> arr) {
    if (arr.ndim() != 2)
        throw std::runtime_error("Expected 2D array");
    auto buf = arr.unchecked<2>();
    ssize_t rows = buf.shape(0);
    ssize_t cols = buf.shape(1);
    }