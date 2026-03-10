"""Crystal Engine - Main launcher application (ttkbootstrap)."""
import os
import tkinter as tk
from tkinter import messagebox, filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk

from engine.constants import (APP_NAME, APP_VERSION, LAUNCHER_W, LAUNCHER_H,
                               CRYSTAL_FILE_EXT, DEFAULT_TITLE, DEFAULT_WIDTH,
                               DEFAULT_HEIGHT, DEFAULT_FPS)
from engine.utils import screen_fraction, center_window, load_icon
from engine.project_manager import (new_project, save_project, load_project,
                                     new_screen)


ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "assets")


class CrystalApp:
    """Launcher: shows the project list and handles project CRUD."""

    def __init__(self):
        self.root = ttk.Window(themename="darkly")
        self.root.title(f"{APP_NAME}  {APP_VERSION}")
        self.root.resizable(True, True)

        w, h = screen_fraction(self.root, LAUNCHER_W, LAUNCHER_H)
        center_window(self.root, w, h)
        self.root.minsize(640, 480)

        self._projects_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "projects.index"
        )
        self._project_entries = []   # list of {"name":..., "path":...}
        self._load_index()

        # Icons
        logo_path = os.path.join(ASSETS_DIR, "icons", "crystal_logo.png")
        self._logo_img = load_icon(logo_path, (48, 48))

        self._build_ui(w, h)

    # ── Index file ────────────────────────────────────────────────────────

    def _load_index(self):
        import json
        if os.path.exists(self._projects_file):
            try:
                with open(self._projects_file) as f:
                    self._project_entries = json.load(f)
            except Exception:
                self._project_entries = []

    def _save_index(self):
        import json
        with open(self._projects_file, "w") as f:
            json.dump(self._project_entries, f, indent=2)

    # ── UI ───────────────────────────────────────────────────────────────

    def _build_ui(self, w, h):
        # Header bar
        header = ttk.Frame(self.root, padding=(16, 10))
        header.pack(fill=X)

        if self._logo_img:
            ttk.Label(header, image=self._logo_img).pack(
                side=LEFT, padx=(0, 10))

        ttk.Label(header, text=APP_NAME, font=("Segoe UI", 18, "bold")).pack(side=LEFT)
        ttk.Label(header, text=f"v{APP_VERSION}", font=("Segoe UI", 10),
                  foreground="#888").pack(
                  side=LEFT, padx=(8, 0), anchor=S, pady=(0, 4))

        btn_frame = ttk.Frame(header)
        btn_frame.pack(side=RIGHT)

        ttk.Button(btn_frame, text="＋  New Project", bootstyle="success",
                   command=self._on_new_project, width=16).pack(side=LEFT, padx=4)
        ttk.Button(btn_frame, text="📂  Open File", bootstyle="secondary",
                   command=self._on_open_file, width=14).pack(side=LEFT, padx=4)

        # Search bar
        search_bar = ttk.Frame(self.root, padding=(16, 8))
        search_bar.pack(fill=X)
        ttk.Label(search_bar, text="Projects", font=("Segoe UI", 12, "bold")).pack(
            side=LEFT)

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._refresh_list())
        search_entry = ttk.Entry(search_bar, textvariable=self._search_var, width=30)
        search_entry.pack(side=RIGHT)
        ttk.Label(search_bar, text="🔍", font=("Segoe UI", 11)).pack(side=RIGHT, padx=4)

        ttk.Separator(self.root).pack(fill=X)

        # Project list (scrollable)
        list_frame = ttk.Frame(self.root, padding=(12, 8))
        list_frame.pack(fill=BOTH, expand=True)

        canvas = tk.Canvas(list_frame, bg="#1c1c2e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)

        self._cards_frame = ttk.Frame(canvas)
        self._cards_window = canvas.create_window(
            (0, 0), window=self._cards_frame, anchor="nw")

        self._cards_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(self._cards_window, width=e.width))
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        self._canvas_ref = canvas
        self._refresh_list()

        # Status bar
        self._status_var = tk.StringVar(value="Ready")
        ttk.Label(self.root, textvariable=self._status_var,
                  font=("Segoe UI", 9), bootstyle="secondary").pack(
                  side=BOTTOM, anchor=W, padx=12, pady=4)

    def _refresh_list(self):
        for w in self._cards_frame.winfo_children():
            w.destroy()

        query = self._search_var.get().lower()
        entries = [e for e in self._project_entries
                   if query in e["name"].lower()]

        if not entries:
            ttk.Label(self._cards_frame,
                      text="No projects yet.  Click ＋ New Project to get started.",
                      font=("Segoe UI", 11), foreground="#555").pack(pady=60)
            return

        for entry in entries:
            self._make_project_card(entry)

    def _make_project_card(self, entry):
        path_exists = os.path.exists(entry.get("path", ""))

        card = ttk.Frame(self._cards_frame, bootstyle="secondary",
                         padding=(18, 14), cursor="hand2")
        card.pack(fill=X, padx=12, pady=6)

        left = ttk.Frame(card)
        left.pack(side=LEFT, fill=BOTH, expand=True)

        ttk.Label(left, text=entry["name"],
                  font=("Segoe UI", 13, "bold")).pack(anchor=W)

        path_color = "#888" if path_exists else "#e74c3c"
        path_text  = entry.get("path", "(no path)") if path_exists else \
                     f"⚠  Missing: {entry.get('path','')}"
        ttk.Label(left, text=path_text, font=("Segoe UI", 9),
                  foreground=path_color).pack(anchor=W, pady=(2, 0))

        right = ttk.Frame(card)
        right.pack(side=RIGHT, padx=4)

        ttk.Button(right, text="▶  Open", bootstyle="primary",
                   command=lambda e=entry: self._open_project(e), width=10).pack(
                   side=LEFT, padx=4)
        ttk.Button(right, text="Remove", bootstyle="danger-outline",
                   command=lambda e=entry: self._remove_project(e), width=8).pack(
                   side=LEFT, padx=2)

    # ── Actions ──────────────────────────────────────────────────────────

    def _on_new_project(self):
        NewProjectDialog(self.root, self._on_project_created)

    def _on_project_created(self, project, filepath):
        save_project(project, filepath)
        entry = {"name": project["name"], "path": filepath}
        self._project_entries.insert(0, entry)
        self._save_index()
        self._refresh_list()
        self._open_project(entry)

    def _on_open_file(self):
        path = filedialog.askopenfilename(
            title="Open Crystal Project",
            filetypes=[("Crystal Project", f"*{CRYSTAL_FILE_EXT}"), ("All Files", "*.*")])
        if not path:
            return
        try:
            project = load_project(path)
            # Add to index if not present
            if not any(e["path"] == path for e in self._project_entries):
                self._project_entries.insert(0, {"name": project["name"], "path": path})
                self._save_index()
                self._refresh_list()
            self._open_project_at_path(project, path)
        except Exception as ex:
            messagebox.showerror("Error", f"Could not open project:\n{ex}")

    def _open_project(self, entry):
        path = entry.get("path", "")
        if not os.path.exists(path):
            messagebox.showerror("Not Found", f"Project file not found:\n{path}")
            return
        try:
            project = load_project(path)
            self._open_project_at_path(project, path)
        except Exception as ex:
            messagebox.showerror("Error", f"Could not open project:\n{ex}")

    def _open_project_at_path(self, project, path):
        from editor.editor_window import EditorWindow
        EditorWindow(self.root, project, path)

    def _remove_project(self, entry):
        if messagebox.askyesno("Remove", f"Remove '{entry['name']}' from list?\n"
                               "(File will NOT be deleted.)"):
            self._project_entries.remove(entry)
            self._save_index()
            self._refresh_list()

    def run(self):
        self.root.mainloop()


