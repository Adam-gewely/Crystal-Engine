"""Crystal Engine - Utility helpers."""
import os
import tkinter as tk
from PIL import Image, ImageTk


def screen_fraction(root: tk.Tk, w_frac: float, h_frac: float):
    """Return (width, height) as integer pixel sizes from screen fractions."""
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    return int(sw * w_frac), int(sh * h_frac)


def center_window(win, w: int, h: int):
    """Center a window on screen."""
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")


def load_icon(path: str, size=(32, 32)):
    """Load and resize a PNG icon. Returns None if not found."""
    try:
        img = Image.open(path).resize(size, Image.LANCZOS).convert("RGBA")
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


def proportional_pos(canvas_w: int, canvas_h: int, px: float, py: float):
    """Convert proportional (0-1) position to pixel coords on canvas."""
    return int(canvas_w * px), int(canvas_h * py)


def pixel_to_proportion(canvas_w: int, canvas_h: int, x: int, y: int):
    """Convert canvas pixel coords to proportional (0-1) position."""
    return round(x / canvas_w, 4), round(y / canvas_h, 4)


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)
