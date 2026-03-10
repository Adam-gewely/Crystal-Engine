"""Crystal Engine - Sprite management + asset library panel."""
import os, base64, io
import tkinter as tk
import tkinter.simpledialog
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk

from engine.project_manager import new_sprite, embed_asset
from engine.utils import center_window


class SpriteManager(ttk.Frame):
    """Left sidebar: asset library + sprite list for the active screen."""

    def __init__(self, parent, project, screen, on_sprite_select, **kw):
        super().__init__(parent, **kw)
        self._project          = project
        self._screen           = screen
        self._on_sprite_select = on_sprite_select
        self._selected_sprite  = None
        self._thumb_cache      = {}
        self._build()

    def set_screen(self, screen):
        self._screen          = screen
        self._selected_sprite = None
        self.refresh()

    def _build(self):
        # ── Sprites section ───────────────────────────────────────────
        sp_hdr = ttk.Frame(self, padding=(4, 4))
        sp_hdr.pack(fill=X)
        ttk.Label(sp_hdr, text="Sprites", font=("Segoe UI", 10, "bold")).pack(side=LEFT)
        ttk.Button(sp_hdr, text="+", bootstyle="success-outline", width=3,
                   command=self._add_sprite).pack(side=RIGHT)

        # Scrollable sprite tile list
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=BOTH, expand=True)
        sp_cv = tk.Canvas(list_frame, bg="#1a1a2e", highlightthickness=0)
        sp_sb = ttk.Scrollbar(list_frame, orient=VERTICAL, command=sp_cv.yview)
        sp_cv.configure(yscrollcommand=sp_sb.set)
        sp_sb.pack(side=RIGHT, fill=Y)
        sp_cv.pack(fill=BOTH, expand=True)
        self._sp_inner = ttk.Frame(sp_cv)
        sp_win = sp_cv.create_window((0, 0), window=self._sp_inner, anchor="nw")
        self._sp_inner.bind("<Configure>",
                            lambda e: sp_cv.configure(scrollregion=sp_cv.bbox("all")))
        sp_cv.bind("<Configure>",
                   lambda e: sp_cv.itemconfig(sp_win, width=e.width))

        ttk.Separator(self).pack(fill=X, pady=2)

        # ── Properties strip ─────────────────────────────────────────
        prop_cv = tk.Canvas(self, highlightthickness=0, height=210, bg="#1c1c2e")
        prop_sb = ttk.Scrollbar(self, orient=VERTICAL, command=prop_cv.yview)
        prop_cv.configure(yscrollcommand=prop_sb.set)
        prop_sb.pack(side=RIGHT, fill=Y)
        prop_cv.pack(fill=X)
        self._prop_frame = ttk.Frame(prop_cv, padding=(4, 4))
        prop_win = prop_cv.create_window((0, 0), window=self._prop_frame, anchor="nw")
        self._prop_frame.bind("<Configure>",
            lambda e: prop_cv.configure(scrollregion=prop_cv.bbox("all")))
        prop_cv.bind("<Configure>",
            lambda e: prop_cv.itemconfig(prop_win, width=e.width))

        ttk.Separator(self).pack(fill=X, pady=2)

        # ── Asset Library ────────────────────────────────────────────
        al_hdr = ttk.Frame(self, padding=(4, 2))
        al_hdr.pack(fill=X)
        ttk.Label(al_hdr, text="Assets", font=("Segoe UI", 9, "bold")).pack(side=LEFT)
        ttk.Button(al_hdr, text="Import", bootstyle="info-outline",
                   command=self._import_asset, width=7).pack(side=RIGHT)

        al_frame = ttk.Frame(self)
        al_frame.pack(fill=X, pady=(0, 4))
        al_cv = tk.Canvas(al_frame, bg="#111122", highlightthickness=0, height=110)
        al_sb = ttk.Scrollbar(al_frame, orient=VERTICAL, command=al_cv.yview)
        al_cv.configure(yscrollcommand=al_sb.set)
        al_sb.pack(side=RIGHT, fill=Y)
        al_cv.pack(fill=BOTH, expand=True)
        self._al_inner = ttk.Frame(al_cv)
        al_win = al_cv.create_window((0, 0), window=self._al_inner, anchor="nw")
        self._al_inner.bind("<Configure>",
            lambda e: al_cv.configure(scrollregion=al_cv.bbox("all")))
        al_cv.bind("<Configure>",
            lambda e: al_cv.itemconfig(al_win, width=e.width))

        self.refresh()

    # ── Refresh ──────────────────────────────────────────────────────────

    def refresh(self):
        for w in self._sp_inner.winfo_children():
            w.destroy()
        for sp in (self._screen.get("sprites", []) if self._screen else []):
            self._make_sprite_tile(sp)
        self._build_property_strip()
        self._build_asset_list()

    def _build_asset_list(self):
        for w in self._al_inner.winfo_children():
            w.destroy()
        assets = self._project.get("assets", {})
        if not assets:
            ttk.Label(self._al_inner, text="No assets yet.",
                      foreground="#555", font=("Segoe UI", 8),
                      padding=(4, 4)).pack(anchor=W)
            return
        for logical, _ in sorted(assets.items()):
            row = ttk.Frame(self._al_inner)
            row.pack(fill=X, padx=2, pady=1)
            thumb = self._get_thumb_by_key(logical, size=20)
            if thumb:
                lbl = tk.Label(row, image=thumb, bg="#111122")
                lbl.image = thumb
                lbl.pack(side=LEFT, padx=(2, 4))
            short = os.path.basename(logical)
            ttk.Label(row, text=short, font=("Consolas", 8),
                      foreground="#8ab4d4").pack(side=LEFT, fill=X, expand=True)
            # Apply to selected sprite
            ttk.Button(row, text="Use", bootstyle="info-link",
                       command=lambda k=logical: self._apply_asset(k),
                       width=4).pack(side=RIGHT)
            ttk.Button(row, text="✕", bootstyle="danger-link",
                       command=lambda k=logical: self._delete_asset(k),
                       width=2).pack(side=RIGHT)

    def _get_thumb_by_key(self, key, size=20):
        if key in self._thumb_cache and size in str(self._thumb_cache.get((key, size))):
            pass
        cache_key = (key, size)
        if cache_key in self._thumb_cache:
            return self._thumb_cache[cache_key]
        b64 = self._project.get("assets", {}).get(key)
        if not b64:
            return None
        try:
            raw   = base64.b64decode(b64)
            img   = Image.open(io.BytesIO(raw)).convert("RGBA").resize(
                        (size, size), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self._thumb_cache[cache_key] = photo
            return photo
        except Exception:
            return None

    def _apply_asset(self, key):
        if self._selected_sprite:
            self._selected_sprite["asset"] = key
            self._thumb_cache.pop((self._selected_sprite["id"], 48), None)
            self.refresh()

    def _delete_asset(self, key):
        if messagebox.askyesno("Delete Asset", f"Remove '{key}' from project?",
                               parent=self):
            self._project.get("assets", {}).pop(key, None)
            # Clear any sprite using it
            for s in self._project.get("screens", []):
                for sp in s.get("sprites", []):
                    if sp.get("asset") == key:
                        sp["asset"] = None
            self._thumb_cache.clear()
            self.refresh()

    def _import_asset(self):
        paths = filedialog.askopenfilenames(
            title="Import Asset(s)",
            filetypes=[("Images", "*.png;*.jpg;*.bmp;*.jpeg"), ("All", "*.*")])
        if not paths:
            return
        for path in paths:
            fname   = os.path.basename(path)
            logical = f"sprites/{fname}"
            embed_asset(self._project, logical, path)
        self.refresh()

    # ── Sprite tiles ─────────────────────────────────────────────────────

    def _make_sprite_tile(self, sprite):
        selected = (sprite is self._selected_sprite)
        bg       = "#2d5a9e" if selected else "#2a2a3e"
        border   = "#4a90d9" if selected else "#3a3a5e"
        outer    = tk.Frame(self._sp_inner, bg=border, padx=1, pady=1, cursor="hand2")
        outer.pack(fill=X, padx=6, pady=2)
        tile     = tk.Frame(outer, bg=bg, padx=6, pady=5)
        tile.pack(fill=X)

        # Thumbnail
        thumb = self._get_thumb_by_key(sprite.get("asset", ""), size=40)
        if not thumb and sprite.get("asset"):
            thumb = self._get_thumb_by_key(sprite["asset"], size=40)
        if thumb:
            img_lbl = tk.Label(tile, image=thumb, bg=bg)
            img_lbl.image = thumb
            img_lbl.pack(side=LEFT, padx=(0, 6))
        else:
            tk.Label(tile, text="?", bg="#4a90d9", fg="white",
                     width=3, height=2, font=("Segoe UI", 8, "bold")).pack(
                side=LEFT, padx=(0, 6))

        info = tk.Frame(tile, bg=bg)
        info.pack(side=LEFT, fill=X, expand=True)
        nc = "#fff" if selected else "#e0e0e0"
        tk.Label(info, text=sprite["name"], bg=bg, fg=nc,
                 font=("Segoe UI", 9, "bold"), anchor=W).pack(anchor=W)
        tk.Label(info, text=f"x={sprite.get('x',0.5):.2f}  y={sprite.get('y',0.5):.2f}",
                 bg=bg, fg="#8ab4d4", font=("Consolas", 7)).pack(anchor=W)
        eye = "● vis" if sprite.get("visible", True) else "○ hid"
        tk.Label(info, text=eye, bg=bg,
                 fg="#6ecf6e" if sprite.get("visible", True) else "#888",
                 font=("Segoe UI", 7)).pack(anchor=W)

        for w in [outer, tile] + tile.winfo_children() + info.winfo_children():
            w.bind("<Button-1>", lambda e, s=sprite: self._select(s))

    def _get_thumb(self, sprite, size=40):
        return self._get_thumb_by_key(sprite.get("asset", ""), size)

    def _select(self, sprite):
        self._selected_sprite = sprite
        self._on_sprite_select(sprite)
        self.refresh()

    # ── Property strip ────────────────────────────────────────────────────

    def _build_property_strip(self):
        for w in self._prop_frame.winfo_children():
            w.destroy()
        s = self._selected_sprite
        if not s:
            ttk.Label(self._prop_frame, text="Select a sprite",
                      foreground="#666", font=("Segoe UI", 9),
                      padding=(4, 6)).pack(anchor=W)
            return

        def _redraw():
            self._on_sprite_select(s)

        # Name
        nr = ttk.Frame(self._prop_frame, padding=(0, 2))
        nr.pack(fill=X)
        ttk.Label(nr, text="Name", width=6, font=("Segoe UI", 9)).pack(side=LEFT)
        nv = tk.StringVar(value=s["name"])
        ne = ttk.Entry(nr, textvariable=nv)
        ne.pack(side=LEFT, fill=X, expand=True, padx=(4, 0))
        ne.bind("<Return>",   lambda e: s.update({"name": nv.get()}) or _redraw())
        ne.bind("<FocusOut>", lambda e: s.update({"name": nv.get()}) or _redraw())

        ttk.Separator(self._prop_frame).pack(fill=X, pady=2)

        # Position
        pf = ttk.Frame(self._prop_frame, padding=(0, 2))
        pf.pack(fill=X)
        ttk.Label(pf, text="X", width=3, font=("Segoe UI", 9)).grid(row=0, column=0, sticky=W)
        xv = tk.StringVar(value=f"{s.get('x',0.5):.3f}")
        ttk.Entry(pf, textvariable=xv, width=7).grid(row=0, column=1, padx=(2, 8))
        ttk.Label(pf, text="Y", width=3, font=("Segoe UI", 9)).grid(row=0, column=2, sticky=W)
        yv = tk.StringVar(value=f"{s.get('y',0.5):.3f}")
        ttk.Entry(pf, textvariable=yv, width=7).grid(row=0, column=3, padx=2)

        def _ap(*_):
            try: s["x"] = max(0.0, min(1.0, float(xv.get())))
            except ValueError: pass
            try: s["y"] = max(0.0, min(1.0, float(yv.get())))
            except ValueError: pass
            xv.set(f"{s['x']:.3f}"); yv.set(f"{s['y']:.3f}"); _redraw()

        for e in pf.winfo_children():
            e.bind("<Return>",   _ap)
            e.bind("<FocusOut>", _ap)
        pf.columnconfigure(1, weight=1); pf.columnconfigure(3, weight=1)

        ttk.Separator(self._prop_frame).pack(fill=X, pady=2)

        # Scale + Layer
        sf = ttk.Frame(self._prop_frame, padding=(0, 2))
        sf.pack(fill=X)
        ttk.Label(sf, text="Scale", width=6, font=("Segoe UI", 9)).grid(row=0, column=0, sticky=W)
        sv2 = tk.StringVar(value=f"{s.get('scale',1.0):.2f}")
        ttk.Entry(sf, textvariable=sv2, width=7).grid(row=0, column=1, padx=(2, 8))
        ttk.Label(sf, text="Layer", width=5, font=("Segoe UI", 9)).grid(row=0, column=2, sticky=W)
        lv = tk.StringVar(value=str(s.get("zorder", 0)))
        ttk.Entry(sf, textvariable=lv, width=5).grid(row=0, column=3, padx=2)

        def _asl(*_):
            try: s["scale"] = max(0.01, float(sv2.get()))
            except ValueError: pass
            try: s["zorder"] = int(lv.get())
            except ValueError: pass
            sv2.set(f"{s['scale']:.2f}"); lv.set(str(s.get("zorder",0))); _redraw()

        for e in sf.winfo_children():
            e.bind("<Return>",   _asl)
            e.bind("<FocusOut>", _asl)
        sf.columnconfigure(1, weight=1); sf.columnconfigure(3, weight=1)

        ttk.Separator(self._prop_frame).pack(fill=X, pady=2)

        # Visible toggle + action buttons
        af = ttk.Frame(self._prop_frame, padding=(0, 2))
        af.pack(fill=X)
        vis_v = tk.BooleanVar(value=s.get("visible", True))
        def _tvis():
            s["visible"] = vis_v.get(); _redraw()
        ttk.Checkbutton(af, text="Visible", variable=vis_v,
                        bootstyle="round-toggle", command=_tvis).pack(side=LEFT)
        ttk.Button(af, text="⧉ Clone", bootstyle="info-link",
                   command=self._clone_sprite, width=8).pack(side=RIGHT)
        ttk.Button(af, text="🗑 Delete", bootstyle="danger-link",
                   command=self._delete_sprite, width=8).pack(side=RIGHT)

    # ── Sprite actions ────────────────────────────────────────────────────

    def _add_sprite(self):
        AddSpriteDialog(self, self._project, self._screen, self._select)

    def _clone_sprite(self):
        if not self._selected_sprite:
            return
        import copy, uuid
        c2 = copy.deepcopy(self._selected_sprite)
        c2["id"]   = uuid.uuid4().hex[:12]
        c2["name"] = self._selected_sprite["name"] + "_clone"
        c2["x"]    = min(1.0, self._selected_sprite["x"] + 0.05)
        c2["y"]    = min(1.0, self._selected_sprite["y"] + 0.05)
        self._screen.setdefault("sprites", []).append(c2)
        self._select(c2)

    def _delete_sprite(self):
        if not self._selected_sprite:
            return
        if messagebox.askyesno("Delete",
                               f"Delete '{self._selected_sprite['name']}'?", parent=self):
            self._screen["sprites"].remove(self._selected_sprite)
            self._selected_sprite = None
            self._on_sprite_select(None)
            self.refresh()


class AddSpriteDialog(tk.Toplevel):
    def __init__(self, parent, project, screen, callback):
        super().__init__(parent)
        self.title("Add Sprite")
        self.resizable(False, False)
        center_window(self, 400, 240)
        self.grab_set()
        self._project  = project
        self._screen   = screen
        self._callback = callback
        self._img_path = None
        self._build()

    def _build(self):
        f = ttk.Frame(self, padding=(24, 18))
        f.pack(fill=BOTH, expand=True)

        ttk.Label(f, text="Sprite Name").grid(row=0, column=0, sticky=W, pady=8, padx=(0,12))
        self._name_var = tk.StringVar(value="Sprite1")
        ttk.Entry(f, textvariable=self._name_var, width=26).grid(
            row=0, column=1, columnspan=2, sticky=EW, pady=8)

        ttk.Label(f, text="Image").grid(row=1, column=0, sticky=W, pady=8, padx=(0,12))

        # Asset picker from project assets
        assets = list(self._project.get("assets", {}).keys())
        self._asset_var = tk.StringVar(value=assets[0] if assets else "")
        asset_cb = ttk.Combobox(f, textvariable=self._asset_var,
                                 values=assets, width=18, state="readonly")
        asset_cb.grid(row=1, column=1, sticky=EW, pady=8)

        ttk.Button(f, text="Import…", bootstyle="secondary-outline",
                   command=self._import_new, width=9).grid(
            row=1, column=2, padx=(6, 0), pady=8)

        f.columnconfigure(1, weight=1)

        btn_row = ttk.Frame(self, padding=(24, 4))
        btn_row.pack(fill=X)
        ttk.Button(btn_row, text="Cancel", bootstyle="secondary-outline",
                   command=self.destroy).pack(side=LEFT)
        ttk.Button(btn_row, text="Add Sprite ▸", bootstyle="success",
                   command=self._add).pack(side=RIGHT)

    def _import_new(self):
        path = filedialog.askopenfilename(
            title="Import Sprite Image",
            filetypes=[("PNG", "*.png"), ("Images", "*.png;*.jpg;*.bmp")])
        if path:
            fname   = os.path.basename(path)
            logical = f"sprites/{fname}"
            embed_asset(self._project, logical, path)
            assets = list(self._project.get("assets", {}).keys())
            self._asset_var.set(logical)
            # Update combobox values
            for w in self.winfo_children():
                self._refresh_combobox(w, assets)

    def _refresh_combobox(self, widget, assets):
        if isinstance(widget, ttk.Combobox):
            widget.configure(values=assets)
        for child in widget.winfo_children():
            self._refresh_combobox(child, assets)

    def _add(self):
        name  = self._name_var.get().strip() or "Sprite"
        asset = self._asset_var.get()
        sp    = new_sprite(name, project=self._project)
        if asset:
            sp["asset"] = asset
        self._screen.setdefault("sprites", []).append(sp)
        self.destroy()
        self._callback(sp)
