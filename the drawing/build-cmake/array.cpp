#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <array.h>
#include <stdexcept>
#include <vector>
#include <array>

using namespace std;
vector<array<int, 4>> fill_to_squares(pybind11::array_t<int> arr) {
    vector<array<int, 4>> squares_send;
    if (arr.ndim() != 2)
        throw std::runtime_error("Expected 2D array");
    auto buf = arr.unchecked<2>();
    ssize_t rows = buf.shape(0);
    ssize_t cols = buf.shape(1);
    bool isDone = false;
    while (isDone == false) {
        array<int, 4> square;
        array<int, 2> square_start = get_square_origin(rows, cols, buf);
        if (square_start[0] == -1 && square_start[1] == -1) {
            isDone = true;
        }
        if (isDone == false){
            int row_start_square = square_start[0];
            int col_start_square = square_start[1];
            int row_end_square = row_start_square;
            int col_end_square = col_start_square;
            int col_start_check = col_start_square + 1;
            int row_start_check = row_start_square + 1;
            int col_end_check = col_start_check;
            int row_end_check = row_start_check;
            bool stop_row_check = false;
            while (stop_row_check == false) {
                if (expansion_correct(row_start_check,col_start_check,row_end_check,col_start_check,buf) == true) {
                    row_end_check = row_end_check + 1;
                }
                else {
                    col_end_square = col_end_square + col_end_check;
                    row_end_square = row_end_square + row_end_check;
                    stop_row_check = true;
                }
            }
            bool stop_col_check = false;
            while (stop_col_check == false) {
                if (expansion_correct(row_start_check,col_start_check,row_end_check,col_start_check,buf) == true) {
                    col_end_check = col_end_check + 1;
                }
                else {
                    col_end_square = col_end_square + col_end_check;
                    row_end_square = row_end_square + row_end_check;
                    stop_col_check = true;
                }
            }
            square = {row_start_square, col_start_square, row_end_square, col_end_square};
            squares_send.push_back(square);
        }
    }
    return squares_send;
    }

PYBIND11_MODULE(mijnmodule, m) {
    m.def("fill_to_squares", &fill_to_squares, "Voeg twee getallen samen");
}