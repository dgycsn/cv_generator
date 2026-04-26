import tkinter as tk
from tkinter import filedialog, ttk
import json
import sys
import threading
import time
from pathlib import Path

CONFIG_FILE = Path.home() / ".myapp" / "config.json"


# ── Config helpers ────────────────────────────────────────────────────────────

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}

def save_config(data):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f)


# ── File/folder dialog helpers ────────────────────────────────────────────────

def browse_directory(entry_widget, config, config_key):
    last_dir = config.get(config_key)
    initial = last_dir if last_dir and Path(last_dir).exists() else None
    directory = filedialog.askdirectory(title="Select folder", initialdir=initial)
    if directory:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, directory)
        config[config_key] = directory
        save_config(config)

def browse_file(entry_widget, config, config_key, filetypes=None):
    last_path = config.get(config_key)
    initial_dir = None
    if last_path:
        parent = Path(last_path).parent
        if parent.exists():
            initial_dir = str(parent)
    filepath = filedialog.askopenfilename(
        title="Select file",
        initialdir=initial_dir,
        filetypes=filetypes or [("All files", "*.*")]
    )
    if filepath:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, filepath)
        config[config_key] = filepath
        save_config(config)


# ── Pages ─────────────────────────────────────────────────────────────────────

def build_page1(root, config, on_continue):
    frame = tk.Frame(root)
    frame.columnconfigure(1, weight=1)
    pad = {"padx": 10, "pady": 4}

    tk.Label(frame, text="Step 1: Configuration", font=("", 12, "bold")).grid(
        row=0, column=0, columnspan=3, pady=(10, 5))

    def add_field(row, label, var, browse_fn=None):
        tk.Label(frame, text=label).grid(row=row, column=0, sticky="w", **pad)
        tk.Entry(frame, textvariable=var, width=40).grid(row=row, column=1, sticky="ew", **pad)
        if browse_fn:
            tk.Button(frame, text="📂", command=browse_fn).grid(row=row, column=2, padx=(0, 10))

    def get_entry(row):
        return frame.grid_slaves(row=row, column=1)[0]

    job_link_var      = tk.StringVar(value=config.get("job_link", ""))
    template_var      = tk.StringVar(value=config.get("template", ""))
    cl_template_var   = tk.StringVar(value=config.get("cl_template", ""))
    config_folder_var = tk.StringVar(value=config.get("config_folder", ""))
    output_folder_var = tk.StringVar(value=config.get("output_folder", ""))
    filename_var      = tk.StringVar(value=config.get("filename", ""))

    gen_cv_var = tk.BooleanVar(value=config.get("gen_cv", True))
    gen_cl_var = tk.BooleanVar(value=config.get("gen_cl", False))

    add_field(1, "Job URL:",         job_link_var)
    add_field(2, "CV template (.odt):", template_var,
              lambda: browse_file(get_entry(2), config, "template",
                                  filetypes=[("ODT files", "*.odt"), ("All files", "*.*")]))
    add_field(3, "Config folder:",   config_folder_var,
              lambda: browse_directory(get_entry(3), config, "config_folder"))
    add_field(4, "Output folder:",   output_folder_var,
              lambda: browse_directory(get_entry(4), config, "output_folder"))
    add_field(5, "Filename:",        filename_var)

    # ── Document selection checkboxes ─────────────────────────────────────────
    check_frame = tk.Frame(frame)
    check_frame.grid(row=6, column=0, columnspan=3, sticky="w", padx=10, pady=(6, 0))
    tk.Label(check_frame, text="Generate:").pack(side="left", padx=(0, 8))
    tk.Checkbutton(check_frame, text="CV",                 variable=gen_cv_var).pack(side="left", padx=4)
    tk.Checkbutton(check_frame, text="Motivation letter",  variable=gen_cl_var,
                   command=lambda: _toggle_cl_row()).pack(side="left", padx=4)

    # ── CL template row (shown/hidden based on checkbox) ──────────────────────
    cl_label  = tk.Label(frame, text="CL template (.odt):")
    cl_entry  = tk.Entry(frame, textvariable=cl_template_var, width=40)
    cl_button = tk.Button(frame, text="📂",
                          command=lambda: browse_file(cl_entry, config, "cl_template",
                                                      filetypes=[("ODT files", "*.odt"),
                                                                 ("All files", "*.*")]))

    def _toggle_cl_row():
        if gen_cl_var.get():
            cl_label.grid( row=7, column=0, sticky="w",  **pad)
            cl_entry.grid( row=7, column=1, sticky="ew", **pad)
            cl_button.grid(row=7, column=2, padx=(0, 10))
            root.geometry(f"560x{370}+{root.winfo_x()}+{root.winfo_y()}")
        else:
            cl_label.grid_remove()
            cl_entry.grid_remove()
            cl_button.grid_remove()
            root.geometry(f"560x{310}+{root.winfo_x()}+{root.winfo_y()}")

    # Show CL row immediately if it was previously enabled
    if gen_cl_var.get():
        _toggle_cl_row()

    error_label = tk.Label(frame, text="", fg="red")
    error_label.grid(row=8, column=1, sticky="w", padx=10)

    def on_continue_click():
        errors = []
        if not job_link_var.get().strip():      errors.append("Job URL is required")
        if not config_folder_var.get().strip(): errors.append("Config folder is required")
        if not output_folder_var.get().strip(): errors.append("Output folder is required")
        if not filename_var.get().strip():      errors.append("Filename is required")
        if not gen_cv_var.get() and not gen_cl_var.get():
            errors.append("Select at least one document to generate")
        if gen_cv_var.get() and not template_var.get().strip():
            errors.append("CV template is required when generating a CV")
        if gen_cl_var.get() and not cl_template_var.get().strip():
            errors.append("CL template is required when generating a motivation letter")

        if errors:
            error_label.config(text="\n".join(errors))
            return

        error_label.config(text="")
        data = {
            "job_link":      job_link_var.get().strip(),
            "template":      template_var.get().strip(),
            "cl_template":   cl_template_var.get().strip(),
            "config_folder": config_folder_var.get().strip().rstrip("/") + "/",
            "output_folder": output_folder_var.get().strip(),
            "filename":      filename_var.get().strip(),
            "gen_cv":        gen_cv_var.get(),
            "gen_cl":        gen_cl_var.get(),
        }
        config.update(data)
        save_config(config)
        on_continue(data)

    tk.Button(frame, text="Continue →", width=15, command=on_continue_click).grid(
        row=9, column=1, pady=10)

    return frame


