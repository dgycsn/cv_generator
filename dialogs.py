import tkinter as tk
from tkinter import filedialog
import json
import sys
from pathlib import Path

# Path to the config file that persists user inputs between sessions
CONFIG_FILE = Path.home() / ".myapp" / "config.json"


# ── Config helpers ────────────────────────────────────────────────────────────

def load_config():
    """Load saved config from disk. Returns empty dict if file doesn't exist."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}

def save_config(data):
    """Save config dict to disk, creating directories if needed."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f)


# ── File dialog helper ────────────────────────────────────────────────────────

def browse_directory(entry_widget, config, config_key):
    """
    Open a folder picker and insert the selected path into entry_widget.
    Remembers the last visited directory via config_key in config.
    """
    last_dir = config.get(config_key)
    initial = last_dir if last_dir and Path(last_dir).exists() else None

    directory = filedialog.askdirectory(title="Select folder", initialdir=initial)

    if directory:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, directory)
        config[config_key] = directory
        save_config(config)


# ── Pages ─────────────────────────────────────────────────────────────────────

def build_page1(root, config, on_continue):
    """
    Build and return page 1 frame (Configuration).

    Args:
        root:        the root Tk window
        config:      the loaded config dict (used to pre-fill fields)
        on_continue: callback function called with a dict of values when
                     Continue is pressed. Signature: on_continue(data: dict)

    Returns:
        frame: the page1 Frame (not yet packed)

    Example:
        def handle_page1(data):
            print(data["url"], data["input_dir"])

        page1 = build_page1(root, config, on_continue=handle_page1)
        page1.pack(fill="both", expand=True)
    """
    frame = tk.Frame(root)
    frame.columnconfigure(1, weight=1)

    pad = {"padx": 10, "pady": 4}

    tk.Label(frame, text="Step 1: Configuration", font=("", 12, "bold")).grid(
        row=0, column=0, columnspan=3, pady=(10, 5))

    def add_field(row, label, var, browse_fn=None):
        """Add a labeled entry row, with an optional folder browse button."""
        tk.Label(frame, text=label).grid(row=row, column=0, sticky="w", **pad)
        tk.Entry(frame, textvariable=var, width=40).grid(row=row, column=1, sticky="ew", **pad)
        if browse_fn:
            tk.Button(frame, text="📂", command=browse_fn).grid(row=row, column=2, padx=(0, 10))

    # StringVars pre-filled from saved config
    url_var         = tk.StringVar(value=config.get("url", ""))
    input_dir_var   = tk.StringVar(value=config.get("input_dir", ""))
    output_dir_var  = tk.StringVar(value=config.get("output_dir", ""))
    json_dir_var    = tk.StringVar(value=config.get("json_dir", ""))
    output_name_var = tk.StringVar(value=config.get("output_name", ""))

    add_field(1, "URL:",              url_var)
    add_field(2, "Input directory:",  input_dir_var,  lambda: browse_directory(frame.grid_slaves(row=2, column=1)[0], config, "input_dir"))
    add_field(3, "Output directory:", output_dir_var, lambda: browse_directory(frame.grid_slaves(row=3, column=1)[0], config, "output_dir"))
    add_field(4, "JSON directory:",   json_dir_var,   lambda: browse_directory(frame.grid_slaves(row=4, column=1)[0], config, "json_dir"))
    add_field(5, "Output name:",      output_name_var)

    # Error label created once, updated in place
    error_label = tk.Label(frame, text="", fg="red")
    error_label.grid(row=6, column=1, sticky="w", padx=10)

    def on_continue_click():
        """Validate all fields, save config, then call on_continue with the data."""
        errors = []
        if not url_var.get().strip():         errors.append("URL is required")
        if not input_dir_var.get().strip():   errors.append("Input directory is required")
        if not output_dir_var.get().strip():  errors.append("Output directory is required")
        if not json_dir_var.get().strip():    errors.append("JSON directory is required")
        if not output_name_var.get().strip(): errors.append("Output name is required")

        if errors:
            error_label.config(text="\n".join(errors))
            return

        error_label.config(text="")

        # Collect all values into a dict
        data = {
            "url":         url_var.get().strip(),
            "input_dir":   input_dir_var.get().strip(),
            "output_dir":  output_dir_var.get().strip(),
            "json_dir":    json_dir_var.get().strip(),
            "output_name": output_name_var.get().strip(),
        }

        # Persist values for next run
        config.update(data)
        save_config(config)

        # Hand off data to whoever called build_page1()
        on_continue(data)

    tk.Button(frame, text="Continue →", width=15, command=on_continue_click).grid(
        row=7, column=1, pady=10)

    return frame


