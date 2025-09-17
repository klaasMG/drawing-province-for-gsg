//
// Created by klaas on 9/16/2025.
//

#ifndef ARRAY_H
#define ARRAY_H

template<typename Buffer>
int get_square_origin(int rows, int cols, Buffer& buff) {
    int x_get = 0;
    while (x_get < rows - 1) {
        int value = buff(x_get, 1);
        if (value == 1) {
            return x_get;
        }
        x_get += 1;
    }
    return -1; // not found
}

template<typename Buffer>
bool expansion_correct(int start_row, int start_col, int end_row, int end_col, Buffer& buff) {
    int row_get = start_row;
    int col_get = start_col;
    int row_check_expand = 0;
    int col_check_expand = 0;
    if (start_row != end_row) {
        int row_check_expand = 1;
    }
    if (start_col != end_col) {
        int col_check_expand = 1;
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