def build_page2(root, pipeline_fn, on_done, gen_cv, gen_cl):
    """
    Page 2: Progress bar while pipeline runs in a background thread.
    Steps are built dynamically based on which documents are being generated.

    Returns (frame, stop_event).
    """
    STEPS = ["Extracting job page blocks"]

    if gen_cv:
        STEPS += [
            "Selecting experience",
            "Selecting skills",
            "Generating summary",
        ]
    if gen_cl:
        STEPS += [
            "Researching company",
            "Generating motivation letter",
        ]

    STEPS += ["Saving documents"]

    N = len(STEPS)

    frame = tk.Frame(root)
    frame.columnconfigure(0, weight=1)
    pad = {"padx": 20, "pady": 4}

    tk.Label(frame, text="Step 2: Processing", font=("", 12, "bold")).grid(
        row=0, column=0, pady=(16, 8))

    step_var     = tk.StringVar(value=STEPS[0])
    progress_var = tk.DoubleVar(value=0)
    counter_var  = tk.StringVar(value=f"0 / {N}")
    timer_var    = tk.StringVar(value="Elapsed: 0s")
    error_var    = tk.StringVar(value="")

    tk.Label(frame, textvariable=step_var, anchor="center").grid(
        row=1, column=0, sticky="ew", **pad)

    bar = ttk.Progressbar(frame, variable=progress_var, maximum=N, length=420)
    bar.grid(row=2, column=0, sticky="ew", **pad)

    tk.Label(frame, textvariable=counter_var, fg="grey").grid(row=3, column=0, **pad)
    tk.Label(frame, textvariable=timer_var,   fg="grey").grid(row=4, column=0, **pad)
    tk.Label(frame, textvariable=error_var, fg="red", wraplength=420,
             justify="left").grid(row=5, column=0, **pad)

    start_time = time.time()
    _running   = [True]
    _destroyed = [False]
    stop_event = threading.Event()

    frame.bind("<Destroy>", lambda e: _destroyed.__setitem__(0, True))

    def safe_after(fn):
        if not _destroyed[0]:
            root.after(0, fn)

    def tick():
        if _running[0] and not _destroyed[0]:
            elapsed = int(time.time() - start_time)
            timer_var.set(f"Elapsed: {elapsed}s")
            root.after(1000, tick)

    tick()

    def progress_callback(step_index, label=None):
        """Call BEFORE each step to update the label and advance the bar."""
        if _destroyed[0]:
            return
        display = label or (STEPS[step_index] if step_index < N else "Finishing…")
        safe_after(lambda d=display, i=step_index: _update(d, i))

    def _update(display, step_index):
        if _destroyed[0]:
            return
        step_var.set(display)
        progress_var.set(step_index + 1)
        counter_var.set(f"{step_index + 1} / {N}")

    def run_pipeline():
        try:
            result = pipeline_fn(progress_callback, stop_event)
        except InterruptedError:
            return
        except Exception as e:
            _running[0] = False
            safe_after(lambda err=e: error_var.set(f"Error: {err}"))
            return

        _running[0] = False
        elapsed = int(time.time() - start_time)
        safe_after(lambda: timer_var.set(f"Completed in {elapsed}s ✓"))
        safe_after(lambda: on_done(result))

    threading.Thread(target=run_pipeline, daemon=True).start()

    return frame, stop_event


