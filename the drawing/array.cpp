#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <array.h>
#include <stdexcept>
#include <vector>

using namespace std;
vector<int> foo(pybind11::array_t<int> arr) {
    vector<int> squares_send;
    if (arr.ndim() != 2)
        throw std::runtime_error("Expected 2D array");
    auto buf = arr.unchecked<2>();
    ssize_t rows = buf.shape(0);
    ssize_t cols = buf.shape(1);
    int row_start_square = get_square_origin(rows, cols, buf);
    int col_start_square = 0;
    int row_end_square = row_start_square;
    int col_end_square = 0;
    int col_start_check = col_start_square + 1;
    int row_start_check = row_start_square + 1;
    int col_end_check = col_start_check;
    int row_end_check = row_start_check;
    bool stop_row_check = false;
    while (stop_row_check == false) {
        if (expansion_correct(row_start_check,col_start_check,row_end_check,col_start_check,buf) == true) {
            row_end_square = row_end_square + 1;
            row_end_check = row_end_check + 1;
        }
        else {
            col_end_square = col_end_square + col_end_check;
            row_end_square = row_end_square + row_end_check;
            stop_row_check = true;
        }
    }
    bool stop_col_check = false;
    while (stop_col_check == true) {

    }
    return squares_send;
    }