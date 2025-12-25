import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, font as tkfont
import re
import json
import os
from fontTools.ttLib import TTFont
import subprocess
import threading
import platform

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

app = ctk.CTk()
app.title("Run++")
app.geometry("1000x600")

# Settings file
SETTINGS_FILE = "settings.json"

# Default settings
DEFAULT_SETTINGS = {
    "auto_save": True,
    "font_size": 14,
    "font_family": "Consolas",
    "theme": "dark",
    "cpp_standard": "17",
    "show_compiler_cmd": True,
    "tab_width": 4,
    "highlight_current_line": True,
    "syntax_highlighting": True,
    "output_font_family": "Consolas",
    "output_font_size": 13,
    "output_text_color": "#00ff88",
    "output_bg_color": "#111111",
    "current_syntax_file": "default.json",
    "show_system_fonts": False,
    "use_external_terminal": False
}

# Load or create settings
settings = DEFAULT_SETTINGS.copy()
if os.path.exists(SETTINGS_FILE):
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            settings.update(loaded)
    except Exception:
        pass
else:
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)

# Font handling
FONTS_DIR = "fonts"
DEFAULT_FONTS = {"Consolas", "Courier New", "Monospace"}
loaded_custom_font_names = set()


def clean_code_text(text):
    """
    Remove problematic invisible Unicode characters that cause compilation errors.
    Only removes definitively wrong characters, preserves valid special characters.
    """
    # Non-breaking spaces → regular space
    text = text.replace('\u00a0', ' ')  # Non-breaking space
    text = text.replace('\u202f', ' ')  # Narrow no-break space
    text = text.replace('\u2007', ' ')  # Figure space
    text = text.replace('\u2009', ' ')  # Thin space
    text = text.replace('\u200a', ' ')  # Hair space
    
    # Zero-width characters → remove completely
    text = text.replace('\u200b', '')   # Zero-width space
    text = text.replace('\u200c', '')   # Zero-width non-joiner
    text = text.replace('\u200d', '')   # Zero-width joiner
    text = text.replace('\ufeff', '')   # Zero-width no-break space (BOM)
    
    # Right-to-left and left-to-right marks → remove
    text = text.replace('\u200e', '')   # Left-to-right mark
    text = text.replace('\u200f', '')   # Right-to-left mark
    text = text.replace('\u202a', '')   # Left-to-right embedding
    text = text.replace('\u202b', '')   # Right-to-left embedding
    text = text.replace('\u202c', '')   # Pop directional formatting
    text = text.replace('\u202d', '')   # Left-to-right override
    text = text.replace('\u202e', '')   # Right-to-left override
    
    # Soft hyphen → remove
    text = text.replace('\u00ad', '')   # Soft hyphen
    
    return text


def get_font_family_name(ttf_path):
    try:
        ttfont = TTFont(ttf_path)
        for record in ttfont['name'].names:
            if record.nameID == 4:
                try:
                    return record.toUnicode()
                except:
                    continue
            elif record.nameID == 1:
                try:
                    return record.toUnicode()
                except:
                    continue
        return os.path.splitext(os.path.basename(ttf_path))[0]
    except Exception:
        return os.path.splitext(os.path.basename(ttf_path))[0]

def load_custom_fonts():
    global loaded_custom_font_names
    loaded_custom_font_names = set()
    if not os.path.exists(FONTS_DIR):
        os.makedirs(FONTS_DIR)
        return
    for filename in os.listdir(FONTS_DIR):
        if filename.lower().endswith(('.ttf', '.otf')):
            file_path = os.path.join(FONTS_DIR, filename)
            family_name = get_font_family_name(file_path)
            try:
                tkfont.Font(font=(family_name, 12), file=file_path)
                loaded_custom_font_names.add(family_name)
            except tk.TclError:
                pass

load_custom_fonts()

all_tk_fonts = set(tkfont.families())
other_system_fonts = all_tk_fonts - DEFAULT_FONTS - loaded_custom_font_names
base_fonts = loaded_custom_font_names | DEFAULT_FONTS

def get_available_fonts():
    if settings.get("show_system_fonts", False):
        return sorted(base_fonts | other_system_fonts)
    else:
        return sorted(base_fonts)

available_fonts = get_available_fonts()

if settings["font_family"] not in available_fonts and available_fonts:
    settings["font_family"] = "Consolas"
if settings["output_font_family"] not in available_fonts and available_fonts:
    settings["output_font_family"] = "Consolas"

code_editor_font = (settings["font_family"], settings["font_size"])

# Syntax variables
SYNTAX_DIR = "Hsyntax"
if not os.path.exists(SYNTAX_DIR):
    os.makedirs(SYNTAX_DIR)
