"""Crystal Engine - Variable manager dialog."""
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from engine.utils import center_window


class VariableEditor(tk.Toplevel):
    """Modal editor for global and screen-local variables."""

    def __init__(self, parent, project: dict, screen, callback):
        super().__init__(parent)
        self.title("Variables")
        self.resizable(True, True)
        w, h = 520, 480
        center_window(self, w, h)
        self.grab_set()

        self._project  = project
        self._screen   = screen
        self._callback = callback

        self._build()

    def _build(self):
        nb = ttk.Notebook(self)
        nb.pack(fill=BOTH, expand=True, padx=10, pady=10)

        self._global_frame = ttk.Frame(nb)
        nb.add(self._global_frame, text="Global Variables")
        self._local_frame = ttk.Frame(nb)
        nb.add(self._local_frame, text="Screen Variables")

        self._build_var_tab(self._global_frame, self._project.setdefault("global_vars", {}), "global")
        self._build_var_tab(self._local_frame,
                             self._screen.setdefault("variables", {}) if self._screen else {},
                             "local")

        ttk.Button(self, text="Done", bootstyle="success",
                   command=self._done).pack(pady=8)

    def _build_var_tab(self, parent, var_dict, scope):
        top = ttk.Frame(parent, padding=6)
        top.pack(fill=X)

        ttk.Label(top, text="Name", width=20).grid(row=0, column=0, sticky=W)
        ttk.Label(top, text="Default Value", width=20).grid(row=0, column=1, sticky=W)

        list_frame = ttk.Frame(parent, padding=(6, 0))
        list_frame.pack(fill=BOTH, expand=True)

        canvas = tk.Canvas(list_frame, highlightthickness=0)
        sb = ttk.Scrollbar(list_frame, orient=VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        canvas.pack(fill=BOTH, expand=True)

        rows_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=rows_frame, anchor="nw")
        rows_frame.bind("<Configure>",
                        lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        setattr(self, f"_{scope}_rows_frame", rows_frame)
        setattr(self, f"_{scope}_var_dict", var_dict)
        setattr(self, f"_{scope}_row_vars", [])

        for name, value in var_dict.items():
            self._add_var_row(scope, name, str(value))

        btn_bar = ttk.Frame(parent, padding=(6, 4))
        btn_bar.pack(fill=X)
        ttk.Button(btn_bar, text="+ Add Variable", bootstyle="primary-outline",
                   command=lambda s=scope: self._add_var_row(s)).pack(side=LEFT)

    def _add_var_row(self, scope, name="", value="0"):
        rows_frame = getattr(self, f"_{scope}_rows_frame")
        row_vars   = getattr(self, f"_{scope}_row_vars")

        row = len(row_vars)
        name_var  = tk.StringVar(value=name)
        value_var = tk.StringVar(value=value)
        row_vars.append((name_var, value_var))

        f = ttk.Frame(rows_frame, padding=(0, 2))
        f.pack(fill=X)
        ttk.Entry(f, textvariable=name_var,  width=22).pack(side=LEFT, padx=2)
        ttk.Entry(f, textvariable=value_var, width=22).pack(side=LEFT, padx=2)
        ttk.Button(f, text="✕", bootstyle="danger-link", width=3,
                   command=lambda r=row_vars, nv=name_var, vv=value_var, fr=f:
                       (r.remove((nv, vv)), fr.destroy())).pack(side=LEFT)

    def _done(self):
        for scope in ("global", "local"):
            row_vars = getattr(self, f"_{scope}_row_vars", [])
            var_dict = getattr(self, f"_{scope}_var_dict", {})
            var_dict.clear()
            for name_var, value_var in row_vars:
                n = name_var.get().strip()
                if n:
                    var_dict[n] = value_var.get()
        self._callback()
        self.destroy()
