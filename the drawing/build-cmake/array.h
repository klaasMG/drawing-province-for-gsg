//
// Created by klaas on 9/16/2025.
//

#ifndef ARRAY_H
#define ARRAY_H
#include <array>

template<typename Buffer>
std::array<int, 2> get_square_origin(int rows, int cols, Buffer& buff) {
    std::array<int, 2> return_start_square;
    int x_get = 0;
    int y_get = 0;
    bool all_squares_found = false;
    while (all_squares_found == false) {
        if (x_get >= rows) {
            x_get = 0;
            y_get = y_get + 1;
        }
        int value = buff(x_get, y_get);
        if (value == 1) {
            return_start_square[0] = x_get;
            return_start_square[1] = y_get;
            return return_start_square;
        }
        x_get += 1;
        if (x_get >= cols) {
            all_squares_found = true;
        }
    }
    return_start_square[0] = -1;
    return_start_square[1] = -1;
    return return_start_square; // not found
}

template<typename Buffer>
bool expansion_correct(int start_row, int start_col, int end_row, int end_col, Buffer& buff) {
    int row_get = start_row;
    int col_get = start_col;
    int row_check_expand = 0;
    int col_check_expand = 0;
    if (start_row != end_row) {
        row_check_expand = 1;
    }
    if (start_col != end_col) {
        col_check_expand = 1;
    }
    bool expansion_correct = false;
    while (expansion_correct == false) {
        int value = buff(row_get, col_get);
        if (value == 1) {
            expansion_correct = false;
        } else {
            expansion_correct = true;
        }
        if (row_get == end_row && col_get == end_col) {
            break;
        }
        row_get += row_check_expand;
        col_get += col_check_expand;
    }
    return expansion_correct;
}

#endif // ARRAY_H
