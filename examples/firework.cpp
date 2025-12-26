#include <iostream>
#include <windows.h>
#include <cmath>
#include <ctime>

int main() {
    srand(time(0));
    const int W = 80, H = 25;

    while (true) {
        system("cls");

        int cx = W / 2 + (rand() % 20 - 10);
        int cy = H / 2 + (rand() % 10 - 5);
        int color = 1 + rand() % 15;

        for (int r = 1; r < 15; ++r) {
            system("cls");
            for (int y = 0; y < H; ++y) {
                for (int x = 0; x < W; ++x) {
                    double dist = hypot(x - cx, y - cy);
                    if (fabs(dist - r) < 1.5) {
                        SetConsoleTextAttribute(GetStdHandle(STD_OUTPUT_HANDLE), color);
                        std::cout << "*";
                    } else {
                        std::cout << " ";
                    }
                }
                std::cout << "\n";
            }
            Sleep(50);
        }
        Sleep(800);
    }
    return 0;
}