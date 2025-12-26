#include <iostream>
#include <windows.h>
#include <conio.h>
#include <vector>
#include <deque>
#include <ctime>

#define WIDTH 80
#define HEIGHT 25

int main() {
    srand(time(0));
    std::deque<std::pair<int, int>> snake = {{WIDTH/2, HEIGHT/2}};
    int dx = 1, dy = 0;
    std::pair<int, int> food = {rand() % WIDTH, rand() % HEIGHT};
    int score = 0;

    while (true) {
        if (_kbhit()) {
            char ch = _getch();
            if (ch == 'w' && dy != 1) { dx = 0; dy = -1; }
            if (ch == 's' && dy != -1) { dx = 0; dy = 1; }
            if (ch == 'a' && dx != 1) { dx = -1; dy = 0; }
            if (ch == 'd' && dx != -1) { dx = 1; dy = 0; }
            if (ch == 27) break; // ESC
        }

        // Move snake
        auto head = snake.front();
        head.first += dx; head.second += dy;

        // Wall wrap-around
        head.first = (head.first + WIDTH) % WIDTH;
        head.second = (head.second + HEIGHT) % HEIGHT;

        // Check self-collision
        bool dead = false;
        for (auto& seg : snake) {
            if (seg == head) { dead = true; break; }
        }
        if (dead) {
            std::cout << "\nGame Over! Score: " << score << "\n";
            break;
        }

        snake.push_front(head);

        // Eat food
        if (head == food) {
            score += 10;
            food = {rand() % WIDTH, rand() % HEIGHT};
        } else {
            snake.pop_back();
        }

        // Clear screen
        std::cout << "\033[2J\033[H";  // Clear screen + move cursor to top

        // Draw
        for (int y = 0; y < HEIGHT; ++y) {
            for (int x = 0; x < WIDTH; ++x) {
                bool is_snake = false;
                for (auto& seg : snake) {
                    if (seg.first == x && seg.second == y) {
                        is_snake = true;
                        break;
                    }
                }
                if (is_snake) {
                    SetConsoleTextAttribute(GetStdHandle(STD_OUTPUT_HANDLE), 10 + (x + y) % 6);
                    std::cout << "█";
                } else if (x == food.first && y == food.second) {
                    SetConsoleTextAttribute(GetStdHandle(STD_OUTPUT_HANDLE), 14);
                    std::cout << "*";
                } else {
                    std::cout << " ";
                }
            }
            std::cout << "\n";
        }
        SetConsoleTextAttribute(GetStdHandle(STD_OUTPUT_HANDLE), 7);
        std::cout << "Score: " << score << "   Use WASD - ESC to quit\n";

        Sleep(80);
    }
    return 0;
}