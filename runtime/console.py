# Crystal Engine - Embedded console panel + detachable window
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import threading
import queue
import time


LEVEL_COLORS = {
    "info":  "#c8e6c9",
    "error": "#ef9a9a",
    "warn":  "#ffe082",
}
LEVEL_TAGS = {
    "info":  "tag_info",
    "error": "tag_error",
    "warn":  "tag_warn",
}


class ConsolePanel(ttk.Frame):
    # Shared queue: (line, level) tuples pushed from any thread
    _queue: queue.Queue = None

    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        ConsolePanel._queue = queue.Queue()
        self._detached_win  = None
        self._build()
        self._poll()

    # ── Build ──────────────────────────────────────────────────────

    def _build(self):
        # Top bar
        bar = ttk.Frame(self, padding=(6, 3))
        bar.pack(fill=X)
        ttk.Label(bar, text="Console", font=("Segoe UI", 10, "bold")).pack(side=LEFT)
        ttk.Button(bar, text="Clear",    bootstyle="secondary-link", width=6,
                   command=self._clear).pack(side=RIGHT)
        ttk.Button(bar, text="↗ Pop out", bootstyle="info-link", width=9,
                   command=self._detach).pack(side=RIGHT)
        ttk.Separator(self).pack(fill=X)

        # Text area
        self._text, self._sb = self._make_text_area(self)

    def _make_text_area(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill=BOTH, expand=True)

        sb = ttk.Scrollbar(frame, orient=VERTICAL)
        sb.pack(side=RIGHT, fill=Y)

        txt = tk.Text(frame, state="disabled", bg="#0d1117", fg="#c9d1d9",
                      font=("Consolas", 9), relief="flat",
                      yscrollcommand=sb.set, wrap=WORD,
                      selectbackground="#264f78")
        txt.pack(fill=BOTH, expand=True, side=LEFT)
        sb.configure(command=txt.yview)

        txt.tag_configure("tag_info",  foreground="#8bc34a")
        txt.tag_configure("tag_error", foreground="#ef5350")
        txt.tag_configure("tag_warn",  foreground="#ffca28")
        txt.tag_configure("tag_ts",    foreground="#546e7a")

        return txt, sb

    # ── Public API ─────────────────────────────────────────────────

    @classmethod
    def post(cls, line: str, level: str = "info"):
        if cls._queue is not None:
            cls._queue.put_nowait((line, level))

    def _poll(self):
        # Drain queue onto text widget (runs in Tkinter main thread via after())
        try:
            while True:
                line, level = ConsolePanel._queue.get_nowait()
                self._append(line, level)
        except queue.Empty:
            pass
        self.after(80, self._poll)

    def _append(self, line: str, level: str):
        tag  = LEVEL_TAGS.get(level, "tag_info")
        ts   = time.strftime("%H:%M:%S")

        for widget in self._get_text_widgets():
            widget.configure(state="normal")
            widget.insert(END, f"[{ts}] ", "tag_ts")
            widget.insert(END, line + "\n", tag)
            widget.see(END)
            widget.configure(state="disabled")

    def _get_text_widgets(self):
        widgets = [self._text]
        if self._detached_win and self._detached_win.winfo_exists():
            widgets.append(self._detached_win._text)
        return widgets

    def _clear(self):
        for w in self._get_text_widgets():
            w.configure(state="normal")
            w.delete("1.0", END)
            w.configure(state="disabled")

    # ── Detach ─────────────────────────────────────────────────────

    def _detach(self):
        if self._detached_win and self._detached_win.winfo_exists():
            self._detached_win.lift()
            return
        win = tk.Toplevel(self)
        win.title("Crystal — Console")
        win.geometry("760x340")
        win.configure(bg="#0d1117")

        top = ttk.Frame(win, padding=(6, 3))
        top.pack(fill=X)
        ttk.Label(top, text="Console", font=("Segoe UI", 10, "bold")).pack(side=LEFT)
        ttk.Button(top, text="Clear", bootstyle="secondary-link",
                   command=self._clear, width=6).pack(side=RIGHT)

        txt, sb = self._make_text_area(win)
        win._text = txt

        # Copy existing content
        existing = self._text.get("1.0", END)
        txt.configure(state="normal")
        txt.insert("1.0", existing)
        txt.see(END)
        txt.configure(state="disabled")

        self._detached_win = win