SYNTAX_FILE = os.path.join(SYNTAX_DIR, settings["current_syntax_file"])
theme = {}
tag_map = {}
compiled_syntax_regex = None
highlight_after_id = None

# Main Split View
paned = tk.PanedWindow(app, orient=tk.HORIZONTAL, sashwidth=6, bg="#1a1a1a", bd=0, relief="flat")
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
tab_bar.grid_columnconfigure(999, weight=1)

tabs = {}
active_tab = None
previous_active_tab = None
tab_counter = 1

# Line number setup
text_frame = ctk.CTkFrame(editor_frame)
text_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
text_frame.grid_rowconfigure(0, weight=1)
text_frame.grid_columnconfigure(1, weight=1)

# Line numbers canvas
line_numbers = tk.Canvas(
    text_frame,
    width=50,
    bg="#1e1e1e",
    highlightthickness=0
)
line_numbers.grid(row=0, column=0, sticky="ns")

# Code Editor
code_editor = tk.Text(
    text_frame,
    bg="#1e1e1e",
    fg="#dcdcdc",
    insertbackground="white",
    font=code_editor_font,
    undo=True,
    wrap="none",
    tabs=settings["tab_width"] * 8
)
code_editor.grid(row=0, column=1, sticky="nsew")

# Scrollbar
scrollbar = ctk.CTkScrollbar(text_frame, command=code_editor.yview)
scrollbar.grid(row=0, column=2, sticky="ns")


try:
    scrollbar.configure(cursor="sb_v_double_arrow")
except:
    pass


def on_scroll(*args):
    scrollbar.set(*args)
    update_line_numbers()

code_editor.configure(yscrollcommand=on_scroll)

# Update line numbers
def update_line_numbers(event=None):
    line_numbers.delete("all")
    
    first_visible = code_editor.index("@0,0")
    line_num = int(first_visible.split('.')[0])

    i = code_editor.index("@0,0")
    while True:
        dline = code_editor.dlineinfo(i)
        if dline is None:
            break
        y = dline[1] + dline[3] // 2
        linenum_str = str(line_num)
        line_numbers.create_text(40, y, anchor="e", text=linenum_str, fill="#666666", font=code_editor_font)
        i = code_editor.index(f"{i}+1line")
        line_num += 1

# Bind events to  line numbers update
code_editor.bind("<KeyRelease>", lambda e: code_editor.after_idle(update_line_numbers))
code_editor.bind("<MouseWheel>", lambda e: code_editor.after_idle(update_line_numbers))
code_editor.bind("<Button-4>", lambda e: code_editor.after_idle(update_line_numbers))
code_editor.bind("<Button-5>", lambda e: code_editor.after_idle(update_line_numbers))
text_frame.bind("<Configure>", lambda e: code_editor.after_idle(update_line_numbers))

# Bind scrollbar drag to update line numbers
def on_scrollbar_command(*args):
    code_editor.yview(*args)
    code_editor.after_idle(update_line_numbers)

scrollbar.configure(command=on_scrollbar_command)

# Initial update (run multiple times to ensure it works)
def initial_line_number_update():
    update_line_numbers()
    app.after(50, update_line_numbers)
    app.after(150, update_line_numbers)
    app.after(300, update_line_numbers)

app.after(100, initial_line_number_update)

code_editor.tag_configure("current_line", background="#2a2a2a")

# Global process
process = None

def switch_tab(tab_id):
    global active_tab, previous_active_tab
    if active_tab is not None and active_tab != tab_id:
        previous_active_tab = active_tab
    active_tab = tab_id
    for tid, tab_data in tabs.items():
        is_active = (tid == tab_id)
        tab_data["button"].configure(fg_color="#2b2b2b" if is_active else "#1f1f1f")
        if is_active:
            tab_data["close"].grid(row=0, column=1, padx=(5, 0))
        else:
            tab_data["close"].grid_forget()
    code_editor.delete("1.0", "end")
    code_editor.insert("1.0", tabs[tab_id]["content"])
    highlight_code()
    update_line_numbers()

def close_tab(tab_id):
    tab = tabs.get(tab_id)
    if not tab:
        return False
    if tab["content"] != tab["saved_content"]:
        response = messagebox.askyesnocancel(
            "Unsaved Changes",
            f"Save changes to {tab['display'].rstrip('*')} before closing?"
        )
        if response is None:
            return False
        if response:
            if not save_current_tab():
                return False
    tab["frame"].destroy()
    del tabs[tab_id]
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
        active_tab = next(iter(tabs))
        switch_tab(active_tab)
    else:
        new_tab()

