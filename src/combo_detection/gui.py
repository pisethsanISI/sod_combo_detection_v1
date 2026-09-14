"""Tkinter desktop GUI (installed as the windowed `combo-detect-gui`
command -- no console window, no command line needed after launch).

Point-and-click front end over the exact same pipeline.run_detection()
that `combo-detect` uses -- browse to your role/user CSVs (fresh off a new
SAP export), click Run, get both reports. Remembers your last-used paths
in a small per-user settings file so re-running after the next export
doesn't mean re-browsing everything from scratch.
"""

import json
import os
import sys
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, scrolledtext, ttk

from .pipeline import run_detection
from .sample_data import any_sample_data_paths

# src/combo_detection/gui.py -> src/combo_detection -> src -> project root
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SETTINGS_PATH = os.path.join(os.path.expanduser("~"), ".combo_detection_gui_settings.json")

DEFAULT_RULESET = os.path.join(_PROJECT_ROOT, "ruleset", "sap_sod_combination_ruleset.json")
DEFAULT_OUTPUT_PDF = os.path.join(_PROJECT_ROOT, "output", "sod_combination_report.pdf")
DEFAULT_OUTPUT_EXCEL = os.path.join(_PROJECT_ROOT, "output", "sod_combination_report.xlsx")

FIELD_KEYS = ["ruleset", "role_tcodes", "user_roles", "composite_roles", "output_pdf", "output_excel", "generated_for"]


def _load_settings():
    try:
        with open(_SETTINGS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}


def _save_settings(values):
    try:
        with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(values, f, indent=2)
    except OSError:
        pass  # best-effort -- never fail a run over a settings file we can't write