def build_page3(root, result):
    """
    Page 3: Scrollable summary of what was generated.
    """
    frame = tk.Frame(root)
    frame.columnconfigure(0, weight=1)
    pad = {"padx": 20, "pady": 4}

    tk.Label(frame, text="✅ Complete!", font=("", 13, "bold"), fg="#2a7a2a").grid(
        row=0, column=0, pady=(14, 6))

    if result.get("_finish_error"):
        tk.Label(frame, text=f"⚠ Error: {result['_finish_error']}",
                 fg="red", wraplength=500, justify="left").grid(
            row=0, column=0, pady=(14, 6))

    info_frame = tk.LabelFrame(frame, text="Job details", padx=10, pady=6)
    info_frame.grid(row=1, column=0, sticky="ew", **pad)
    info_frame.columnconfigure(1, weight=1)

    def kv(parent, row, key, value):
        tk.Label(parent, text=key, font=("", 9, "bold"), anchor="w").grid(
            row=row, column=0, sticky="w", padx=(0, 10))
        tk.Label(parent, text=value, anchor="w").grid(row=row, column=1, sticky="w")

    kv(info_frame, 0, "Job title:", result.get("job_title", "—"))
    kv(info_frame, 1, "Company:",   result.get("company_name", "—"))
    kv(info_frame, 2, "Language:",  result.get("language", "—"))

    # Show which documents were generated
    docs = []
    if result.get("gen_cv"):  docs.append("CV")
    if result.get("gen_cl"):  docs.append("Motivation letter")
    kv(info_frame, 3, "Generated:", ", ".join(docs) if docs else "—")

    canvas    = tk.Canvas(frame, borderwidth=0, highlightthickness=0)
    scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.grid(row=2, column=0, sticky="nsew", padx=(20, 0), pady=4)
    scrollbar.grid(row=2, column=1, sticky="ns", pady=4)
    frame.rowconfigure(2, weight=1)

    inner = tk.Frame(canvas)
    canvas_window = canvas.create_window((0, 0), window=inner, anchor="nw")
    inner.columnconfigure(0, weight=1)

    def on_inner_resize(e):
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfig(canvas_window, width=canvas.winfo_width())

    inner.bind("<Configure>", on_inner_resize)
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))

    def on_mousewheel(e):
        canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
    canvas.bind_all("<MouseWheel>", on_mousewheel)

    def add_section(parent, row, title, data_dict):
        section = tk.LabelFrame(parent, text=title, padx=10, pady=6)
        section.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        section.columnconfigure(0, weight=1)

        if not data_dict:
            tk.Label(section, text="(none)", fg="grey").grid(row=0, column=0, sticky="w")
            return

        r = 0
        for block_name, block_data in data_dict.items():
            tk.Label(section, text=block_name, font=("", 9, "bold"), anchor="w").grid(
                row=r, column=0, sticky="w", pady=(4 if r > 0 else 0, 2))
            r += 1
            if not block_data:
                tk.Label(section, text="  (none selected)", fg="grey").grid(
                    row=r, column=0, sticky="w")
                r += 1
                continue
            for num, text in block_data.items():
                tk.Label(section, text=f"  [{num}] {text}", anchor="w",
                         justify="left", wraplength=460).grid(
                    row=r, column=0, sticky="ew")
                r += 1

    inner_row = 0
    if result.get("gen_cv"):
        add_section(inner, inner_row, "Selected experience", result.get("selected_experience", {}))
        inner_row += 1
        add_section(inner, inner_row, "Selected skills",     result.get("selected_skill", {}))
        inner_row += 1
    if result.get("gen_cl"):
        # Show the generated paragraphs in a simple label frame
        cl_section = tk.LabelFrame(inner, text="Motivation letter", padx=10, pady=6)
        cl_section.grid(row=inner_row, column=0, sticky="ew", pady=(0, 8))
        cl_section.columnconfigure(0, weight=1)
        para_keys = ["OPENING_PARAGRAPH", "EXPERIENCE_PARAGRAPH",
                     "COMPANY_PARAGRAPH",  "CLOSING_PARAGRAPH"]
        for i, key in enumerate(para_keys):
            text = result.get(key, "")
            if text:
                tk.Label(cl_section, text=key.replace("_", " ").title(),
                         font=("", 9, "bold"), anchor="w").grid(
                    row=i*2, column=0, sticky="w", pady=(4 if i > 0 else 0, 2))
                tk.Label(cl_section, text=text, anchor="w",
                         justify="left", wraplength=460).grid(
                    row=i*2+1, column=0, sticky="ew")

    docs_str = " and ".join(docs) if docs else "document"
    tk.Label(frame, text=f"{docs_str} saved. You may close this window.",
             fg="grey", font=("", 9)).grid(row=3, column=0, pady=(4, 10))

    return frame


