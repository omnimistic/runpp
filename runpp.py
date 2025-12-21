import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import re
import json
import os

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

app = ctk.CTk()
app.title("Run++")
app.geometry("1000x600")

# Syntax loading variables (global)
SYNTAX_DIR = "Hsyntax"
SYNTAX_FILE = os.path.join(SYNTAX_DIR, "default.json")
theme = {}

# Main Split View
paned = tk.PanedWindow(
    app,
    orient=tk.HORIZONTAL,
    sashwidth=6,
    bg="#1a1a1a",
    bd=0,
    relief="flat"
)
paned.pack(fill="both", expand=True)
paned.configure(cursor="sb_h_double_arrow")

# Left Panel
editor_frame = ctk.CTkFrame(paned, corner_radius=10)
editor_frame.grid_rowconfigure(1, weight=1)
editor_frame.grid_columnconfigure(0, weight=1)

paned.add(editor_frame, minsize=350)

# Tab Bar
tab_bar = ctk.CTkFrame(editor_frame, height=35, corner_radius=0)
tab_bar.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 0))
tab_bar.grid_columnconfigure(999, weight=1)  # spacer

tabs = {}
active_tab = None
previous_active_tab = None
tab_counter = 1

def switch_tab(name):
    global active_tab, previous_active_tab
    if active_tab is not None and active_tab != name:
        previous_active_tab = active_tab
    active_tab = name

    for tab_name, tab_data in tabs.items():
        is_active = (tab_name == name)
        tab_data["button"].configure(
            fg_color="#2b2b2b" if is_active else "#1f1f1f"
        )
        if is_active:
            tab_data["close"].grid(row=0, column=1, padx=(5, 0))
        else:
            tab_data["close"].grid_forget()

    code_editor.delete("1.0", "end")
    code_editor.insert("1.0", tabs[name]["content"])
    highlight_code()

def close_tab(name):
    global active_tab
    tab = tabs.get(name)
    if not tab:
        return False

    if tab["content"] != tab["saved_content"]:
        filename = tab["button"].cget("text").rstrip("*")
        response = messagebox.askyesnocancel(
            "Unsaved Changes",
            f"Save changes to {filename} before closing?"
        )
        if response is None:
            return False
        if response:
            if not save_current_tab():
                return False

    tab["frame"].destroy()
    del tabs[name]
    return True

def close_current_tab():
    global active_tab, previous_active_tab
    if active_tab is None:
        return

    if not close_tab(active_tab):
        return

    if previous_active_tab in tabs:
        switch_tab(previous_active_tab)
        previous_active_tab = None
    elif tabs:
        active_tab = list(tabs.keys())[0]
        switch_tab(active_tab)
    else:
        new_tab()

def new_tab():
    global tab_counter
    name = f"untitled{tab_counter}.cpp"
    tab_counter += 1

    frame = ctk.CTkFrame(tab_bar, fg_color="transparent")
    frame.grid(row=0, column=len(tabs), padx=(0, 4))

    btn = ctk.CTkButton(
        frame,
        text=name,
        height=28,
        fg_color="#1f1f1f",
        hover_color="#333333",
        corner_radius=5,
        command=lambda n=name: switch_tab(n)
    )
    btn.grid(row=0, column=0)

    close_btn = ctk.CTkButton(
        frame,
        text="×",
        width=28,
        height=28,
        fg_color="transparent",
        hover_color="#aa3333",
        command=lambda n=name: close_tab(n)
    )

    tabs[name] = {
        "frame": frame,
        "button": btn,
        "close": close_btn,
        "content": "",
        "saved_content": "",
        "path": None
    }

    switch_tab(name)

# "+" Button
add_btn = ctk.CTkButton(
    tab_bar,
    text="+",
    width=32,
    height=28,
    fg_color="#1f1f1f",
    hover_color="#333333",
    command=new_tab
)
add_btn.grid(row=0, column=998, padx=5)

# Code Editor (must be created before syntax loading)
code_editor = tk.Text(
    editor_frame,
    bg="#1e1e1e",
    fg="#dcdcdc",
    insertbackground="white",
    font=("Consolas", 14),
    undo=True,
    wrap="none"
)
code_editor.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

# Load syntax after code_editor exists
tag_map = {}

def load_syntax(file_path, silent=False):
    global theme, tag_map
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            theme = {k: v for k, v in loaded.items() if k != "name"}
        # Reconfigure tags
        tag_map = {}
        for word, color in theme.items():
            tag_name = f"hl_{word.replace('#', 'hash').replace(':', 'colon')}"
            code_editor.tag_configure(tag_name, foreground=color)
            tag_map[word] = tag_name
        if not silent:
            messagebox.showinfo("Syntax Loaded", f"Loaded: {os.path.basename(file_path)}")
        # Re-highlight active tab
        if active_tab:
            highlight_code()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load syntax file:\n{e}")

# Load initial syntax (silent = no popup)
load_syntax(SYNTAX_FILE, silent=True)

