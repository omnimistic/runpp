import customtkinter as ctk
import tkinter as tk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

app = ctk.CTk()
app.title("Run++")
app.geometry("1000x600")

#Layout
app.grid_columnconfigure(0, weight=3)
app.grid_columnconfigure(1, weight=2)
app.grid_rowconfigure(0, weight=1)

#Code Editor Frame
editor_frame = ctk.CTkFrame(app, corner_radius=10)
editor_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

editor_label = ctk.CTkLabel(editor_frame, text="main.cpp", font=("Consolas", 16))
editor_label.pack(anchor="w", padx=10, pady=(10, 0))

code_editor = tk.Text(
    editor_frame,
    bg="#1e1e1e",
    fg="#dcdcdc",
    insertbackground="white",
    font=("Consolas", 14),
    undo=True
)
code_editor.pack(fill="both", expand=True, padx=10, pady=10)

#Starter template
code_editor.insert("1.0", """#include <iostream>
using namespace std;

int main() {
    cout << "Hello, C++!" << endl;
    return 0;
}
""")

#Right Panel
right_frame = ctk.CTkFrame(app, corner_radius=10)
right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
right_frame.grid_rowconfigure(1, weight=1)

#Run Button
def run_code():
    output_box.configure(state="normal")
    output_box.delete("1.0", "end")
    output_box.insert("end", "Compiling...\n")
    output_box.insert("end", "Running program...\n\n")
    output_box.insert("end", "Hello, C++!\n")
    output_box.configure(state="disabled")

run_button = ctk.CTkButton(
    right_frame,
    text="Run",
    font=("Arial", 16),
    command=run_code
)
run_button.pack(padx=10, pady=10, fill="x")

#Output Console
output_label = ctk.CTkLabel(right_frame, text="Output", font=("Arial", 14))
output_label.pack(anchor="w", padx=10)

output_box = tk.Text(
    right_frame,
    height=15,
    bg="#111111",
    fg="#00ff88",
    font=("Consolas", 13),
    state="disabled"
)
output_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))
app.mainloop()
