"""Crystal Engine - Screen list sidebar panel with bg editing."""
import tkinter as tk
import tkinter.simpledialog
from tkinter import colorchooser, filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from engine.project_manager import new_screen, embed_asset
from engine.utils import center_window


class ScreenManager(ttk.Frame):
    """Left sidebar: screen list + per-screen background controls."""

    def __init__(self, parent, project, on_screen_select, **kw):
        super().__init__(parent, **kw)
        self._project          = project
        self._on_screen_select = on_screen_select
        self._selected         = None
        self._build()

    def _build(self):
        hdr = ttk.Frame(self, padding=(4, 4))
        hdr.pack(fill=X)
        ttk.Label(hdr, text="Screens", font=("Segoe UI", 10, "bold")).pack(side=LEFT)
        ttk.Button(hdr, text="+", bootstyle="success-outline", width=3,
                   command=self._add_screen).pack(side=RIGHT)

        self._listbox = tk.Listbox(self, selectmode=SINGLE,
                                    bg="#2a2a3e", fg="white",
                                    selectbackground="#4a90d9",
                                    font=("Segoe UI", 10), relief="flat",
                                    borderwidth=0, height=4,
                                    activestyle="none")
        self._listbox.pack(fill=X, padx=4)
        self._listbox.bind("<<ListboxSelect>>", self._on_select)

        # Rename / Delete
        btn_bar = ttk.Frame(self, padding=(4, 2))
        btn_bar.pack(fill=X)
        ttk.Button(btn_bar, text="Rename", bootstyle="secondary-outline",
                   command=self._rename_screen, width=8).pack(side=LEFT)
        ttk.Button(btn_bar, text="Delete", bootstyle="danger-outline",
                   command=self._delete_screen, width=8).pack(side=RIGHT)

        ttk.Separator(self).pack(fill=X, pady=4)

        # ── Background controls ───────────────────────────────────────
        bg_frame = ttk.Frame(self, padding=(6, 4))
        bg_frame.pack(fill=X)
        ttk.Label(bg_frame, text="Background",
                  font=("Segoe UI", 9, "bold")).pack(anchor=W, pady=(0, 4))

        # Color swatch + label
        row1 = ttk.Frame(bg_frame)
        row1.pack(fill=X, pady=2)
        ttk.Label(row1, text="Color", width=7, font=("Segoe UI", 9)).pack(side=LEFT)
        self._bg_swatch = tk.Label(row1, width=4, relief="solid", cursor="hand2",
                                    bg="#1a1a2e")
        self._bg_swatch.pack(side=LEFT, padx=(4, 4))
        self._bg_hex_var = tk.StringVar(value="#1a1a2e")
        bg_entry = ttk.Entry(row1, textvariable=self._bg_hex_var, width=9)
        bg_entry.pack(side=LEFT)
        bg_entry.bind("<Return>",   lambda e: self._apply_bg_color())
        bg_entry.bind("<FocusOut>", lambda e: self._apply_bg_color())
        self._bg_swatch.bind("<Button-1>", lambda e: self._pick_bg_color())

        # Image background
        row2 = ttk.Frame(bg_frame)
        row2.pack(fill=X, pady=2)
        ttk.Label(row2, text="Image", width=7, font=("Segoe UI", 9)).pack(side=LEFT)
        self._bg_img_var = tk.StringVar(value="None")
        ttk.Entry(row2, textvariable=self._bg_img_var, state="readonly",
                  width=11).pack(side=LEFT, padx=(4, 4))
        ttk.Button(row2, text="Browse", bootstyle="secondary-outline",
                   command=self._set_bg_image, width=7).pack(side=LEFT)
        ttk.Button(row2, text="✕", bootstyle="danger-link",
                   command=self._clear_bg_image, width=2).pack(side=LEFT)

        self.refresh()

    # ── Refresh ──────────────────────────────────────────────────────────

    def refresh(self):
        sel_name = self._selected.get("name") if self._selected else None
        self._listbox.delete(0, END)
        for screen in self._project.get("screens", []):
            tag = " ⧉" if screen.get("overlay") else ""
            self._listbox.insert(END, screen["name"] + tag)

        screens = self._project.get("screens", [])
        restored = False
        for i, s in enumerate(screens):
            if s.get("name") == sel_name:
                self._listbox.selection_set(i)
                self._listbox.activate(i)
                self._selected = s
                self._refresh_bg_ui()
                restored = True
                break
        if not restored and screens:
            self._listbox.selection_set(0)
            self._selected = screens[0]
            self._on_screen_select(screens[0])
            self._refresh_bg_ui()

    def _refresh_bg_ui(self):
        s = self._selected
        if not s:
            return
        col = s.get("bg_color", "#1a1a2e")
        self._bg_hex_var.set(col)
        try:
            self._bg_swatch.configure(bg=col)
        except Exception:
            pass
        asset = s.get("bg_asset") or "None"
        if asset and asset != "None":
            import os
            self._bg_img_var.set(os.path.basename(asset))
        else:
            self._bg_img_var.set("None")

    # ── Screen list events ────────────────────────────────────────────────

    def _on_select(self, _=None):
        sel = self._listbox.curselection()
        if not sel:
            return
        self._selected = self._project["screens"][sel[0]]
        self._refresh_bg_ui()
        self._on_screen_select(self._selected)

    def _add_screen(self):
        AddScreenDialog(self, self._project, self._on_added)

    def _on_added(self, screen):
        self._project["screens"].append(screen)
        self.refresh()
        self._on_screen_select(screen)

    def _rename_screen(self):
        if not self._selected:
            return
        name = tkinter.simpledialog.askstring(
            "Rename", "New screen name:",
            initialvalue=self._selected["name"], parent=self)
        if name and name.strip():
            self._selected["name"] = name.strip()
            self.refresh()

    def _delete_screen(self):
        if not self._selected:
            return
        from tkinter import messagebox
        if len(self._project["screens"]) <= 1:
            messagebox.showwarning("Cannot Delete",
                                   "A project needs at least one screen.")
            return
        if messagebox.askyesno("Delete Screen",
                               f"Delete '{self._selected['name']}'?", parent=self):
            self._project["screens"].remove(self._selected)
            self._selected = None
            self.refresh()

    # ── Background controls ───────────────────────────────────────────────

    def _pick_bg_color(self):
        if not self._selected:
            return
        col = colorchooser.askcolor(
            color=self._selected.get("bg_color", "#1a1a2e"), parent=self)[1]
        if col:
            self._selected["bg_color"] = col
            self._refresh_bg_ui()
            self._on_screen_select(self._selected)

    def _apply_bg_color(self):
        if not self._selected:
            return
        col = self._bg_hex_var.get().strip()
        if col.startswith("#") and len(col) in (4, 7):
            try:
                self._bg_swatch.configure(bg=col)
                self._selected["bg_color"] = col
                self._on_screen_select(self._selected)
            except Exception:
                pass

    def _set_bg_image(self):
        if not self._selected:
            return
        path = filedialog.askopenfilename(
            title="Background Image",
            filetypes=[("Image", "*.png;*.jpg;*.bmp;*.jpeg"), ("All", "*.*")])
        if not path:
            return
        import os
        fname   = os.path.basename(path)
        logical = f"backgrounds/{fname}"
        embed_asset(self._project, logical, path)
        self._selected["bg_asset"] = logical
        self._refresh_bg_ui()
        self._on_screen_select(self._selected)

    def _clear_bg_image(self):
        if self._selected:
            self._selected["bg_asset"] = None
            self._refresh_bg_ui()
            self._on_screen_select(self._selected)


