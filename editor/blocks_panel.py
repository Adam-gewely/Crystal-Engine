"""Crystal Engine - Block scripting panel with named scripts."""
import tkinter as tk
from tkinter import colorchooser
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from engine.constants import BLOCK_CATEGORIES, CATEGORY_COLORS
from editor.block_definitions import BLOCKS_BY_CATEGORY, get_block, render_block_label


# Hooks that fire without needing a key sub-field
SIMPLE_HOOKS = {
    "on_start", "on_update", "on_screen_load",
    "on_click", "on_any_key", "on_collision", "on_timer",
}
KEY_HOOKS   = {"on_key", "on_key_up", "on_key_hold"}
TIMER_HOOKS = {"on_timer"}


class BlocksPanel(ttk.Frame):
    """Right panel: block palette + script editor for selected sprite/screen."""

    def __init__(self, parent, project, **kw):
        super().__init__(parent, **kw)
        self._project = project
        self._target  = None
        self._scripts = []
        self._sel_idx = 0
        self._build()

    # ── Layout ────────────────────────────────────────────────────────────

    def _build(self):
        # Header bar
        hdr = ttk.Frame(self, padding=(6, 4))
        hdr.pack(fill=X)
        self._title_lbl = ttk.Label(hdr, text="Scripts",
                                     font=("Segoe UI", 11, "bold"))
        self._title_lbl.pack(side=LEFT)
        ttk.Button(hdr, text="+ Script", bootstyle="success-outline",
                   command=self._add_script, width=9).pack(side=RIGHT)

        # Script tab row
        self._tab_frame = ttk.Frame(self)
        self._tab_frame.pack(fill=X, padx=4)

        ttk.Separator(self).pack(fill=X)

        # Horizontal split: palette | script editor
        paned = tk.PanedWindow(self, orient=HORIZONTAL, bg="#1c1c2e", sashwidth=4)
        paned.pack(fill=BOTH, expand=True)

        pal = ttk.Frame(paned, width=200)
        paned.add(pal)
        self._build_palette(pal)

        scr = ttk.Frame(paned)
        paned.add(scr)
        self._build_script_area(scr)

    def _build_palette(self, parent):
        ttk.Label(parent, text="Block Palette",
                  font=("Segoe UI", 9, "bold"), padding=(4, 4)).pack(anchor=W)

        cv = tk.Canvas(parent, bg="#1a1a2e", highlightthickness=0)
        sb = ttk.Scrollbar(parent, orient=VERTICAL, command=cv.yview)
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        cv.pack(fill=BOTH, expand=True)

        inner = ttk.Frame(cv)
        win = cv.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>",    lambda e: cv.itemconfig(win, width=e.width))
        cv.bind("<MouseWheel>",   lambda e: cv.yview_scroll(-1*(e.delta//120), "units"))

        for cat in BLOCK_CATEGORIES:
            color  = CATEGORY_COLORS.get(cat, "#555")
            blocks = BLOCKS_BY_CATEGORY.get(cat, [])
            if not blocks:
                continue
            hdr = tk.Frame(inner, bg=color)
            hdr.pack(fill=X, pady=(8, 1), padx=3)
            tk.Label(hdr, text=f"  {cat}", bg=color, fg="white",
                     font=("Segoe UI", 9, "bold"), padx=6, pady=4).pack(anchor=W, fill=X)

            for blk in blocks:
                import re as _re
                disp = _re.sub(r"\\{[^}]+\\}", "…", blk["label"])
                lbl = tk.Label(inner, text="  " + disp,
                               bg="#252535", fg="#d0d0e8",
                               font=("Segoe UI", 9), padx=8, pady=4,
                               relief="flat", cursor="hand2", anchor=W, wraplength=175)
                lbl.pack(fill=X, padx=3, pady=1)
                lbl.bind("<Button-1>", lambda e, b=blk: self._on_palette_click(b))
                lbl.bind("<Enter>",    lambda e, col=color, w=lbl: w.configure(bg=col, fg="white"))
                lbl.bind("<Leave>",    lambda e, w=lbl:            w.configure(bg="#252535", fg="#d0d0e8"))

    def _build_script_area(self, parent):
        cv = tk.Canvas(parent, bg="#1c1c2e", highlightthickness=0)
        sb = ttk.Scrollbar(parent, orient=VERTICAL, command=cv.yview)
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        cv.pack(fill=BOTH, expand=True)

        self._script_cv    = cv
        self._script_inner = ttk.Frame(cv)
        self._script_win   = cv.create_window((0, 0), window=self._script_inner, anchor="nw")
        self._script_inner.bind("<Configure>",
            lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>",
            lambda e: cv.itemconfig(self._script_win, width=e.width))
        cv.bind("<MouseWheel>",
            lambda e: cv.yview_scroll(-1*(e.delta//120), "units"))

    # ── Public API ────────────────────────────────────────────────────────

    def set_target(self, target):
        self._target  = target
        self._scripts = (target.get("scripts", []) if target else [])
        self._sel_idx = 0
        label = target.get("name", "Scripts") if target else "Scripts"
        self._title_lbl.configure(text=f"Scripts — {label}")
        self._refresh_tabs()
        self._refresh_script_view()

    # ── Tabs ──────────────────────────────────────────────────────────────

    def _refresh_tabs(self):
        for w in self._tab_frame.winfo_children():
            w.destroy()
        for i, script in enumerate(self._scripts):
            name  = script.get("name") or script.get("hook", "script")
            hook  = script.get("hook", "on_start")
            color = CATEGORY_COLORS.get("Events", "#e74c3c")
            bg    = color if i == self._sel_idx else "#2a2a3e"
            lbl   = tk.Label(self._tab_frame, text=name,
                             bg=bg, fg="white", font=("Segoe UI", 8),
                             padx=8, pady=3, relief="flat", cursor="hand2")
            lbl.pack(side=LEFT, padx=2, pady=2)
            lbl.bind("<Button-1>", lambda e, idx=i: self._select_tab(idx))
            lbl.bind("<Button-3>", lambda e, idx=i: self._rename_tab(idx, e))

    def _select_tab(self, idx):
        self._sel_idx = idx
        self._refresh_tabs()
        self._refresh_script_view()

    def _rename_tab(self, idx, event):
        import tkinter.simpledialog
        script = self._scripts[idx]
        cur    = script.get("name") or script.get("hook", "script")
        name   = tkinter.simpledialog.askstring("Rename Script", "Script name:",
                                                 initialvalue=cur, parent=self)
        if name and name.strip():
            script["name"] = name.strip()
            self._refresh_tabs()

    def _add_script(self):
        if not self._target:
            return
        hook   = "on_start"
        script = {"name": f"Script {len(self._scripts)+1}",
                  "hook": hook, "key": "", "target": "",
                  "interval": "1.0", "blocks": []}
        self._target.setdefault("scripts", []).append(script)
        self._scripts = self._target["scripts"]
        self._sel_idx = len(self._scripts) - 1
        self._refresh_tabs()
        self._refresh_script_view()

    # ── Script view ───────────────────────────────────────────────────────

    def _refresh_script_view(self):
        for w in self._script_inner.winfo_children():
            w.destroy()

        if not self._scripts:
            ttk.Label(self._script_inner, text="No scripts yet.\nClick '+ Script' to add one.",
                      foreground="#666", font=("Segoe UI", 9), padding=(16, 16),
                      justify=CENTER).pack(expand=True)
            return

        if self._sel_idx >= len(self._scripts):
            self._sel_idx = 0

        script = self._scripts[self._sel_idx]

        # ── Script header ─────────────────────────────────────────────
        hdr = ttk.Frame(self._script_inner, padding=(6, 6))
        hdr.pack(fill=X)

        # Name field
        ttk.Label(hdr, text="Name:", font=("Segoe UI", 9)).pack(side=LEFT)
        name_var = tk.StringVar(value=script.get("name", ""))
        name_e   = ttk.Entry(hdr, textvariable=name_var, width=14)
        name_e.pack(side=LEFT, padx=(4, 12))
        name_var.trace_add("write", lambda *_, sv=name_var, s=script:
                           s.update({"name": sv.get()}) or self._refresh_tabs())

        # Hook selector
        ttk.Label(hdr, text="Trigger:", font=("Segoe UI", 9)).pack(side=LEFT)
        hook_var = tk.StringVar(value=script.get("hook", "on_start"))
        hook_opts = [
            "on_start", "on_update", "on_screen_load",
            "on_key", "on_key_up", "on_key_hold", "on_any_key",
            "on_click", "on_collision", "on_timer",
        ]
        hook_cb = ttk.Combobox(hdr, textvariable=hook_var,
                                values=hook_opts, width=14, state="readonly")
        hook_cb.pack(side=LEFT, padx=(4, 6))

        # Sub-field area (key / interval / target)
        sub = ttk.Frame(hdr)
        sub.pack(side=LEFT, padx=4)

        def _refresh_sub(*_):
            for w in sub.winfo_children():
                w.destroy()
            h = hook_var.get()
            script["hook"] = h
            self._refresh_tabs()
            if h in KEY_HOOKS:
                ttk.Label(sub, text="key:", font=("Segoe UI", 9)).pack(side=LEFT)
                kv = tk.StringVar(value=script.get("key", "space"))
                ke = ttk.Entry(sub, textvariable=kv, width=10)
                ke.pack(side=LEFT, padx=2)
                kv.trace_add("write", lambda *_, sv=kv: script.update({"key": sv.get()}))
            elif h == "on_timer":
                ttk.Label(sub, text="every:", font=("Segoe UI", 9)).pack(side=LEFT)
                tv = tk.StringVar(value=str(script.get("interval", "1.0")))
                te = ttk.Entry(sub, textvariable=tv, width=6)
                te.pack(side=LEFT, padx=2)
                ttk.Label(sub, text="s", font=("Segoe UI", 9)).pack(side=LEFT)
                tv.trace_add("write", lambda *_, sv=tv: script.update({"interval": sv.get()}))
            elif h == "on_collision":
                ttk.Label(sub, text="with:", font=("Segoe UI", 9)).pack(side=LEFT)
                opts = self._get_options("sprite")
                cv2  = tk.StringVar(value=script.get("target", ""))
                ttk.Combobox(sub, textvariable=cv2, values=opts, width=12
                             ).pack(side=LEFT, padx=2)
                cv2.trace_add("write", lambda *_, sv=cv2: script.update({"target": sv.get()}))

        hook_cb.bind("<<ComboboxSelected>>", _refresh_sub)
        _refresh_sub()

        ttk.Button(hdr, text="🗑 Delete", bootstyle="danger-link",
                   command=self._delete_current_script).pack(side=RIGHT)

        ttk.Separator(self._script_inner).pack(fill=X)

        # ── Block rows ────────────────────────────────────────────────
        blocks = script.setdefault("blocks", [])
        for i, inst in enumerate(blocks):
            self._render_block_row(self._script_inner, blocks, i, inst)

        ttk.Label(self._script_inner, text="↓  click palette to add blocks",
                  foreground="#555", font=("Segoe UI", 8), padding=(8, 6)).pack()

    def _render_block_row(self, parent, blocks_list, idx, block_inst):
        block_def = get_block(block_inst.get("id", ""))
        if not block_def:
            return

        cat   = block_def.get("category", "Python")
        color = CATEGORY_COLORS.get(cat, "#555")

        row = tk.Frame(parent, bg=color, padx=8, pady=6, cursor="hand2")
        row.pack(fill=X, padx=8, pady=2)

        # Build label + param inputs inline
        label  = block_def["label"]
        parts  = label.split("{")
        lf     = tk.Frame(row, bg=color)
        lf.pack(side=LEFT, fill=X, expand=True)

        tk.Label(lf, text=parts[0].rstrip(), bg=color, fg="white",
                 font=("Segoe UI", 9)).pack(side=LEFT)

        for part in parts[1:]:
            if "}" not in part:
                continue
            param_name, rest = part.split("}", 1)
            param_def = next((p for p in block_def.get("params", [])
                              if p["name"] == param_name), None)
            if not param_def:
                continue
            ptype    = param_def.get("type", "string")
            pdefault = block_inst["params"].get(param_name, param_def.get("default", ""))
            pvar     = tk.StringVar(value=str(pdefault))
            block_inst["params"][param_name] = str(pdefault)
            pvar.trace_add("write", lambda *_, sv=pvar, bi=block_inst, pn=param_name:
                           bi["params"].update({pn: sv.get()}))

            if ptype == "color":
                sw = tk.Label(lf, bg=str(pdefault) if pdefault else "#ffffff",
                              width=3, relief="solid", cursor="hand2")
                sw.pack(side=LEFT, padx=2)
                def _pick(e, sv=pvar, w=sw, bi=block_inst, pn=param_name):
                    col = colorchooser.askcolor(color=sv.get())[1]
                    if col:
                        sv.set(col); w.configure(bg=col)
                        bi["params"][pn] = col
                sw.bind("<Button-1>", _pick)
            elif ptype in ("var", "sprite", "screen"):
                opts = self._get_options(ptype)
                cb = ttk.Combobox(lf, textvariable=pvar, values=opts,
                                  width=10, font=("Segoe UI", 9))
                cb.pack(side=LEFT, padx=2)
            else:
                width = 7 if ptype == "number" else 13
                ttk.Entry(lf, textvariable=pvar, width=width,
                          font=("Segoe UI", 9)).pack(side=LEFT, padx=2)

            if rest.strip():
                tk.Label(lf, text=" " + rest.lstrip(), bg=color, fg="white",
                         font=("Segoe UI", 9)).pack(side=LEFT)

        # Controls
        ctrl = tk.Frame(row, bg=color)
        ctrl.pack(side=RIGHT)
        for text, cmd in [
            ("▲", lambda bl=blocks_list, i=idx: self._move(bl, i, -1)),
            ("▼", lambda bl=blocks_list, i=idx: self._move(bl, i,  1)),
            ("✕", lambda bl=blocks_list, i=idx: self._del_block(bl, i)),
        ]:
            lbl = tk.Label(ctrl, text=text, bg=color,
                           fg="#ffaaaa" if text == "✕" else "white",
                           font=("Segoe UI", 9, "bold"), padx=4, cursor="hand2")
            lbl.pack(side=LEFT)
            lbl.bind("<Button-1>", lambda e, fn=cmd: fn())

    # ── Helpers ───────────────────────────────────────────────────────────

    def _move(self, bl, i, delta):
        j = i + delta
        if 0 <= j < len(bl):
            bl[i], bl[j] = bl[j], bl[i]
            self._refresh_script_view()

    def _del_block(self, bl, i):
        del bl[i]
        self._refresh_script_view()

    def _delete_current_script(self):
        if self._scripts:
            del self._scripts[self._sel_idx]
            self._sel_idx = max(0, self._sel_idx - 1)
            if self._target:
                self._target["scripts"] = self._scripts
            self._refresh_tabs()
            self._refresh_script_view()

    def _get_options(self, ptype):
        p = self._project
        if ptype == "var":
            opts = list(p.get("global_vars", {}).keys())
            for s in p.get("screens", []):
                opts += list(s.get("variables", {}).keys())
            return list(dict.fromkeys(opts))
        if ptype == "sprite":
            for s in p.get("screens", []):
                return [sp["name"] for sp in s.get("sprites", [])]
        if ptype == "screen":
            return [s["name"] for s in p.get("screens", [])]
        return []

    def _on_palette_click(self, block_def):
        if not self._scripts:
            self._add_script()
        script = self._scripts[self._sel_idx]
        inst   = {"id": block_def["id"],
                  "params": {p["name"]: p.get("default", "")
                              for p in block_def.get("params", [])}}
        script.setdefault("blocks", []).append(inst)
        self._refresh_script_view()


import tkinter.simpledialog