# ── Main entry point ──────────────────────────────────────────────────────────

def run_dialog(pipeline_fn, finish_fn, initial_data=None):
    """
    Launch the full 3-page dialog flow.

    Args:
        pipeline_fn : callable(dialog_data, progress_callback, stop_event) -> dict
        finish_fn   : callable(result) -> None
                      Called on the main thread after pipeline completes.
        initial_data: optional dict to pre-fill page 1 fields.
    """
    config = load_config()
    if initial_data:
        config.update(initial_data)

    root = tk.Tk()
    root.title("CV / CL Generator")
    root.resizable(True, True)

    root.update_idletasks()
    w, h = 560, 310
    x = (root.winfo_screenwidth() - w) // 2
    y = 40
    root.geometry(f"{w}x{h}+{x}+{y}")
    root.update()

    root.lift()
    root.focus_force()
    root.attributes("-topmost", True)
    root.after(100, lambda: root.attributes("-topmost", False))

    current_frame = {"ref": None}
    stop_ref      = {"event": None}

    def show_frame(new_frame):
        if current_frame["ref"] is not None:
            current_frame["ref"].pack_forget()
        new_frame.pack(fill="both", expand=True)
        current_frame["ref"] = new_frame

    def on_close():
        if stop_ref["event"] is not None:
            stop_ref["event"].set()
        root.quit()
        root.destroy()
        sys.exit(0)

    root.protocol("WM_DELETE_WINDOW", on_close)

    def on_page1_continue(data):
        def wrapped_pipeline(progress_callback, stop_event):
            return pipeline_fn(data, progress_callback, stop_event)

        def on_pipeline_done(result):
            try:
                finish_fn(result)
            except Exception as e:
                import traceback
                traceback.print_exc()
                # Show error on page 2's error label if still visible
                safe_show_error = getattr(on_pipeline_done, "_error_cb", None)
                print(f"Document generation error: {e}")
                # Still advance to page 3 so the user sees what was selected,
                # but add the error to result so page 3 can display it
                result["_finish_error"] = str(e)
            root.geometry(f"560x500+{x}+{y}")
            page3 = build_page3(root, result)
            show_frame(page3)

        page2, stop_event = build_page2(
            root, wrapped_pipeline, on_done=on_pipeline_done,
            gen_cv=data.get("gen_cv", True),
            gen_cl=data.get("gen_cl", False),
        )
        stop_ref["event"] = stop_event
        show_frame(page2)

    page1 = build_page1(root, config, on_continue=on_page1_continue)
    show_frame(page1)

    root.mainloop()


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":

    def dummy_pipeline(dialog_data, progress_callback, stop_event):
        def check():
            if stop_event.is_set():
                raise InterruptedError("Cancelled.")

        progress_callback(0); time.sleep(2); check()
        progress_callback(1); time.sleep(2); check()
        progress_callback(2); time.sleep(2); check()
        progress_callback(3); time.sleep(1.5); check()

        return {
            **dialog_data,
            "job_title":    "Software Engineer",
            "company_name": "Acme Corp",
            "language":     "en",
            "gen_cv":       dialog_data.get("gen_cv", True),
            "gen_cl":       dialog_data.get("gen_cl", False),
            "selected_experience": {
                "EXPERIENCE_1": {"1": "Built scalable APIs", "2": "Led team of 5 engineers"},
                "EXPERIENCE_2": {"1": "Reduced latency by 40%"},
                "EXPERIENCE_3": {},
                "EDUCATION_1":  {"2": "Completed advanced coursework in ML and statistics"},
            },
            "selected_skill": {
                "SKILLS_1": {"1": "Python", "2": "Docker"},
                "SKILLS_2": {},
            },
            "OPENING_PARAGRAPH":    "Sample opening paragraph text.",
            "EXPERIENCE_PARAGRAPH": "Sample experience paragraph text.",
            "COMPANY_PARAGRAPH":    "Sample company paragraph text.",
            "CLOSING_PARAGRAPH":    "Sample closing paragraph text.",
        }

    def dummy_finish(result):
        print("finish_fn called — would generate documents here.")
        time.sleep(0.3)

    run_dialog(pipeline_fn=dummy_pipeline, finish_fn=dummy_finish)