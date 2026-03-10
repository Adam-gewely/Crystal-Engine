"""Crystal Engine - Animation editor dialog."""
import os, base64
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk
from engine.utils import center_window
from engine.project_manager import embed_asset


class AnimationEditor(tk.Toplevel):
    """Edit animations for a sprite: add/remove/reorder PNG frames."""

    def __init__(self, parent, project: dict, sprite: dict, callback):
        super().__init__(parent)
        self.title(f"Animations – {sprite['name']}")
        self.resizable(True, True)
        w, h = 700, 520
        center_window(self, w, h)
        self.grab_set()

        self._project  = project
        self._sprite   = sprite
        self._callback = callback
        self._anim_images = {}  # anim_name -> list of PhotoImage for preview

        self._current_anim = None
        self._build()
        self._refresh_anim_list()

    def _build(self):
        paned = tk.PanedWindow(self, orient=HORIZONTAL, bg="#1c1c2e", sashwidth=4)
        paned.pack(fill=BOTH, expand=True, padx=8, pady=8)

        # Left: animation list
        left = ttk.Frame(paned, width=180)
        paned.add(left)

        ttk.Label(left, text="Animations", font=("Segoe UI", 10, "bold")).pack(
            pady=(4, 2))

        self._anim_listbox = tk.Listbox(left, selectmode=SINGLE,
                                         bg="#2a2a3e", fg="white",
                                         selectbackground="#4a90d9",
                                         font=("Segoe UI", 10), relief="flat",
                                         borderwidth=0)
        self._anim_listbox.pack(fill=BOTH, expand=True, padx=4)
        self._anim_listbox.bind("<<ListboxSelect>>", self._on_anim_select)

        btn_bar = ttk.Frame(left)
        btn_bar.pack(fill=X, padx=4, pady=4)
        ttk.Button(btn_bar, text="+", width=3, bootstyle="success-outline",
                   command=self._new_anim).pack(side=LEFT)
        ttk.Button(btn_bar, text="✕", width=3, bootstyle="danger-outline",
                   command=self._delete_anim).pack(side=LEFT, padx=4)

        # Right: frame editor
        right = ttk.Frame(paned)
        paned.add(right)

        top = ttk.Frame(right)
        top.pack(fill=X, padx=4, pady=4)
        ttk.Label(top, text="Frames (PNGs)", font=("Segoe UI", 10, "bold")).pack(
            side=LEFT)
        ttk.Button(top, text="Add Frames…", bootstyle="primary-outline",
                   command=self._add_frames).pack(side=RIGHT, padx=4)
        ttk.Button(top, text="Remove Selected", bootstyle="danger-outline",
                   command=self._remove_frame).pack(side=RIGHT)

        # Frame scroll list
        frame_scroll = ttk.Frame(right)
        frame_scroll.pack(fill=BOTH, expand=True, padx=4)

        canvas = tk.Canvas(frame_scroll, bg="#1a1a2e", highlightthickness=0)
        sb = ttk.Scrollbar(frame_scroll, orient=VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        canvas.pack(fill=BOTH, expand=True)

        self._frames_inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=self._frames_inner, anchor="nw")
        self._frames_inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # Speed
        speed_bar = ttk.Frame(right)
        speed_bar.pack(fill=X, padx=4, pady=4)
        ttk.Label(speed_bar, text="Speed (fps):").pack(side=LEFT)
        self._speed_var = tk.IntVar(value=12)
        ttk.Spinbox(speed_bar, from_=1, to=120, textvariable=self._speed_var,
                    width=6).pack(side=LEFT, padx=6)

        ttk.Button(right, text="Save & Close", bootstyle="success",
                   command=self._save_close).pack(pady=8)

    def _refresh_anim_list(self):
        self._anim_listbox.delete(0, END)
        for name in self._sprite.get("animations", {}):
            self._anim_listbox.insert(END, name)

    def _on_anim_select(self, _=None):
        sel = self._anim_listbox.curselection()
        if not sel:
            return
        self._current_anim = self._anim_listbox.get(sel[0])
        self._refresh_frames()

    def _refresh_frames(self):
        for w in self._frames_inner.winfo_children():
            w.destroy()
        if not self._current_anim:
            return
        anim_data = self._sprite["animations"].get(self._current_anim, {})
        frames = anim_data.get("frames", [])

        self._frame_checkboxes = []
        for i, fname in enumerate(frames):
            row = ttk.Frame(self._frames_inner, padding=(2, 2))
            row.pack(fill=X)
            var = tk.BooleanVar()
            ttk.Checkbutton(row, variable=var).pack(side=LEFT)
            # Thumbnail
            b64 = self._project.get("assets", {}).get(f"sprites/{fname}")
            if b64:
                try:
                    import io
                    raw = base64.b64decode(b64)
                    img = Image.open(io.BytesIO(raw)).resize((40, 40), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    lbl = ttk.Label(row, image=photo)
                    lbl.image = photo
                    lbl.pack(side=LEFT, padx=4)
                except Exception:
                    pass
            ttk.Label(row, text=f"{i+1}. {fname}", font=("Segoe UI", 9)).pack(
                side=LEFT)
            self._frame_checkboxes.append((var, fname))

    def _new_anim(self):
        name = tkinter.simpledialog.askstring("New Animation", "Animation name:",
                                          parent=self)
        if name and name.strip():
            self._sprite.setdefault("animations", {})[name.strip()] = {
                "frames": [], "fps": 12}
            self._refresh_anim_list()

    def _delete_anim(self):
        if self._current_anim:
            self._sprite["animations"].pop(self._current_anim, None)
            self._current_anim = None
            self._refresh_anim_list()
            self._refresh_frames()

    def _add_frames(self):
        if not self._current_anim:
            messagebox.showwarning("No Animation", "Select or create an animation first.",
                                   parent=self)
            return
        paths = filedialog.askopenfilenames(
            title="Add Frame PNGs",
            filetypes=[("PNG Images", "*.png"), ("All Images", "*.png;*.jpg;*.bmp")])
        if not paths:
            return
        anim = self._sprite["animations"][self._current_anim]
        for p in paths:
            fname = os.path.basename(p)
            logical = f"sprites/{fname}"
            embed_asset(self._project, logical, p)
            if fname not in anim["frames"]:
                anim["frames"].append(fname)
        self._refresh_frames()

    def _remove_frame(self):
        if not self._current_anim:
            return
        anim = self._sprite["animations"][self._current_anim]
        to_remove = {fname for var, fname in getattr(self, "_frame_checkboxes", [])
                     if var.get()}
        anim["frames"] = [f for f in anim["frames"] if f not in to_remove]
        self._refresh_frames()

    def _save_close(self):
        if self._current_anim and self._current_anim in self._sprite["animations"]:
            self._sprite["animations"][self._current_anim]["fps"] = self._speed_var.get()
        self._callback()
        self.destroy()


# need simpledialog
import tkinter.simpledialog
