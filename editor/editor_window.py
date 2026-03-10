"""Crystal Engine - Main editor window."""
import os
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from engine.constants import EDITOR_W, EDITOR_H, SIDEBAR_W_FRAC, CANVAS_W_FRAC
from engine.utils import screen_fraction, center_window
from engine.project_manager import save_project

from editor.toolbar       import EditorToolbar
from editor.screen_manager import ScreenManager
from editor.sprite_manager import SpriteManager
from editor.canvas         import EditorCanvas
from editor.blocks_panel   import BlocksPanel
from editor.variable_editor import VariableEditor


class EditorWindow(tk.Toplevel):
    """Full editor: toolbar + 3-column layout."""

    def __init__(self, parent, project: dict, filepath: str):
        super().__init__(parent)
        self._project  = project
        self._filepath = filepath
        self._running_process = None

        self.title(f"Crystal – {project['name']}")
        self.resizable(True, True)

        w, h = screen_fraction(self, EDITOR_W, EDITOR_H)
        center_window(self, w, h)
        self.minsize(900, 600)

        self._active_screen = (project["screens"][0]
                               if project.get("screens") else None)
        self._active_sprite = None

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Build ────────────────────────────────────────────────────────────

    def _build(self):
        # Toolbar
        tb_cbs = {
            "run":     self._run,
            "stop":    self._stop,
            "compile": self._compile,
            "build":   self._build_project,
            "export":  self._export,
            "save":    self._save,
        }
        self._toolbar = EditorToolbar(self, tb_cbs)
        self._toolbar.pack(fill=X)
        self._toolbar.set_project_name(self._project["name"])

        ttk.Separator(self).pack(fill=X)

        # Menu bar
        menubar = tk.Menu(self)
        self.configure(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Save",         command=self._save,
                              accelerator="Ctrl+S")
        file_menu.add_command(label="Save As…",     command=self._save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Project Settings…", command=self._project_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Close",        command=self._on_close)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Global Variables…",
                              command=lambda: VariableEditor(
                                  self, self._project, None, self._refresh_all))
        edit_menu.add_command(label="Screen Variables…",
                              command=lambda: VariableEditor(
                                  self, self._project, self._active_screen,
                                  self._refresh_all))
        menubar.add_cascade(label="Edit", menu=edit_menu)

        run_menu = tk.Menu(menubar, tearoff=0)
        run_menu.add_command(label="Run",       command=self._run)
        run_menu.add_command(label="Stop",      command=self._stop)
        run_menu.add_separator()
        run_menu.add_command(label="Compile",   command=self._compile)
        run_menu.add_command(label="Build…",    command=self._build_project)
        menubar.add_cascade(label="Run", menu=run_menu)

        export_menu = tk.Menu(menubar, tearoff=0)
        export_menu.add_command(label="Export as Python Project…",
                                command=self._export)
        menubar.add_cascade(label="Export", menu=export_menu)

        self.bind("<Control-s>", lambda e: self._save())

        # Vertical split: editor (top) + console (bottom)
        v_split = tk.PanedWindow(self, orient=VERTICAL, bg="#1c1c2e", sashwidth=5)
        v_split.pack(fill=BOTH, expand=True)

        editor_area = ttk.Frame(v_split)
        v_split.add(editor_area, minsize=200)

        from runtime.console import ConsolePanel
        self._console = ConsolePanel(v_split)
        v_split.add(self._console, minsize=90)

        def _set_vsash():
            h = v_split.winfo_height()
            if h > 20:
                v_split.sash_place(0, 0, int(h * 0.76))
        self.after(250, _set_vsash)

        # 3-Column main area inside editor_area
        main = tk.PanedWindow(editor_area, orient=HORIZONTAL, bg="#1c1c2e", sashwidth=4)
        main.pack(fill=BOTH, expand=True)

        sw = self.winfo_screenwidth()
        lw = int(sw * EDITOR_W * SIDEBAR_W_FRAC)
        cw = int(sw * EDITOR_W * CANVAS_W_FRAC)

        # LEFT sidebar frame
        left = ttk.Frame(main, width=lw)
        main.add(left)

        # CENTER canvas
        center_frame = ttk.Frame(main, width=cw)
        main.add(center_frame)

        self._screen_info = ttk.Label(center_frame, text="",
                                       font=("Segoe UI", 9),
                                       padding=(8, 2))
        self._screen_info.pack(fill=X)

        self._canvas = EditorCanvas(center_frame, self._project,
                                     self._active_screen)
        self._canvas.pack(fill=BOTH, expand=True)
        self._canvas.on_sprite_moved    = self._on_sprite_moved
        self._canvas.on_sprite_selected = self._on_sprite_selected_canvas

        # RIGHT blocks panel — must be created BEFORE sidebar managers
        right = ttk.Frame(main)
        main.add(right)

        self._blocks = BlocksPanel(right, self._project)
        self._blocks.pack(fill=BOTH, expand=True)
        self._blocks.set_target(self._active_screen)

        # NOW safe to build sidebar — callbacks will find _canvas and _blocks ready
        self._sprite_mgr = SpriteManager(left, self._project,
                                          self._active_screen,
                                          self._on_sprite_select)
        self._sprite_mgr.pack(fill=BOTH, expand=True)

        ttk.Separator(left).pack(fill=X, pady=4)

        self._screen_mgr = ScreenManager(left, self._project,
                                          self._on_screen_select)
        self._screen_mgr.pack(fill=X)

        self._update_screen_info()

    # ── Screen / Sprite selection ────────────────────────────────────────

    def _on_screen_select(self, screen):
        self._active_screen = screen
        self._active_sprite = None
        if hasattr(self, '_canvas'):
            self._canvas.set_screen(screen)
        if hasattr(self, '_sprite_mgr'):
            self._sprite_mgr.set_screen(screen)
        if hasattr(self, '_blocks'):
            self._blocks.set_target(screen)
        if hasattr(self, '_screen_info'):
            self._update_screen_info()

    def _on_sprite_select(self, sprite):
        self._active_sprite = sprite
        if hasattr(self, '_canvas'):
            self._canvas.set_selected_sprite(sprite)
        if hasattr(self, '_blocks'):
            self._blocks.set_target(sprite if sprite else self._active_screen)

    def _on_sprite_selected_canvas(self, sprite):
        self._active_sprite = sprite
        if hasattr(self, '_canvas'):
            self._canvas.set_selected_sprite(sprite)
        if hasattr(self, '_sprite_mgr'):
            self._sprite_mgr._selected_sprite = sprite
            self._sprite_mgr.refresh()
        if hasattr(self, '_blocks'):
            self._blocks.set_target(sprite)

    def _on_sprite_moved(self, sprite, px, py):
        pass  # project dict already updated in-place

    def _update_screen_info(self):
        s = self._active_screen
        if not s or not hasattr(self, '_screen_info'):
            return
        info = f"Screen: {s['name']}    " \
               f"{'[OVERLAY] ' if s.get('overlay') else ''}" \
               f"Sprites: {len(s.get('sprites', []))}"
        self._screen_info.configure(text=info)

    def _refresh_all(self):
        if hasattr(self, '_canvas'):
            self._canvas.redraw()
        if hasattr(self, '_sprite_mgr'):
            self._sprite_mgr.refresh()
        if hasattr(self, '_blocks'):
            self._blocks.set_target(self._active_sprite or self._active_screen)

    # ── Toolbar actions ──────────────────────────────────────────────────

    def _save(self):
        try:
            save_project(self._project, self._filepath)
            self.title(f"Crystal – {self._project['name']}")
        except Exception as ex:
            messagebox.showerror("Save Error", str(ex), parent=self)

    def _save_as(self):
        from tkinter import filedialog
        from engine.constants import CRYSTAL_FILE_EXT
        path = filedialog.asksaveasfilename(
            title="Save Project As",
            initialfile=os.path.basename(self._filepath),
            defaultextension=CRYSTAL_FILE_EXT,
            filetypes=[("Crystal Project", f"*{CRYSTAL_FILE_EXT}")])
        if path:
            self._filepath = path
            self._save()

    def _project_settings(self):
        ProjectSettingsDialog(self, self._project)

    def _run(self):
        self._save()
        from runtime.runner import ProjectRunner
        from runtime.console import ConsolePanel
        self._runner = ProjectRunner(self._project, self._filepath)
        self._runner.on_output = lambda line, level: ConsolePanel.post(line, level)
        try:
            self._runner.launch()
            self._toolbar.set_running(True)
        except Exception as ex:
            messagebox.showerror("Run Error", str(ex), parent=self)
            self._runner = None

    def _stop(self):
        if hasattr(self, "_runner") and self._runner:
            self._runner.stop()
            self._runner = None
        self._toolbar.set_running(False)

    def _compile(self):
        from runtime.compiler import Compiler
        compiler = Compiler(self._project)
        try:
            src = compiler.compile()
            CodePreviewDialog(self, src)
        except Exception as ex:
            messagebox.showerror("Compile Error", str(ex), parent=self)

    def _build_project(self):
        import tempfile, os, shutil, zipfile
        from runtime.compiler import Compiler
        compiler = Compiler(self._project)
        try:
            src = compiler.compile()
        except Exception as ex:
            messagebox.showerror("Build Error", str(ex), parent=self)
            return

        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            title="Save Build",
            defaultextension=".py",
            filetypes=[("Python Script", "*.py")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(src)
            messagebox.showinfo("Build", f"Built successfully:\n{path}", parent=self)

    def _export(self):
        from exporter.export_window import ExportWindow
        ExportWindow(self, self._project)

    def _on_close(self):
        if messagebox.askyesno("Close", "Save before closing?", parent=self):
            self._save()
        self.destroy()


# ── Project Settings Dialog ───────────────────────────────────────────────────

class ProjectSettingsDialog(tk.Toplevel):
    PRESETS = [
        ("1920 × 1080  (16:9 Full HD)",   1920, 1080),
        ("1280 × 720   (16:9 HD)",         1280,  720),
        ("1024 × 768   (4:3)",             1024,  768),
        ("800 × 600    (4:3 Classic)",      800,  600),
        ("2560 × 1440  (16:9 2K)",         2560, 1440),
        ("960 × 540    (16:9 qHD)",         960,  540),
    ]

    def __init__(self, parent, project):
        super().__init__(parent)
        self.title("Project Settings")
        self.resizable(True, False)
        center_window(self, 520, 480)
        self.grab_set()
        self._project = project
        self._build()

    def _build(self):
        # ── Resolution presets ────────────────────────────────────
        preset_frame = ttk.Frame(self, padding=(20, 16))
        preset_frame.pack(fill=X)
        ttk.Label(preset_frame, text="Resolution Preset",
                  font=("Segoe UI", 10, "bold")).pack(anchor=W, pady=(0, 6))

        preset_row = ttk.Frame(preset_frame)
        preset_row.pack(fill=X)
        preset_names = [p[0] for p in self.PRESETS]
        self._preset_var = tk.StringVar(value="Custom")
        preset_cb = ttk.Combobox(preset_row, textvariable=self._preset_var,
                                  values=preset_names, state="readonly", width=38)
        preset_cb.pack(side=LEFT)
        preset_cb.bind("<<ComboboxSelected>>", self._on_preset)

        ttk.Separator(self).pack(fill=X, padx=20)

        # ── Fields ────────────────────────────────────────────────
        f = ttk.Frame(self, padding=(20, 12))
        f.pack(fill=BOTH, expand=True)

        fields = [
            ("Window Title",  "window_title", None),
            ("Width (px)",    "width",        None),
            ("Height (px)",   "height",       None),
            ("Target FPS",    "fps",          None),
            ("BG Color",      "bg_color",     None),
            ("Fullscreen",    "fullscreen",   None),
            ("Adaptive Size", "adaptive",     None),
        ]
        self._vars = {}
        BOOL_KEYS = ("fullscreen", "adaptive")
        for row, (label, key, _) in enumerate(fields):
            ttk.Label(f, text=label, width=15,
                      font=("Segoe UI", 10)).grid(
                row=row, column=0, sticky=W, pady=8, padx=(0, 12))
            if key in BOOL_KEYS:
                bool_var = tk.BooleanVar(value=bool(self._project.get(key, False)))
                str_var  = tk.StringVar(value=str(bool_var.get()))
                self._vars[key] = str_var
                def _sync(bv=bool_var, sv=str_var):
                    sv.set(str(bv.get()))
                chk = ttk.Checkbutton(f, variable=bool_var,
                                       bootstyle="round-toggle",
                                       command=_sync)
                chk.grid(row=row, column=1, sticky=W, pady=8)
                bool_var.trace_add("write", lambda *_, bv=bool_var, sv=str_var:
                                   sv.set(str(bv.get())))
            else:
                var = tk.StringVar(value=str(self._project.get(key, "")))
                self._vars[key] = var
                entry = ttk.Entry(f, textvariable=var, width=20)
                entry.grid(row=row, column=1, sticky=EW, pady=8)
                if key in ("width", "height"):
                    hint_var = tk.StringVar()
                    ttk.Label(f, textvariable=hint_var, foreground="#888",
                              font=("Segoe UI", 8)).grid(
                        row=row, column=2, sticky=W, padx=(8, 0))
                    def _update_hint(v=var, h=hint_var, k=key):
                        try:
                            val = int(v.get())
                            sw  = self.winfo_screenwidth()
                            sh  = self.winfo_screenheight()
                            ref = sw if k == "width" else sh
                            h.set(f"= {val/ref:.2f} × screen")
                        except ValueError:
                            h.set("")
                    var.trace_add("write", lambda *_, f=_update_hint: f())
                    _update_hint()

        f.columnconfigure(1, weight=1)

        ttk.Separator(self).pack(fill=X, padx=20)

        btn_row = ttk.Frame(self, padding=(20, 10))
        btn_row.pack(fill=X)
        ttk.Button(btn_row, text="Cancel", bootstyle="secondary-outline",
                   command=self.destroy).pack(side=LEFT)
        ttk.Button(btn_row, text="Apply", bootstyle="success",
                   command=self._apply).pack(side=RIGHT)

    def _on_preset(self, _=None):
        name = self._preset_var.get()
        for label, w, h in self.PRESETS:
            if label == name:
                self._vars["width"].set(str(w))
                self._vars["height"].set(str(h))
                break

    def _apply(self):
        for key, var in self._vars.items():
            val = var.get()
            if key in ("width", "height", "fps"):
                try:
                    val = int(val)
                except ValueError:
                    pass
            elif key in ("fullscreen", "adaptive"):
                val = val.lower() in ("true", "yes", "1", "on")
            self._project[key] = val
        self.destroy()


# ── Code Preview ──────────────────────────────────────────────────────────────

class CodePreviewDialog(tk.Toplevel):
    def __init__(self, parent, code: str):
        super().__init__(parent)
        self.title("Compiled Code Preview")
        self.resizable(True, True)
        center_window(self, 700, 550)

        txt = tk.Text(self, bg="#1a1a2e", fg="#e0e0e0",
                      font=("Consolas", 10), wrap="none")
        sb_y = ttk.Scrollbar(self, orient=VERTICAL,   command=txt.yview)
        sb_x = ttk.Scrollbar(self, orient=HORIZONTAL, command=txt.xview)
        txt.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)
        sb_y.pack(side=RIGHT, fill=Y)
        sb_x.pack(side=BOTTOM, fill=X)
        txt.pack(fill=BOTH, expand=True)
        txt.insert("1.0", code)
        txt.configure(state="disabled")

        ttk.Button(self, text="Close", command=self.destroy,
                   bootstyle="secondary").pack(pady=6)


from engine.utils import center_window
