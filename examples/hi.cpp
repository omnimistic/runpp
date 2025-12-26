#include <iostream>

int main() {
    // Variables to store user information
    char name[50];
    int age;

    // Asking for the user's name
    std::cout << "Enter your first name: ";
    std::cin >> name;

    // Asking for the user's age
    std::cout << "Enter your age: ";
    std::cin >> age;

    // Greeting the user
    std::cout << "\nHello, " << name << "!" << std::endl;
    std::cout << "It's cool that you are " << age << " years old." << std::endl;

    return 0;
}

