def build_page2(root, config, data, on_back):
    """
    Build and return page 2 frame. Add your step 2 widgets here.

    Args:
        root:    the root Tk window
        config:  the loaded config dict
        data:    dict of values passed in from page 1 (or any previous page)
        on_back: callback called when Back is pressed (no arguments)

    Returns:
        frame: the page2 Frame (not yet packed)

    Example:
        page2 = build_page2(root, config, data=page1_data, on_back=go_back)
        page2.pack(fill="both", expand=True)
    """
    frame = tk.Frame(root)
    frame.columnconfigure(0, weight=1)

    pad = {"padx": 10, "pady": 4}

    tk.Label(frame, text="Step 2: Coming soon...", font=("", 12, "bold")).grid(
        row=0, column=0, columnspan=2, pady=(10, 5))

    # Example: display data received from page 1
    tk.Label(frame, text=f"URL: {data.get('url', '')}").grid(row=1, column=0, sticky="w", **pad)

    # Add your page 2 widgets below this line
    # ...

    def on_back_click():
        on_back()

    tk.Button(frame, text="← Back", width=10, command=on_back_click).grid(
        row=99, column=0, pady=10, sticky="w", padx=10)

    return frame


# ── Main ──────────────────────────────────────────────────────────────────────

def run_dialog(initial_data=None):
    """
    Launch the dialog window.

    Args:
        initial_data: optional dict to pre-fill fields, overrides saved config.
                      Useful when calling from another script.
                      Example: {"url": "https://example.com", "output_name": "run1"}

    Returns:
        result: dict of final submitted values, or None if window was closed.

    Example (calling from another script):
        from dialog import run_dialog

        result = run_dialog(initial_data={"url": "https://example.com"})
        if result:
            print(result["url"], result["output_dir"])
    """
    config = load_config()

    # Merge any externally provided data into config (overrides saved values)
    if initial_data:
        config.update(initial_data)

    # This will hold the final result once the user submits
    result = {"data": None}

    root = tk.Tk()
    root.title("Job Application")
    root.resizable(True, True)

    # ── Window positioning ────────────────────────────────────────────────────
    root.update_idletasks()
    window_width  = 500
    window_height = 280
    x = (root.winfo_screenwidth() - window_width) // 2
    y = 40
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    root.update()

    root.lift()
    root.focus_force()
    root.attributes("-topmost", True)
    root.after(100, lambda: root.attributes("-topmost", False))

    # ── Close handler ─────────────────────────────────────────────────────────
    def on_close():
        root.quit()
        root.destroy()
        sys.exit(0)
    root.protocol("WM_DELETE_WINDOW", on_close)

    # ── Page switching logic ──────────────────────────────────────────────────
    # current_frame tracks whichever frame is currently visible
    current_frame = {"ref": None}

    def show_frame(new_frame):
        """Hide the current frame and show new_frame."""
        if current_frame["ref"] is not None:
            current_frame["ref"].pack_forget()
        new_frame.pack(fill="both", expand=True)
        current_frame["ref"] = new_frame

    # ── Wire pages together ───────────────────────────────────────────────────

    # page2 is defined as a variable so go_back can reference it
    page2_ref = {"ref": None}

    def on_page1_continue(data):
        """Called when page 1 Continue is pressed. Receives page 1 data."""
        # Build page 2 fresh with the data from page 1
        page2 = build_page2(root, config, data=data, on_back=on_go_back)
        page2_ref["ref"] = page2
        show_frame(page2)

        # Store result so it's available if the user submits on page 2
        result["data"] = data

    def on_go_back():
        """Called when page 2 Back is pressed. Returns to page 1."""
        show_frame(page1)

    # Build page 1 and show it immediately
    page1 = build_page1(root, config, on_continue=on_page1_continue)
    show_frame(page1)

    root.mainloop()

    # Return the final collected data to the caller (if any)
    return result["data"]


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Running this file directly
    result = run_dialog()
    print("Dialog result:", result)