def new_tab(path=None):
    global tab_counter
    tab_id = f"tab_{tab_counter}"
    tab_counter += 1
    if path:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            display_name = os.path.basename(path)
        except:
            messagebox.showerror("Open Failed", "Could not read file.")
            return
    else:
        content = ""
        display_name = f"untitled{tab_counter-1}.cpp"
    frame = ctk.CTkFrame(tab_bar, fg_color="transparent")
    frame.grid(row=0, column=len(tabs), padx=(0, 4))
    btn = ctk.CTkButton(
        frame,
        text=display_name,
        height=28,
        fg_color="#1f1f1f",
        hover_color="#333333",
        corner_radius=5,
        command=lambda tid=tab_id: switch_tab(tid)
    )
    btn.grid(row=0, column=0)
    close_btn = ctk.CTkButton(
        frame,
        text="×",
        width=28,
        height=28,
        fg_color="transparent",
        hover_color="#aa3333",
        command=lambda tid=tab_id: (
            switch_tab(tid),
            close_current_tab()
        )
    )
    tabs[tab_id] = {
        "id": tab_id,
        "display": display_name,
        "frame": frame,
        "button": btn,
        "close": close_btn,
        "content": content,
        "saved_content": content,
        "path": path
    }
    switch_tab(tab_id)

add_btn = ctk.CTkButton(
    tab_bar,
    text="+",
    width=32,
    height=28,
    fg_color="#1f1f1f",
    hover_color="#333333",
    command=lambda: new_tab()
)
add_btn.grid(row=0, column=998, padx=5)

def highlight_current_line(event=None):
    if settings["highlight_current_line"]:
        code_editor.tag_remove("current_line", "1.0", "end")
        code_editor.tag_add("current_line", "insert linestart", "insert lineend+1c")
    else:
        code_editor.tag_remove("current_line", "1.0", "end")

def on_edit(event=None):
    global highlight_after_id
    if active_tab:
        current = code_editor.get("1.0", "end-1c")
        tab = tabs[active_tab]
        tab["content"] = current
        title = tab["button"].cget("text")
        display_base = tab["display"]
        if current != tab["saved_content"]:
            if not title.endswith("*"):
                tab["button"].configure(text=display_base + "*")
        else:
            if title.endswith("*"):
                tab["button"].configure(text=display_base)
        if highlight_after_id:
            code_editor.after_cancel(highlight_after_id)
        highlight_after_id = code_editor.after(120, highlight_code)
        if settings.get("auto_save") and tab["path"]:
            save_current_tab()
        highlight_current_line()
        update_line_numbers()

code_editor.bind("<KeyRelease>", on_edit)
code_editor.bind("<Button-1>", lambda e: code_editor.after(1, highlight_current_line))
code_editor.bind("<ButtonRelease-1>", lambda e: highlight_current_line())

def highlight_code():
    if not active_tab:
        return
    for tag in tag_map.values():
        code_editor.tag_remove(tag, "1.0", "end")
    if settings["syntax_highlighting"] and compiled_syntax_regex:
        text = code_editor.get("1.0", "end-1c")
        for match in compiled_syntax_regex.finditer(text):
            word = match.group(0)
            tag = tag_map.get(word)
            if tag:
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                code_editor.tag_add(tag, start, end)

def load_syntax(file_path, silent=False):
    global theme, tag_map, compiled_syntax_regex
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            theme = {k: v for k, v in loaded.items() if k != "name"}
        tag_map = {}
        patterns = []
        for word, color in theme.items():
            tag_name = f"hl_{word.replace('#', 'hash').replace(':', 'colon')}"
            code_editor.tag_configure(tag_name, foreground=color)
            tag_map[word] = tag_name
            if word.startswith("#"):
                patterns.append(re.escape(word))
            else:
                patterns.append(rf"\b{re.escape(word)}\b")
        compiled_syntax_regex = re.compile("|".join(patterns)) if patterns else None
        if not silent:
            messagebox.showinfo("Syntax Loaded", f"Loaded: {os.path.basename(file_path)}")
        highlight_code()
    except Exception as e:
        if not silent:
            messagebox.showerror("Error", f"Failed to load syntax file:\n{e}")
        theme = {}
        tag_map = {}
        compiled_syntax_regex = None
        highlight_code()

load_syntax(SYNTAX_FILE, silent=True)

# File operations
def save_current_tab():
    if active_tab is None:
        return False
    tab = tabs[active_tab]
    if tab["path"] is None:
        return save_as_current_tab()
    try:
        # Clean the content before saving
        cleaned_content = clean_code_text(tab["content"])
        
        with open(tab["path"], "w", encoding="utf-8") as f:
            f.write(cleaned_content)
        
        # Update the tab content to the cleaned version
        tab["content"] = cleaned_content
        tab["saved_content"] = cleaned_content
        
        # Update the editor display if content changed
        if cleaned_content != code_editor.get("1.0", "end-1c"):
            code_editor.delete("1.0", "end")
            code_editor.insert("1.0", cleaned_content)
            highlight_code()
        
        if tab["button"].cget("text").endswith("*"):
            tab["button"].configure(text=tab["display"])
        return True
    except Exception as e:
        messagebox.showerror("Save Failed", f"Could not save:\n{e}")
        return False

