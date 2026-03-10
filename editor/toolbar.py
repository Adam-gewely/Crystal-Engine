"""Crystal Engine - Editor toolbar."""
import os
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from engine.utils import load_icon

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "assets")


class EditorToolbar(ttk.Frame):
    """Top toolbar: Run / Stop / Compile / Build / Export / Save."""

    def __init__(self, parent, callbacks: dict, **kw):
        super().__init__(parent, padding=(10, 7), **kw)
        self._cbs   = callbacks
        self._icons = {}
        self._build()

    def _build(self):
        icon_cfg = [
            ("run",     "▶  Run",     "success",   "run"),
            ("stop",    "⏹  Stop",    "danger",    "stop"),
            None,
            ("compile", "⚙  Compile", "info",      "compile"),
            ("build",   "📦  Build",  "warning",   "build"),
            None,
            ("export",  "📤  Export", "secondary", "export"),
            None,
            ("save",    "💾  Save",   "primary",   "save"),
        ]

        for cfg in icon_cfg:
            if cfg is None:
                ttk.Separator(self, orient=VERTICAL).pack(
                    side=LEFT, fill=Y, padx=6, pady=4)
                continue

            key, label, style, icon_name = cfg
            icon_path = os.path.join(ASSETS_DIR, "icons", f"icon_{icon_name}.png")
            icon      = load_icon(icon_path, (20, 20))
            if icon:
                self._icons[key] = icon

            btn = ttk.Button(self,
                             text=label,
                             image=self._icons.get(key),
                             compound=LEFT,
                             bootstyle=f"{style}-outline",
                             command=self._cbs.get(key, lambda: None),
                             width=11)
            btn.pack(side=LEFT, padx=5)
            if key == "stop":
                self._stop_btn = btn
                btn.configure(state=DISABLED)

        # Project name label on the right
        self._proj_label = ttk.Label(self, text="",
                                      font=("Segoe UI", 10, "bold"),
                                      foreground="#888")
        self._proj_label.pack(side=RIGHT, padx=12)

    def set_running(self, running: bool):
        self._stop_btn.configure(state=NORMAL if running else DISABLED)

    def set_project_name(self, name: str):
        self._proj_label.configure(text=name)