# Syntax highlighting function
def highlight_code(event=None):
    if not active_tab or not theme:
        return

    # Clear previous tags
    for tag_name in tag_map.values():
        code_editor.tag_remove(tag_name, "1.0", "end")

    text_content = code_editor.get("1.0", "end")

    for word in theme:
        escaped = re.escape(word)
        pattern = r'\b' + escaped + r'\b' if not word.startswith('#') else escaped
        for match in re.finditer(pattern, text_content):
            start = f"1.0 + {match.start()} chars"
            end = f"1.0 + {match.end()} chars"
            code_editor.tag_add(tag_map[word], start, end)

def on_edit(event=None):
    if active_tab:
        current = code_editor.get("1.0", "end-1c")
        tabs[active_tab]["content"] = current

        tab_data = tabs[active_tab]
        title = tab_data["button"].cget("text")
        if current != tab_data["saved_content"]:
            if not title.endswith("*"):
                tab_data["button"].configure(text=title + "*")
        else:
            if title.endswith("*"):
                tab_data["button"].configure(text=title[:-1])

        highlight_code()

code_editor.bind("<KeyRelease>", on_edit)

# File operations
def save_current_tab():
    if active_tab is None or active_tab not in tabs:
        return False
    tab = tabs[active_tab]

    if tab["path"] is None:
        return save_as_current_tab()
    else:
        try:
            with open(tab["path"], "w", encoding="utf-8") as f:
                f.write(tab["content"])
            tab["saved_content"] = tab["content"]
            title = tab["button"].cget("text")
            if title.endswith("*"):
                tab["button"].configure(text=title[:-1])
            return True
        except Exception as e:
            messagebox.showerror("Save Failed", f"Could not save:\n{e}")
            return False

def save_as_current_tab():
    if active_tab is None or active_tab not in tabs:
        return False
    tab = tabs[active_tab]

    filetypes = [("C++ files", "*.cpp *.h *.hpp"), ("All files", "*.*")]
    path = filedialog.asksaveasfilename(
        title="Save As",
        defaultextension=".cpp",
        filetypes=filetypes,
        initialfile=tab["button"].cget("text").rstrip("*")
    )
    if not path:
        return False

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(tab["content"])
        tab["path"] = path
        tab["saved_content"] = tab["content"]
        filename = path.split("/")[-1] if "/" in path else path.split("\\")[-1]
        tab["button"].configure(text=filename)
        return True
    except Exception as e:
        messagebox.showerror("Save Failed", f"Could not save:\n{e}")
        return False

def open_file():
    filetypes = [("C++ files", "*.cpp *.h *.hpp"), ("Text files", "*.txt"), ("All files", "*.*")]
    path = filedialog.askopenfilename(title="Open File", filetypes=filetypes)
    if not path:
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        for tab_name, tab in tabs.items():
            if tab["path"] == path:
                switch_tab(tab_name)
                return

        filename = path.split("/")[-1] if "/" in path else path.split("\\")[-1]

        frame = ctk.CTkFrame(tab_bar, fg_color="transparent")
        frame.grid(row=0, column=len(tabs), padx=(0, 4))

        btn = ctk.CTkButton(
            frame,
            text=filename,
            height=28,
            fg_color="#1f1f1f",
            hover_color="#333333",
            corner_radius=5,
            command=lambda n=filename: switch_tab(n)
        )
        btn.grid(row=0, column=0)

        close_btn = ctk.CTkButton(
            frame,
            text="×",
            width=28,
            height=28,
            fg_color="transparent",
            hover_color="#aa3333",
            command=lambda n=filename: close_tab(n)
        )

        tabs[filename] = {
            "frame": frame,
            "button": btn,
            "close": close_btn,
            "content": content,
            "saved_content": content,
            "path": path
        }

        switch_tab(filename)
        code_editor.delete("1.0", "end")
        code_editor.insert("1.0", content)
        highlight_code()

    except Exception as e:
        messagebox.showerror("Open Failed", f"Could not open file:\n{e}")