def save_as_current_tab():
    if active_tab is None:
        return False
    tab = tabs[active_tab]
    filetypes = [("C++ files", "*.cpp *.h *.hpp"), ("All files", "*.*")]
    path = filedialog.asksaveasfilename(
        title="Save As",
        defaultextension=".cpp",
        filetypes=filetypes,
        initialfile=tab["display"].rstrip("*")
    )
    if not path:
        return False
    try:
        # Clean the content before saving
        cleaned_content = clean_code_text(tab["content"])
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(cleaned_content)
        
        tab["path"] = path
        tab["content"] = cleaned_content
        tab["saved_content"] = cleaned_content
        
        # Update the editor display if content changed
        if cleaned_content != code_editor.get("1.0", "end-1c"):
            code_editor.delete("1.0", "end")
            code_editor.insert("1.0", cleaned_content)
            highlight_code()
        
        filename = os.path.basename(path)
        tab["display"] = filename
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
    for tab in tabs.values():
        if tab["path"] == path:
            switch_tab(tab["id"])
            return
    new_tab(path=path)

# Font & UI helpers
def update_font_size(size):
    global code_editor_font
    size = int(size)
    settings["font_size"] = size
    code_editor_font = (settings["font_family"], size)
    code_editor.configure(font=code_editor_font)
    update_line_numbers()

def update_tab_width(width):
    width = int(width)
    settings["tab_width"] = width
    code_editor.configure(tabs=width * 8)

def update_font_lists():
    global available_fonts
    available_fonts = get_available_fonts()
    if 'font_family_combo' in globals():
        current = font_family_combo.get()
        font_family_combo.configure(values=available_fonts)
        if current not in available_fonts and available_fonts:
            new_font = "Consolas"
            font_family_combo.set(new_font)
            settings["font_family"] = new_font
            update_font_size(settings["font_size"])
        else:
            font_family_combo.set(current)
    if 'output_font_combo' in globals():
        current = output_font_combo.get()
        output_font_combo.configure(values=available_fonts)
        if current not in available_fonts and available_fonts:
            new_font = "Consolas"
            output_font_combo.set(new_font)
            settings["output_font_family"] = new_font
        else:
            output_font_combo.set(current)

def apply_settings_to_ui(settings_dict):
    settings.update(settings_dict)
    update_font_size(settings["font_size"])
    update_tab_width(settings["tab_width"])
    try:
        output_box.configure(
            font=(settings["output_font_family"], settings["output_font_size"]),
            fg=settings["output_text_color"],
            bg=settings["output_bg_color"]
        )
    except tk.TclError:
        pass
    highlight_code()
    highlight_current_line()
    update_line_numbers()