class AddScreenDialog(tk.Toplevel):
    def __init__(self, parent, project, callback):
        super().__init__(parent)
        self.title("Add Screen")
        self.resizable(False, False)
        center_window(self, 380, 280)
        self.grab_set()
        self._project  = project
        self._callback = callback
        self._build()

    def _build(self):
        f = ttk.Frame(self, padding=20)
        f.pack(fill=BOTH, expand=True)
        ttk.Label(f, text="Screen Name").grid(row=0, column=0, sticky=W, pady=6)
        self._name_var = tk.StringVar(value="Screen2")
        ttk.Entry(f, textvariable=self._name_var, width=24).grid(
            row=0, column=1, sticky=EW, pady=6)
        self._overlay_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="Overlay screen",
                        variable=self._overlay_var,
                        bootstyle="round-toggle",
                        command=self._toggle_overlay).grid(
            row=1, column=0, columnspan=2, sticky=W, pady=6)
        ttk.Label(f, text="Bound to screen").grid(row=2, column=0, sticky=W, pady=6)
        screen_names = [s["name"] for s in project.get("screens", [])]
        self._bound_var = tk.StringVar(value=screen_names[0] if screen_names else "")
        self._bound_cb  = ttk.Combobox(f, textvariable=self._bound_var,
                                        values=screen_names, width=20, state="disabled")
        self._bound_cb.grid(row=2, column=1, sticky=EW, pady=6)
        f.columnconfigure(1, weight=1)
        btns = ttk.Frame(self, padding=(20, 8))
        btns.pack(fill=X)
        ttk.Button(btns, text="Cancel", bootstyle="secondary-outline",
                   command=self.destroy).pack(side=LEFT)
        ttk.Button(btns, text="Add", bootstyle="success",
                   command=self._add).pack(side=RIGHT)

    def _toggle_overlay(self):
        state = "readonly" if self._overlay_var.get() else "disabled"
        self._bound_cb.configure(state=state)

    def _add(self):
        name    = self._name_var.get().strip()
        overlay = self._overlay_var.get()
        bound   = self._bound_var.get() if overlay else None
        if not name:
            return
        bound_id = None
        if bound:
            for s in self._project.get("screens", []):
                if s["name"] == bound:
                    bound_id = s["id"]
                    break
        screen = new_screen(name, overlay=overlay, bound_to=bound_id)
        self.destroy()
        self._callback(screen)