# Settings window
def open_settings():
    settings_win = ctk.CTkToplevel(app)
    settings_win.title("Settings")
    settings_win.geometry("600x500")
    settings_win.resizable(False, False)
    
    # Make it a child window
    settings_win.transient(app)
    
    # Force it to the front
    settings_win.lift()
    settings_win.focus_force()  # Give it keyboard focus too
    
    # Always on top (only while open)
    settings_win.attributes('-topmost', True)
    settings_win.after(100, lambda: settings_win.attributes('-topmost', False))

    ctk.CTkLabel(settings_win, text="Syntax Highlighting", font=("Arial", 18, "bold")).pack(pady=15)

    # Current syntax file display
    current_label = ctk.CTkLabel(settings_win, text=f"Current: {os.path.basename(SYNTAX_FILE)}", font=("Arial", 12))
    current_label.pack(pady=5)

    def reload_current():
        load_syntax(SYNTAX_FILE)
        current_label.configure(text=f"Current: {os.path.basename(SYNTAX_FILE)}")
        messagebox.showinfo("Reloaded", "Current syntax reloaded.")

    ctk.CTkButton(settings_win, text="Reload Current Syntax", command=reload_current).pack(pady=5)

    # Load new syntax file
    def load_new_syntax():
        global SYNTAX_FILE
        path = filedialog.askopenfilename(
            title="Select Syntax JSON File",
            initialdir=SYNTAX_DIR,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if path:
            SYNTAX_FILE = path
            load_syntax(path)
            current_label.configure(text=f"Current: {os.path.basename(path)}")

    ctk.CTkButton(settings_win, text="Load New Syntax File", command=load_new_syntax).pack(pady=10)

    # Create new syntax file
    def create_new_syntax():
        name = ctk.CTkInputDialog(
            title="New Syntax Theme",
            text="Enter name for new theme (without .json):"
        ).get_input()
        if not name:
            return

        new_path = os.path.join(SYNTAX_DIR, f"{name}.json")
        default_content = {
            "name": name,
            "int": "#ff79c6",
            "float": "#ff79c6",
            "double": "#ff79c6",
            "char": "#ff79c6",
            "void": "#ff79c6",
            "if": "#ff79c6",
            "else": "#ff79c6",
            "for": "#ff79c6",
            "while": "#ff79c6",
            "switch": "#ff79c6",
            "case": "#ff79c6",
            "return": "#ff79c6",
            "#include": "#8be9fd",
            "cout": "#50fa7b",
            "cin": "#50fa7b",
            "using": "#bd93f9",
            "namespace": "#bd93f9",
            "std": "#bd93f9"
        }

        try:
            with open(new_path, "w", encoding="utf-8") as f:
                json.dump(default_content, f, indent=2)
            messagebox.showinfo("Success", f"Created {new_path}\nEdit it and load it in settings.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not create file:\n{e}")

    ctk.CTkButton(settings_win, text="Create New Syntax Theme", command=create_new_syntax).pack(pady=10)

    # Revert to default
    def revert_to_default():
        global SYNTAX_FILE
        default_path = os.path.join(SYNTAX_DIR, "default.json")
        if os.path.exists(default_path):
            SYNTAX_FILE = default_path
            load_syntax(default_path)
            current_label.configure(text="Current: default.json")
        else:
            messagebox.showerror("Not Found", "default.json not found in Hsyntax folder.")

    ctk.CTkButton(settings_win, text="Revert to Default", command=revert_to_default).pack(pady=10)

    ctk.CTkLabel(settings_win, text="Note: Restart the app if changes don't apply fully.", font=("Arial", 10)).pack(pady=20)


# Keyboard shortcuts
def on_key_press(event):
    if event.keysym == "s" and event.state & 0x4:  # Ctrl+S
        save_current_tab()
        return "break"
    elif event.keysym == "o" and event.state & 0x4:  # Ctrl+O
        open_file()
        return "break"
    elif event.keysym == "t" and event.state & 0x4:  # Ctrl+T
        new_tab()
        return "break"
    elif event.keysym == "w" and event.state & 0x4:  # Ctrl+W
        close_current_tab()
        return "break"
    elif event.keysym == "S" and (event.state & 0x4) and (event.state & 0x1):  # Ctrl+Shift+S
        open_settings()
        return "break"

app.bind_all("<Control-s>", on_key_press)
app.bind_all("<Control-o>", on_key_press)
app.bind_all("<Control-t>", on_key_press)
app.bind_all("<Control-w>", on_key_press)
app.bind_all("<Control-Shift-S>", on_key_press)

# Initial tab
new_tab()
tabs[active_tab]["content"] = """#include <iostream>
using namespace std;

int main() {
    cout << "Hello, Run++!" << endl;
    return 0;
}
"""
tabs[active_tab]["saved_content"] = tabs[active_tab]["content"]
code_editor.insert("1.0", tabs[active_tab]["content"])
highlight_code()
switch_tab(active_tab)

# Right Panel
right_frame = ctk.CTkFrame(paned, corner_radius=10)
right_frame.grid_rowconfigure(1, weight=1)
right_frame.grid_columnconfigure(0, weight=1)

paned.add(right_frame, minsize=250)

def run_code():
    output_box.configure(state="normal")
    output_box.delete("1.0", "end")
    output_box.insert("end", "Compiling...\nRunning...\n\nHello, Run++!\n")
    output_box.configure(state="disabled")

run_button = ctk.CTkButton(
    right_frame,
    text="Run",
    font=("Arial", 16),
    command=run_code
)
run_button.pack(padx=10, pady=10, fill="x")

output_label = ctk.CTkLabel(right_frame, text="Output")
output_label.pack(anchor="w", padx=10)

output_box = tk.Text(
    right_frame,
    bg="#111111",
    fg="#00ff88",
    font=("Consolas", 13),
    state="disabled",
    wrap="word"
)
output_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))

app.mainloop()