# ── New Project Dialog ────────────────────────────────────────────────────────

class NewProjectDialog(tk.Toplevel):
    """Two-step wizard: choose type → fill details."""

    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("New Project")
        self.resizable(False, False)
        self._callback = callback
        self.configure(bg="#2b2b2b")

        from engine.utils import screen_fraction, center_window
        w, h = screen_fraction(self, 0.45, 0.70)
        center_window(self, w, h)
        self.grab_set()

        self._step1()

    # Step 1 – Dimension type
    def _step1(self):
        for c in self.winfo_children():
            c.destroy()

        ttk.Label(self, text="Choose Project Type", font=("Segoe UI", 14, "bold"),
                  padding=(20, 16)).pack()
        ttk.Separator(self).pack(fill=X, padx=20)

        grid_frame = ttk.Frame(self, padding=20)
        grid_frame.pack(fill=BOTH, expand=True)

        # Scrollable grid of dimension options
        canvas = tk.Canvas(grid_frame, bg="#1c1c2e", highlightthickness=0, height=280)
        sb = ttk.Scrollbar(grid_frame, orient=VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        canvas.pack(fill=BOTH, expand=True)

        inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # Only "2D" for now — easily extensible
        options = [
            ("2D", "Flat 2D game.\nPygame-based renderer.", "#4a90d9"),
        ]

        col = 0
        for label, desc, color in options:
            btn = tk.Frame(inner, bg=color, cursor="hand2",
                           width=160, height=120, relief="flat")
            btn.grid(row=0, column=col, padx=12, pady=12)
            btn.pack_propagate(False)
            tk.Label(btn, text=label, bg=color, fg="white",
                     font=("Segoe UI", 16, "bold")).pack(expand=True)
            tk.Label(btn, text=desc, bg=color, fg="#ddd",
                     font=("Segoe UI", 8), justify=CENTER,
                     wraplength=140).pack(pady=(0, 8))
            btn.bind("<Button-1>", lambda e, lbl=label: self._step2(lbl))
            for child in btn.winfo_children():
                child.bind("<Button-1>", lambda e, lbl=label: self._step2(lbl))
            col += 1

    # Step 2 – Project details
    def _step2(self, proj_type):
        for c in self.winfo_children():
            c.destroy()

        ttk.Label(self, text=f"New {proj_type} Project",
                  font=("Segoe UI", 14, "bold"), padding=(20, 16)).pack()
        ttk.Separator(self).pack(fill=X, padx=20)

        form = ttk.Frame(self, padding=(30, 20))
        form.pack(fill=BOTH, expand=True)

        fields = [
            ("Project Name",  "name",    "MyGame"),
            ("Window Title",  "title",   DEFAULT_TITLE),
            ("Width (px)",    "width",   str(DEFAULT_WIDTH)),
            ("Height (px)",   "height",  str(DEFAULT_HEIGHT)),
            ("Target FPS",    "fps",     str(DEFAULT_FPS)),
        ]

        self._vars = {}
        for row, (label, key, default) in enumerate(fields):
            ttk.Label(form, text=label, font=("Segoe UI", 10)).grid(
                row=row, column=0, sticky=W, pady=6, padx=(0, 16))
            var = tk.StringVar(value=default)
            self._vars[key] = var
            ttk.Entry(form, textvariable=var, width=28).grid(
                row=row, column=1, sticky=EW, pady=6)

        form.columnconfigure(1, weight=1)

        # Save location
        ttk.Label(form, text="Save to", font=("Segoe UI", 10)).grid(
            row=len(fields), column=0, sticky=W, pady=6, padx=(0, 16))
        self._save_path_var = tk.StringVar()
        ttk.Entry(form, textvariable=self._save_path_var, width=22).grid(
            row=len(fields), column=1, sticky=EW, pady=6)
        ttk.Button(form, text="…", command=self._browse_save, width=3,
                   bootstyle="secondary").grid(
            row=len(fields), column=2, padx=(4, 0), pady=6)

        btn_row = ttk.Frame(self, padding=(20, 10))
        btn_row.pack(fill=X)
        ttk.Button(btn_row, text="← Back", command=self._step1,
                   bootstyle="secondary-outline").pack(side=LEFT)
        ttk.Button(btn_row, text="Create Project ▸", command=self._create,
                   bootstyle="success").pack(side=RIGHT)

    def _browse_save(self):
        from engine.constants import CRYSTAL_FILE_EXT
        name = self._vars["name"].get().strip().replace(" ", "_") or "project"
        path = filedialog.asksaveasfilename(
            title="Save Project As",
            initialfile=f"{name}{CRYSTAL_FILE_EXT}",
            defaultextension=CRYSTAL_FILE_EXT,
            filetypes=[("Crystal Project", f"*{CRYSTAL_FILE_EXT}")])
        if path:
            self._save_path_var.set(path)

    def _create(self):
        name  = self._vars["name"].get().strip()
        title = self._vars["title"].get().strip()
        path  = self._save_path_var.get().strip()

        if not name:
            messagebox.showwarning("Missing", "Project name is required.", parent=self)
            return
        if not path:
            messagebox.showwarning("Missing", "Save location is required.", parent=self)
            return

        try:
            w = int(self._vars["width"].get())
            h = int(self._vars["height"].get())
            fps = int(self._vars["fps"].get())
        except ValueError:
            messagebox.showwarning("Invalid", "Width, Height and FPS must be integers.",
                                   parent=self)
            return

        from engine.project_manager import new_project
        project = new_project(name=name, title=title or name,
                               width=w, height=h, fps=fps)
        self.destroy()
        self._callback(project, path)
