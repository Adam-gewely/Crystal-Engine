"""Crystal Engine - Visual canvas for sprite placement."""
import os, base64, io
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk

from engine.utils import pixel_to_proportion, proportional_pos
from engine.constants import CANVAS_BG


class EditorCanvas(ttk.Frame):
    """
    Renders sprites onto a canvas. Sprites are draggable.
    Reports position changes back via on_sprite_moved(sprite, px, py).
    """

    def __init__(self, parent, project, screen, **kw):
        super().__init__(parent, **kw)
        self._project = project
        self._screen  = screen

        self._sprite_items        = {}
        self._sprite_images       = {}
        self._drag_start          = None
        self._drag_sprite         = None
        self._placeholder         = None
        self._selected_sprite_id  = None

        self.on_sprite_moved    = None
        self.on_sprite_selected = None

        self._build()

    def _build(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._canvas = tk.Canvas(self, bg=CANVAS_BG, cursor="crosshair",
                                  highlightthickness=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")

        hbar = ttk.Scrollbar(self, orient=HORIZONTAL,
                               command=self._canvas.xview)
        vbar = ttk.Scrollbar(self, orient=VERTICAL,
                               command=self._canvas.yview)
        self._canvas.configure(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        hbar.grid(row=1, column=0, sticky=EW)
        vbar.grid(row=0, column=1, sticky=NS)

        self._canvas.bind("<Configure>", self._on_resize)
        self._canvas.bind("<ButtonPress-1>",   self._on_press)
        self._canvas.bind("<B1-Motion>",        self._on_drag)
        self._canvas.bind("<ButtonRelease-1>",  self._on_release)

    def _on_resize(self, event):
        self.redraw()

    def set_screen(self, screen):
        self._screen = screen
        self._selected_sprite_id = None
        self.redraw()

    def set_selected_sprite(self, sprite):
        self._selected_sprite_id = sprite["id"] if sprite else None
        self.redraw()

    def redraw(self):
        cw = self._canvas.winfo_width()
        ch = self._canvas.winfo_height()
        if cw < 2 or ch < 2:
            return
        self._canvas.delete("all")
        self._sprite_items.clear()
        self._sprite_images.clear()

        # Background
        bg = self._screen.get("bg_color", CANVAS_BG)
        self._canvas.configure(bg=bg)

        # Grid
        step = max(max(cw, ch) // 20, 1)
        if cw > 1 and ch > 1:
            for x in range(0, cw, step):
                self._canvas.create_line(x, 0, x, ch, fill="#2d2d4a")
            for y in range(0, ch, step):
                self._canvas.create_line(0, y, cw, y, fill="#2d2d4a")

        # Sprites
        sprites = sorted(self._screen.get("sprites", []),
                         key=lambda s: s.get("zorder", 0))
        for sprite in sprites:
            if not sprite.get("visible", True):
                continue
            px, py = proportional_pos(cw, ch, sprite["x"], sprite["y"])
            img    = self._load_sprite_image(sprite, cw, ch)

            if img:
                item = self._canvas.create_image(px, py, image=img, anchor="center",
                                                  tags=("sprite", sprite["id"]))
                self._sprite_images[sprite["id"]] = img
            else:
                # Placeholder rectangle
                size = int(min(cw, ch) * 0.06)
                item = self._canvas.create_rectangle(
                    px - size, py - size, px + size, py + size,
                    fill="#4a90d9", outline="#6ab0f9", width=2,
                    tags=("sprite", sprite["id"]))

                self._canvas.create_text(px, py, text=sprite["name"][:6],
                                          fill="white", font=("Segoe UI", 7),
                                          tags=("sprite_label", sprite["id"]))

            self._sprite_items[sprite["id"]] = item

            # Selection highlight ring
            if sprite["id"] == self._selected_sprite_id:
                base = max(int(min(cw, ch) * 0.08 * sprite.get("scale", 1.0)), 20)
                self._canvas.create_rectangle(
                    px - base//2 - 3, py - base//2 - 3,
                    px + base//2 + 3, py + base//2 + 3,
                    outline="#4a90d9", width=2, dash=(6, 3))
                # Corner handles
                for cx2, cy2 in [(px - base//2, py - base//2),
                                  (px + base//2, py - base//2),
                                  (px - base//2, py + base//2),
                                  (px + base//2, py + base//2)]:
                    self._canvas.create_rectangle(
                        cx2 - 3, cy2 - 3, cx2 + 3, cy2 + 3,
                        fill="#4a90d9", outline="white")

    def _load_sprite_image(self, sprite, cw, ch):
        asset_key = sprite.get("asset")
        if not asset_key:
            return None
        b64 = self._project.get("assets", {}).get(asset_key)
        if not b64:
            return None
        try:
            raw  = base64.b64decode(b64)
            img  = Image.open(io.BytesIO(raw)).convert("RGBA")
            base = max(int(min(cw, ch) * 0.08), 32)
            scale = sprite.get("scale", 1.0)
            new_size = (max(1, int(base * scale)), max(1, int(base * scale)))
            img = img.resize(new_size, Image.LANCZOS)
            opacity = sprite.get("opacity", 100)
            if opacity < 100:
                r, g, b, a = img.split()
                a = a.point(lambda p: int(p * opacity / 100))
                img.putalpha(a)
            return ImageTk.PhotoImage(img)
        except Exception:
            return None

    def _find_sprite_at(self, x, y):
        items = self._canvas.find_overlapping(x-4, y-4, x+4, y+4)
        for item in reversed(items):
            tags = self._canvas.gettags(item)
            if "sprite" in tags:
                sid = tags[tags.index("sprite") + 1] if len(tags) > tags.index("sprite") + 1 else None
                if sid:
                    for s in self._screen.get("sprites", []):
                        if s["id"] == sid:
                            return s
        return None

    def _on_press(self, event):
        sprite = self._find_sprite_at(event.x, event.y)
        if sprite:
            self._drag_sprite = sprite
            self._drag_start  = (event.x, event.y)
            if self.on_sprite_selected:
                self.on_sprite_selected(sprite)

    def _on_drag(self, event):
        if not self._drag_sprite:
            return
        cw = max(self._canvas.winfo_width(), 2)
        ch = max(self._canvas.winfo_height(), 2)

        px, py = pixel_to_proportion(cw, ch, event.x, event.y)
        self._drag_sprite["x"] = max(0.0, min(1.0, px))
        self._drag_sprite["y"] = max(0.0, min(1.0, py))
        self.redraw()

    def _on_release(self, event):
        if self._drag_sprite and self.on_sprite_moved:
            self.on_sprite_moved(self._drag_sprite,
                                  self._drag_sprite["x"],
                                  self._drag_sprite["y"])
        self._drag_sprite = None
        self._drag_start  = None