# Settings window
def open_settings():
    settings_win = ctk.CTkToplevel(app)
    settings_win.title("Settings")
    settings_win.geometry("650x650")
    settings_win.transient(app)
    settings_win.lift()
    settings_win.focus_force()
    settings_win.attributes('-topmost', True)
    settings_win.after(100, lambda: settings_win.attributes('-topmost', False))

    original_settings = settings.copy()

    top_frame = ctk.CTkFrame(settings_win, fg_color="#2b2b2b")
    top_frame.pack(fill="x", pady=10)

    content_frame = ctk.CTkFrame(settings_win, fg_color="transparent")
    content_frame.pack(fill="both", expand=True, padx=20, pady=10)

    general_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    compiler_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    editor_settings_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    syntax_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    output_frame = ctk.CTkFrame(content_frame, fg_color="transparent")

    output_font_combo = None
    output_show_system_switch = None
    output_font_slider = None
    output_text_color_entry = None
    output_bg_color_entry = None
    external_terminal_switch = None

    def show_output_tab():
        nonlocal output_font_combo, output_show_system_switch, output_font_slider, output_text_color_entry, output_bg_color_entry, external_terminal_switch
        [f.pack_forget() for f in [general_frame, compiler_frame, editor_settings_frame, syntax_frame]]
        output_frame.pack(fill="both", expand=True)
        for widget in output_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(output_frame, text="Output Panel Appearance", font=("Arial", 16, "bold")).pack(anchor="w", pady=(10, 15))

        ctk.CTkLabel(output_frame, text="Use External Terminal", font=("Arial", 14)).pack(anchor="w", pady=(10, 5))
        external_terminal_switch = ctk.CTkSwitch(
            output_frame,
            text="Run programs in a separate console window",
            command=lambda: (
                settings.update({"use_external_terminal": external_terminal_switch.get()}),
                apply_settings_to_ui(settings)
            )
        )
        external_terminal_switch.pack(anchor="w", padx=10, pady=5)
        external_terminal_switch.select() if settings["use_external_terminal"] else external_terminal_switch.deselect()

        ctk.CTkLabel(output_frame, text="Font Family").pack(anchor="w", padx=10, pady=(20, 0))
        output_font_combo = ctk.CTkComboBox(
            output_frame,
            values=available_fonts,
            state="readonly",
            command=lambda v: (
                settings.update({"output_font_family": v}),
                apply_settings_to_ui(settings)
            )
        )
        output_font_combo.set(settings["output_font_family"])
        output_font_combo.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(output_frame, text="Show Other System Fonts", font=("Arial", 14)).pack(anchor="w", pady=(20, 5))
        output_show_system_switch = ctk.CTkSwitch(
            output_frame,
            text="Include all other installed system fonts (e.g. Arial, Times, etc.)",
            command=lambda: (
                settings.update({"show_system_fonts": output_show_system_switch.get()}),
                update_font_lists()
            )
        )
        output_show_system_switch.pack(anchor="w", padx=10, pady=5)
        output_show_system_switch.select() if settings["show_system_fonts"] else output_show_system_switch.deselect()

        ctk.CTkLabel(output_frame, text="Font Size").pack(anchor="w", padx=10, pady=(15, 0))
        output_font_slider = ctk.CTkSlider(
            output_frame,
            from_=8, to=20, number_of_steps=12,
            command=lambda v: (
                settings.update({"output_font_size": int(v)}),
                apply_settings_to_ui(settings)
            )
        )
        output_font_slider.set(settings["output_font_size"])
        output_font_slider.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(output_frame, text="Text Color").pack(anchor="w", padx=10, pady=(15, 0))
        output_text_color_entry = ctk.CTkEntry(output_frame)
        output_text_color_entry.insert(0, settings["output_text_color"])
        output_text_color_entry.pack(fill="x", padx=10, pady=5)

        def on_output_text_color_change(event=None):
            settings["output_text_color"] = output_text_color_entry.get()
            apply_settings_to_ui(settings)

        output_text_color_entry.bind("<KeyRelease>", on_output_text_color_change)

        ctk.CTkLabel(output_frame, text="Background Color").pack(anchor="w", padx=10, pady=(15, 0))
        output_bg_color_entry = ctk.CTkEntry(output_frame)
        output_bg_color_entry.insert(0, settings["output_bg_color"])
        output_bg_color_entry.pack(fill="x", padx=10, pady=5)

        def on_output_bg_color_change(event=None):
            settings["output_bg_color"] = output_bg_color_entry.get()
            apply_settings_to_ui(settings)

        output_bg_color_entry.bind("<KeyRelease>", on_output_bg_color_change)

    # General Tab
    ctk.CTkLabel(general_frame, text="Auto-save on edit", font=("Arial", 14)).pack(anchor="w", pady=5)
    auto_save_switch = ctk.CTkSwitch(
        general_frame, text="Enable",
        command=lambda: settings.update({"auto_save": auto_save_switch.get()})
    )
    auto_save_switch.pack(anchor="w", padx=10, pady=5)
    auto_save_switch.select() if settings["auto_save"] else auto_save_switch.deselect()

    ctk.CTkLabel(general_frame, text="Editor Font Family", font=("Arial", 14)).pack(anchor="w", pady=(20, 5))
    global font_family_combo
    font_family_combo = ctk.CTkComboBox(
        general_frame,
        values=available_fonts,
        state="readonly",
        command=lambda v: (settings.update({"font_family": v}), update_font_size(settings["font_size"]))
    )
    font_family_combo.set(settings["font_family"])
    font_family_combo.pack(fill="x", padx=10, pady=5)

    ctk.CTkLabel(general_frame, text="Show Other System Fonts", font=("Arial", 14)).pack(anchor="w", pady=(20, 5))
    show_system_fonts_switch = ctk.CTkSwitch(
        general_frame,
        text="Include all other installed system fonts (e.g. Arial, Times, etc.)",
        command=lambda: (
            settings.update({"show_system_fonts": show_system_fonts_switch.get()}),
            update_font_lists()
        )
    )
    show_system_fonts_switch.pack(anchor="w", padx=10, pady=5)
    show_system_fonts_switch.select() if settings["show_system_fonts"] else show_system_fonts_switch.deselect()

    ctk.CTkLabel(general_frame, text="Editor Font Size", font=("Arial", 14)).pack(anchor="w", pady=(20, 5))
    font_size_slider = ctk.CTkSlider(
        general_frame,
        from_=8, to=24, number_of_steps=16,
        command=update_font_size
    )
    font_size_slider.set(settings["font_size"])
    font_size_slider.pack(fill="x", padx=10, pady=5)

    # Compiler Tab
    ctk.CTkLabel(compiler_frame, text="C++ Standard", font=("Arial", 14)).pack(anchor="w", pady=5)
    cpp_std_combo = ctk.CTkComboBox(
        compiler_frame,
        values=["14", "17", "20", "23"],
        state="readonly",
        command=lambda v: settings.update({"cpp_standard": v})
    )
    cpp_std_combo.set(settings["cpp_standard"])
    cpp_std_combo.pack(fill="x", padx=10, pady=5)

    ctk.CTkLabel(compiler_frame, text="Show Compiler Command", font=("Arial", 14)).pack(anchor="w", pady=(20, 5))
    show_cmd_switch = ctk.CTkSwitch(
        compiler_frame, text="Enable",
        command=lambda: settings.update({"show_compiler_cmd": show_cmd_switch.get()})
    )
    show_cmd_switch.pack(anchor="w", padx=10, pady=5)
    show_cmd_switch.select() if settings["show_compiler_cmd"] else show_cmd_switch.deselect()

    # Editor Settings Tab
    ctk.CTkLabel(editor_settings_frame, text="Tab Width (spaces)", font=("Arial", 14)).pack(anchor="w", pady=5)
    tab_width_slider = ctk.CTkSlider(
        editor_settings_frame,
        from_=2, to=8, number_of_steps=6,
        command=update_tab_width
    )
    tab_width_slider.set(settings["tab_width"])
    tab_width_slider.pack(fill="x", padx=10, pady=5)

    ctk.CTkLabel(editor_settings_frame, text="Highlight Current Line", font=("Arial", 14)).pack(anchor="w", pady=(20, 5))
    highlight_line_switch = ctk.CTkSwitch(
        editor_settings_frame, text="Enable",
        command=lambda: settings.update({"highlight_current_line": highlight_line_switch.get()}) or highlight_current_line()
    )
    highlight_line_switch.pack(anchor="w", padx=10, pady=5)
    highlight_line_switch.select() if settings["highlight_current_line"] else highlight_line_switch.deselect()

    ctk.CTkLabel(editor_settings_frame, text="Syntax Highlighting", font=("Arial", 14)).pack(anchor="w", pady=(20, 5))
    syntax_switch = ctk.CTkSwitch(
        editor_settings_frame, text="Enable",
        command=lambda: (
            settings.update({"syntax_highlighting": syntax_switch.get()}),
            highlight_code()
        )
    )
    syntax_switch.pack(anchor="w", padx=10, pady=5)
    syntax_switch.select() if settings["syntax_highlighting"] else syntax_switch.deselect()

    # Syntax Tab
    ctk.CTkLabel(syntax_frame, text="Syntax Highlighting Theme", font=("Arial", 16, "bold")).pack(anchor="w", pady=(10, 15))
    available_syntaxes = [f for f in os.listdir(SYNTAX_DIR) if f.endswith(".json")] if os.path.exists(SYNTAX_DIR) else []
    syntax_combo = ctk.CTkComboBox(
        syntax_frame,
        values=available_syntaxes,
        state="readonly",
        width=300,
        command=lambda v: (
            settings.update({"current_syntax_file": v}),
            load_syntax(os.path.join(SYNTAX_DIR, v), silent=True),
            apply_settings_to_ui(settings)
        )
    )
    if settings["current_syntax_file"] in available_syntaxes:
        syntax_combo.set(settings["current_syntax_file"])
    elif available_syntaxes:
        syntax_combo.set(available_syntaxes[0])
    syntax_combo.pack(anchor="w", padx=10, pady=10)

    ctk.CTkLabel(syntax_frame, text="Note: Changes are applied immediately in preview.\nSave settings to make permanent.",
                 font=("Arial", 11), text_color="gray").pack(anchor="w", padx=10, pady=15)

    # Initial tab visibility
    general_frame.pack(fill="both", expand=True)

    def show_general():
        [f.pack_forget() for f in [compiler_frame, editor_settings_frame, syntax_frame, output_frame]]
        general_frame.pack(fill="both", expand=True)

    def show_compiler():
        [f.pack_forget() for f in [general_frame, editor_settings_frame, syntax_frame, output_frame]]
        compiler_frame.pack(fill="both", expand=True)

    def show_editor():
        [f.pack_forget() for f in [general_frame, compiler_frame, syntax_frame, output_frame]]
        editor_settings_frame.pack(fill="both", expand=True)

    def show_syntax():
        [f.pack_forget() for f in [general_frame, compiler_frame, editor_settings_frame, output_frame]]
        syntax_frame.pack(fill="both", expand=True)

    ctk.CTkButton(top_frame, text="General", width=120, command=show_general).pack(side="left", padx=3)
    ctk.CTkButton(top_frame, text="Compiler", width=120, command=show_compiler).pack(side="left", padx=3)
    ctk.CTkButton(top_frame, text="Editor", width=120, command=show_editor).pack(side="left", padx=3)
    ctk.CTkButton(top_frame, text="Syntax", width=120, command=show_syntax).pack(side="left", padx=3)
    ctk.CTkButton(top_frame, text="Output", width=120, command=show_output_tab).pack(side="left", padx=3)

    bottom_frame = ctk.CTkFrame(settings_win, fg_color="transparent")
    bottom_frame.pack(fill="x", pady=20)

    def save_settings():
        if output_text_color_entry:
            settings["output_text_color"] = output_text_color_entry.get()
        if output_bg_color_entry:
            settings["output_bg_color"] = output_bg_color_entry.get()
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        apply_settings_to_ui(settings)
        settings_win.destroy()
        messagebox.showinfo("Saved", "Settings saved permanently.")

    def cancel_settings():
        apply_settings_to_ui(original_settings)
        settings_win.destroy()

    def revert_to_defaults():
        if messagebox.askyesno("Revert", "Reset all settings to defaults?"):
            settings.update(DEFAULT_SETTINGS)
            font_size_slider.set(DEFAULT_SETTINGS["font_size"])
            font_family_combo.set(DEFAULT_SETTINGS["font_family"])
            cpp_std_combo.set(DEFAULT_SETTINGS["cpp_standard"])
            tab_width_slider.set(DEFAULT_SETTINGS["tab_width"])
            auto_save_switch.select() if DEFAULT_SETTINGS["auto_save"] else auto_save_switch.deselect()
            show_cmd_switch.select() if DEFAULT_SETTINGS["show_compiler_cmd"] else show_cmd_switch.deselect()
            highlight_line_switch.select() if DEFAULT_SETTINGS["highlight_current_line"] else highlight_line_switch.deselect()
            syntax_switch.select() if DEFAULT_SETTINGS["syntax_highlighting"] else syntax_switch.deselect()
            show_system_fonts_switch.deselect()
            if output_show_system_switch:
                output_show_system_switch.deselect()
            if output_font_combo:
                output_font_combo.set(DEFAULT_SETTINGS["output_font_family"])
            if output_font_slider:
                output_font_slider.set(DEFAULT_SETTINGS["output_font_size"])
            if output_text_color_entry:
                output_text_color_entry.delete(0, "end")
                output_text_color_entry.insert(0, DEFAULT_SETTINGS["output_text_color"])
            if output_bg_color_entry:
                output_bg_color_entry.delete(0, "end")
                output_bg_color_entry.insert(0, DEFAULT_SETTINGS["output_bg_color"])
            if external_terminal_switch:
                external_terminal_switch.select() if DEFAULT_SETTINGS["use_external_terminal"] else external_terminal_switch.deselect()
            if DEFAULT_SETTINGS["current_syntax_file"] in available_syntaxes:
                syntax_combo.set(DEFAULT_SETTINGS["current_syntax_file"])
            update_font_lists()
            apply_settings_to_ui(DEFAULT_SETTINGS)

    ctk.CTkButton(bottom_frame, text="Save & Close", command=save_settings).pack(side="left", padx=10)
    ctk.CTkButton(bottom_frame, text="Revert to Defaults", command=revert_to_defaults).pack(side="left", padx=10)
    ctk.CTkButton(bottom_frame, text="Cancel", command=cancel_settings).pack(side="right", padx=10)

    spacer = ctk.CTkFrame(bottom_frame, fg_color="transparent")
    spacer.pack(fill="both", expand=True)

    ctk.CTkLabel(
        bottom_frame, 
        text="Changes apply instantly. Use Cancel to discard all changes.", 
        font=("Arial", 11), 
        text_color="gray"
    ).pack(pady=(0, 10))

    settings_win.protocol("WM_DELETE_WINDOW", cancel_settings)