class App(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.master = master
        master.title("SOD Combination Ruleset Detector")
        master.minsize(720, 580)
        self.grid(sticky="nsew")
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)

        settings = _load_settings()
        self.vars = {key: tk.StringVar() for key in FIELD_KEYS}
        self.vars["ruleset"].set(settings.get("ruleset") or DEFAULT_RULESET)
        self.vars["role_tcodes"].set(settings.get("role_tcodes", ""))
        self.vars["user_roles"].set(settings.get("user_roles", ""))
        self.vars["composite_roles"].set(settings.get("composite_roles", ""))
        self.vars["output_pdf"].set(settings.get("output_pdf") or DEFAULT_OUTPUT_PDF)
        self.vars["output_excel"].set(settings.get("output_excel") or DEFAULT_OUTPUT_EXCEL)
        self.vars["generated_for"].set(settings.get("generated_for", ""))

        self._build_widgets()

        for key in ("role_tcodes", "user_roles", "composite_roles"):
            self.vars[key].trace_add("write", lambda *_args: self._update_sample_data_warning())
        self._update_sample_data_warning()

    def _build_widgets(self):
        self.columnconfigure(1, weight=1)

        self._path_row(0, "Combination ruleset (JSON)", "ruleset", [("JSON files", "*.json")])
        self._path_row(1, "Role -> T-code CSV", "role_tcodes", [("CSV files", "*.csv")])
        self._path_row(2, "User -> Role CSV", "user_roles", [("CSV files", "*.csv")])
        self._path_row(3, "Composite roles CSV (optional)", "composite_roles", [("CSV files", "*.csv")])

        self.sample_warning = ttk.Label(
            self,
            text=(
                "⚠ Using bundled SAMPLE data (data/sample_*.csv) -- the synthetic 2-user demo dataset, "
                "not a real SAP export. Findings from this run are not real."
            ),
            foreground="#8A1F1F",
            wraplength=640,
            justify="left",
        )
        self.sample_warning.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(4, 0))
        self.sample_warning.grid_remove()

        ttk.Label(self, text="Generated for (optional label)").grid(row=5, column=0, sticky="w", pady=(8, 2))
        ttk.Entry(self, textvariable=self.vars["generated_for"]).grid(
            row=5, column=1, columnspan=2, sticky="ew", pady=(8, 2)
        )

        self._path_row(6, "Output PDF", "output_pdf", [("PDF files", "*.pdf")], save=True, default_ext=".pdf")
        self._path_row(7, "Output Excel", "output_excel", [("Excel files", "*.xlsx")], save=True, default_ext=".xlsx")

        button_row = ttk.Frame(self)
        button_row.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(12, 6))
        self.run_button = ttk.Button(button_row, text="Run Detection", command=self._on_run)
        self.run_button.pack(side="left")
        ttk.Button(button_row, text="Open Output Folder", command=self._open_output_folder).pack(
            side="left", padx=(8, 0)
        )

        ttk.Label(self, text="Log").grid(row=9, column=0, sticky="w")
        self.log = scrolledtext.ScrolledText(self, height=16, state="disabled", wrap="word")
        self.log.grid(row=10, column=0, columnspan=3, sticky="nsew", pady=(2, 0))
        self.rowconfigure(10, weight=1)

    def _path_row(self, row, label, key, filetypes, save=False, default_ext=None):
        ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", pady=2)
        ttk.Entry(self, textvariable=self.vars[key]).grid(row=row, column=1, sticky="ew", pady=2, padx=(0, 4))
        command = (
            (lambda: self._browse_save(key, default_ext, filetypes))
            if save
            else (lambda: self._browse_open(key, filetypes))
        )
        ttk.Button(self, text="Browse...", command=command).grid(row=row, column=2, sticky="w", pady=2)

    def _browse_open(self, key, filetypes):
        initial = os.path.dirname(self.vars[key].get()) or _PROJECT_ROOT
        path = filedialog.askopenfilename(initialdir=initial, filetypes=[*filetypes, ("All files", "*.*")])
        if path:
            self.vars[key].set(path)

    def _browse_save(self, key, default_ext, filetypes):
        initial = os.path.dirname(self.vars[key].get()) or _PROJECT_ROOT
        path = filedialog.asksaveasfilename(
            initialdir=initial, defaultextension=default_ext, filetypes=[*filetypes, ("All files", "*.*")]
        )
        if path:
            self.vars[key].set(path)

    def _append_log(self, line):
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        self.master.update_idletasks()

    def _is_using_sample_data(self):
        return any_sample_data_paths(
            [self.vars["role_tcodes"].get(), self.vars["user_roles"].get(), self.vars["composite_roles"].get()],
            _PROJECT_ROOT,
        )

    def _update_sample_data_warning(self):
        if self._is_using_sample_data():
            self.sample_warning.grid()
        else:
            self.sample_warning.grid_remove()

    def _on_run(self):
        values = {key: var.get().strip() for key, var in self.vars.items()}
        if not values["role_tcodes"] or not values["user_roles"]:
            messagebox.showerror("Missing input", "Role -> T-code CSV and User -> Role CSV are both required.")
            return

        if self._is_using_sample_data() and not messagebox.askyesno(
            "Sample data detected",
            "One or more of the selected files is the bundled SAMPLE data "
            "(data/sample_*.csv) -- the synthetic 2-user demo dataset, not a "
            "real SAP export.\n\nRun anyway?",
            icon="warning",
        ):
            return

        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.run_button.configure(state="disabled")
        self.master.update_idletasks()

        try:
            summary = run_detection(
                values["ruleset"],
                values["role_tcodes"],
                values["user_roles"],
                values["composite_roles"] or None,
                values["output_pdf"],
                values["output_excel"],
                generated_for=values["generated_for"],
                log=self._append_log,
            )
        except FileNotFoundError as e:
            self._append_log(f"ERROR: file not found -- {e.filename}")
            messagebox.showerror("File not found", f"Could not find:\n{e.filename}")
            return
        except ValueError as e:
            self._append_log(f"ERROR: {e}")
            messagebox.showerror("Invalid input", str(e))
            return
        finally:
            self.run_button.configure(state="normal")

        _save_settings(values)
        messagebox.showinfo(
            "Detection complete",
            f"Rules: {summary['rule_count']} ({summary['manual_only_count']} manual-only)\n"
            f"Users resolved: {summary['user_count']}\n"
            f"Findings: {summary['finding_count']} across {len(summary['affected_users'])} user(s)\n\n"
            f"Reports written to:\n{values['output_pdf']}\n{values['output_excel']}",
        )

    def _open_output_folder(self):
        folder = os.path.dirname(self.vars["output_pdf"].get()) or _PROJECT_ROOT
        if not os.path.isdir(folder):
            messagebox.showwarning("Folder not found", f"{folder} doesn't exist yet -- run a detection first.")
            return
        if sys.platform == "win32":
            os.startfile(folder)
        else:
            webbrowser.open(folder)


def main(argv=None):
    root = tk.Tk()
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
