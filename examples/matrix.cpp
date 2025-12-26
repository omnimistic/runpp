#include <iostream>
#include <windows.h>
#include <ctime>
#include <vector>

int main() {
    srand(time(0));
    const int WIDTH = 120;
    const int HEIGHT = 40;
    std::vector<int> columns(WIDTH, 0); // drop start positions

    while (true) {
        for (int i = 0; i < WIDTH; ++i) {
            if (rand() % 100 < 5) columns[i] = 1; // new drop

            if (columns[i] > 0) {
                SetConsoleTextAttribute(GetStdHandle(STD_OUTPUT_HANDLE), 10); // green
                std::cout << char(33 + rand() % 94); // random char
                columns[i]++;
                if (columns[i] > HEIGHT + rand() % 10) columns[i] = 0;
            } else {
                std::cout << " ";
            }
        }
        std::cout << "\n";
        Sleep(40);
    }
    return 0;
}