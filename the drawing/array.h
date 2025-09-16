//
// Created by klaas on 9/16/2025.
//

#ifndef ARRAY_H
#define ARRAY_H

#include <pybind11/numpy.h>

template<typename Buffer>
int get_square_origin(int rows, int cols, Buffer& buff) {
    int x_get = 0;
    while (x_get < rows - 1) {
        int value = buff(x_get, 1);
        if (value == 1) {
            return value;
        }
        x_get += 1;
    }
    return -1; // not found
}

#endif // ARRAY_H
