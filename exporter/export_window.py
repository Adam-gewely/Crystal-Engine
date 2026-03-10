"""Crystal Engine - Export dialog."""
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from engine.utils import center_window


class ExportWindow(tk.Toplevel):
    """Export dialog with format options."""

    def __init__(self, parent, project: dict):
        super().__init__(parent)
        self.title("Export Project")
        self.resizable(False, False)
        center_window(self, 480, 360)
        self.grab_set()
        self._project = project
        self._build()

    def _build(self):
        ttk.Label(self, text="Export Project",
                  font=("Segoe UI", 14, "bold"), padding=(20, 16)).pack()
        ttk.Separator(self).pack(fill=X, padx=20)

        f = ttk.Frame(self, padding=20)
        f.pack(fill=BOTH, expand=True)

        ttk.Label(f, text="Export Format", font=("Segoe UI", 10, "bold")).pack(
            anchor=W, pady=(0, 8))

        self._format_var = tk.StringVar(value="python")

        formats = [
            ("python", "Export as Python Project",
             "A standalone Pygame project with assets extracted to disk."),
        ]

        for val, label, desc in formats:
            row = ttk.Frame(f, padding=(8, 6), bootstyle="secondary")
            row.pack(fill=X, pady=4)
            ttk.Radiobutton(row, text=label, variable=self._format_var,
                            value=val, bootstyle="toolbutton").pack(
                            side=LEFT, anchor=W)
            ttk.Label(row, text=desc, font=("Segoe UI", 8),
                      foreground="#aaa", wraplength=340).pack(
                      side=LEFT, padx=8, anchor=W)

        ttk.Label(f, text="Output Directory", font=("Segoe UI", 10, "bold")).pack(
            anchor=W, pady=(16, 4))

        dir_row = ttk.Frame(f)
        dir_row.pack(fill=X)
        self._dir_var = tk.StringVar()
        ttk.Entry(dir_row, textvariable=self._dir_var).pack(side=LEFT, fill=X, expand=True)
        ttk.Button(dir_row, text="…", bootstyle="secondary", width=3,
                   command=self._browse).pack(side=LEFT, padx=(4, 0))

        ttk.Separator(self).pack(fill=X, padx=20, pady=8)

        btn_row = ttk.Frame(self, padding=(20, 0))
        btn_row.pack(fill=X)
        ttk.Button(btn_row, text="Cancel",
                   bootstyle="secondary-outline",
                   command=self.destroy).pack(side=LEFT)
        ttk.Button(btn_row, text="Export ▸",
                   bootstyle="success",
                   command=self._export).pack(side=RIGHT)

    def _browse(self):
        d = filedialog.askdirectory(title="Select Output Directory")
        if d:
            self._dir_var.set(d)

    def _export(self):
        fmt = self._format_var.get()
        out = self._dir_var.get().strip()
        if not out or not os.path.isdir(out):
            messagebox.showwarning("Missing", "Please select a valid output directory.",
                                   parent=self)
            return

        try:
            if fmt == "python":
                from exporter.python_exporter import PythonExporter
                exp  = PythonExporter(self._project)
                path = exp.export(out)
                messagebox.showinfo("Export Complete",
                                    f"Project exported to:\\n{path}",
                                    parent=self)
                self.destroy()
        except Exception as ex:
            messagebox.showerror("Export Error", str(ex), parent=self)
