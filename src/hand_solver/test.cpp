#include <iostream>
#include <pybind11/pybind11.h>
using namespace std;

int test(int a) {
    return a + 1;
}

int main() {
    std::cout << "Hello, World!" << std::endl;

    for (int i = 0; i < 10; i++) {
        std::cout << test(i) << "\n";
    }
    
    return 0;
}