# Keyboard Shortcuts
def bind_shortcut(sequence, func):
    app.bind_all(sequence, lambda e: (func(), "break")[1])

bind_shortcut("<Control-s>", save_current_tab)
bind_shortcut("<Control-Shift-s>", open_settings)
bind_shortcut("<Control-S>", open_settings)
bind_shortcut("<Control-o>", open_file)
bind_shortcut("<Control-t>", lambda: new_tab())
bind_shortcut("<Control-w>", close_current_tab)

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

app.after(100, update_line_numbers)

# Right Panel
right_frame = ctk.CTkFrame(paned, corner_radius=10)
right_frame.grid_rowconfigure(1, weight=1)
right_frame.grid_columnconfigure(0, weight=1)
paned.add(right_frame, minsize=250)

def run_code():
    global process

    if active_tab is None:
        messagebox.showwarning("No File", "No active file to run.")
        return

    tab = tabs[active_tab]

    if tab["content"] != tab["saved_content"]:
        if not save_current_tab():
            return

    if tab["path"] is None:
        messagebox.showwarning("Save Required", "Please save the file before running.")
        return

    source_file = os.path.abspath(tab["path"])
    output_exe = os.path.splitext(source_file)[0] + ".exe"

    # Check if program is still running
    if os.path.exists(output_exe):
        try:
            os.remove(output_exe)
        except PermissionError:
            messagebox.showerror(
                "Program Still Running",
                "The previous program is still running.\n\n"
                "Close the external terminal or finish the program before running again."
            )
            return

    bundled_compiler = os.path.join("compilers", "mingw64", "bin", "g++.exe")
    if not os.path.exists(bundled_compiler):
        messagebox.showerror("Compiler Missing", "Bundled g++.exe not found!")
        return

    compiler_path = os.path.abspath(bundled_compiler)
    mingw_bin_dir = os.path.dirname(compiler_path)

    env = os.environ.copy()
    env["PATH"] = mingw_bin_dir + os.pathsep + env.get("PATH", "")

    compile_cmd = [
        compiler_path,
        source_file,
        "-o", output_exe,
        f"-std=c++{settings['cpp_standard']}"
    ]

    output_box.configure(state="normal")
    output_box.delete("1.0", "end")

    if settings.get("show_compiler_cmd", True):
        output_box.insert("end", "COMPILING:\n" + " ".join(compile_cmd) + "\n\n")

    output_box.insert("end", "⏳ Compiling...\n")
    output_box.configure(state="disabled")
    output_box.update()

    def compile_and_run():
        try:
            result = subprocess.run(
                compile_cmd,
                capture_output=True,
                text=True,
                cwd=os.path.dirname(source_file),
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )

            output_box.configure(state="normal")

            if result.returncode != 0:
                output_box.insert("end", "❌ COMPILATION FAILED\n\n")
                output_box.insert("end", result.stderr or "Unknown error\n")
                output_box.insert("end", f"\nReturn code: {result.returncode}\n")
                output_box.configure(state="disabled")
                return

            output_box.insert("end", "✓ Compilation successful\n\n")
            output_box.configure(state="disabled")
            output_box.update()

            # Check if code uses input (cin, scanf, getline, etc.)
            code_content = tab["content"].lower()
            uses_input = any(keyword in code_content for keyword in [
                'cin', 'scanf', 'getline', 'getchar', 'gets'
            ])

            # Always use external terminal if enabled OR if program uses input
            if settings.get("use_external_terminal", False) or uses_input:
                output_box.configure(state="normal")
                if uses_input and not settings.get("use_external_terminal", False):
                    output_box.insert("end", "⚠️ Program requires input - launching in external terminal...\n")
                else:
                    output_box.insert("end", "Launching in external terminal...\n")
                output_box.configure(state="disabled")

                subprocess.Popen(
                    ["cmd", "/k", output_exe],
                    cwd=os.path.dirname(source_file),
                    env=env,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                return

            # Run in-app without input (for output-only programs)
            output_box.configure(state="normal")
            output_box.insert("end", "─" * 60 + "\n")
            output_box.insert("end", "PROGRAM OUTPUT\n")
            output_box.insert("end", "─" * 60 + "\n\n")
            output_box.configure(state="disabled")
            output_box.update()

            process = subprocess.Popen(
                [output_exe],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=os.path.dirname(source_file),
                env=env,
                bufsize=1
            )

            def reader():
                try:
                    for line in process.stdout:
                        app.after(0, lambda l=line: update_output(l))
                    
                    process.wait()
                    app.after(0, lambda: finish_output(process.returncode))
                except Exception as e:
                    app.after(0, lambda: update_output(f"\n❌ Error: {e}\n"))
            
            def update_output(text):
                output_box.configure(state="normal")
                output_box.insert("end", text)
                output_box.see("end")
                output_box.configure(state="disabled")
            
            def finish_output(returncode):
                output_box.configure(state="normal")
                output_box.insert("end", f"\n{'─' * 60}\n")
                output_box.insert("end", f"Program finished (exit code {returncode})\n")
                output_box.configure(state="disabled")

            threading.Thread(target=reader, daemon=True).start()

        except Exception as e:
            output_box.configure(state="normal")
            output_box.insert("end", f"\n❌ Error: {e}\n")
            output_box.configure(state="disabled")

    threading.Thread(target=compile_and_run, daemon=True).start()


run_button = ctk.CTkButton(right_frame, text="Run", font=("Arial", 16), command=run_code)
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

output_box.configure(
    font=(settings["output_font_family"], settings["output_font_size"]),
    fg=settings["output_text_color"],
    bg=settings["output_bg_color"]
)

app.mainloop()
