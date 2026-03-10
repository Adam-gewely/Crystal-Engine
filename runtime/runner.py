"""Crystal Engine - Launch compiled project, stream stdout/stderr."""
import os
import sys
import subprocess
import threading

from runtime.compiler import Compiler
from engine.constants import TEMP_DIR
from engine.utils import ensure_dir


class ProjectRunner:
    # Set on_output(line: str, level: str) to receive console lines.
    # level is one of: "info", "error", "warn"
    on_output = None

    def __init__(self, project: dict, filepath: str):
        self._project  = project
        self._filepath = filepath
        self._process  = None
        self._threads  = []

    def launch(self):
        compiler = Compiler(self._project)
        src      = compiler.compile()

        ensure_dir(TEMP_DIR)
        script_path = os.path.join(TEMP_DIR, "_crystal_run.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(src)

        self._process = subprocess.Popen(
            [sys.executable, "-u", script_path],
            cwd=TEMP_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._emit("info", f"▶  Game launched  (PID {self._process.pid})")

        t_out = threading.Thread(
            target=self._stream, args=(self._process.stdout, "info"), daemon=True)
        t_err = threading.Thread(
            target=self._stream, args=(self._process.stderr, "error"), daemon=True)
        t_out.start(); t_err.start()
        self._threads = [t_out, t_err]

    def _stream(self, pipe, level):
        try:
            for line in pipe:
                self._emit(level, line.rstrip())
        except Exception:
            pass
        finally:
            if level == "error" and self._process:
                rc = self._process.wait()
                msg = f"■  Game exited  (code {rc})" if rc != 0 else "■  Game finished"
                self._emit("warn" if rc != 0 else "info", msg)

    def _emit(self, level, line):
        if callable(self.on_output):
            self.on_output(line, level)

    def stop(self):
        if self._process and self._process.poll() is None:
            self._process.terminate()
            self._emit("warn", "■  Stopped by user")
        self._process = None

    @property
    def running(self):
        return self._process is not None and self._process.poll() is None
