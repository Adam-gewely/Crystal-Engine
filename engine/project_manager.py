"""Crystal Engine - Project serialisation/deserialisation using zstandard."""
import os
import io
import json
import base64
import zipfile
import tempfile
import shutil
import zstandard as zstd

from engine.constants import CRYSTAL_FILE_EXT, CRYSTAL_MAGIC, CRYSTAL_VERSION, TEMP_DIR
from engine.utils import ensure_dir


# ── Data Model ────────────────────────────────────────────────────────────────

def new_sprite(name="Sprite1", project=None):
    import os as _os, base64 as _b64
    sp = {
        "id":         _uid(),
        "name":       name,
        "asset":      None,
        "x":          0.5,
        "y":          0.5,
        "scale":      1.0,
        "visible":    True,
        "animations": {},
        "scripts":    [],
        "clones":     [],
        "zorder":     0,
        "tags":       [],
    }
    if project is not None:
        default_key = "sprites/__default__.png"
        if default_key not in project.get("assets", {}):
            _here = _os.path.dirname(_os.path.abspath(__file__))
            for _candidate in [
                _os.path.join(_here, "..", "assets", "icons", "default_sprite.png"),
                _os.path.join(_here, "assets", "icons", "default_sprite.png"),
            ]:
                if _os.path.exists(_candidate):
                    with open(_candidate, "rb") as _f:
                        project.setdefault("assets", {})[default_key] = (
                            _b64.b64encode(_f.read()).decode())
                    break
        if default_key in project.get("assets", {}):
            sp["asset"] = default_key
    return sp


def new_screen(name="Screen1", overlay=False, bound_to=None):
    return {
        "id":         _uid(),
        "name":       name,
        "overlay":    overlay,
        "bound_to":   bound_to,       # screen id for overlays
        "bg_color":   "#1a1a2e",
        "bg_asset":   None,
        "sprites":    [],
        "scripts":    [],             # screen-level event scripts
        "variables":  {},             # local variables
    }


def new_project(name="Untitled", title="My Game", width=1280, height=720, fps=60):
    return {
        "version":         CRYSTAL_VERSION,
        "name":            name,
        "window_title":    title,
        "width":           width,
        "height":          height,
        "fps":             fps,
        "bg_color":        "#1a1a2e",
        "global_vars":     {},
        "screens":         [new_screen("Main")],
        "assets":          {},        # logical_name -> base64 data
        "active_screen":   None,
    }


# ── Persistence ───────────────────────────────────────────────────────────────

def save_project(project: dict, filepath: str):
    """Serialize a project to a .crystal file (zstd-compressed zip)."""
    ensure_dir(os.path.dirname(os.path.abspath(filepath)))

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        meta = {k: v for k, v in project.items() if k != "assets"}
        zf.writestr("project.json", json.dumps(meta, indent=2))

        for name, b64data in project.get("assets", {}).items():
            raw = base64.b64decode(b64data)
            zf.writestr(f"assets/{name}", raw)

    raw_zip = buf.getvalue()
    cctx = zstd.ZstdCompressor(level=3)
    compressed = cctx.compress(raw_zip)

    with open(filepath, "wb") as f:
        f.write(CRYSTAL_MAGIC)
        f.write(compressed)


def load_project(filepath: str) -> dict:
    """Load a .crystal file and return the project dict."""
    with open(filepath, "rb") as f:
        magic = f.read(4)
        if magic != CRYSTAL_MAGIC:
            raise ValueError("Not a valid .crystal file")
        compressed = f.read()

    dctx = zstd.ZstdDecompressor()
    raw_zip = dctx.decompress(compressed)

    buf = io.BytesIO(raw_zip)
    project = {}
    with zipfile.ZipFile(buf, "r") as zf:
        project = json.loads(zf.read("project.json"))
        project["assets"] = {}
        for name in zf.namelist():
            if name.startswith("assets/"):
                logical = name[len("assets/"):]
                if logical:
                    project["assets"][logical] = base64.b64encode(
                        zf.read(name)
                    ).decode()

    return project


def extract_assets_to_temp(project: dict) -> str:
    """Extract all assets to a temp directory; return the path."""
    out = os.path.join(TEMP_DIR, project.get("name", "game"))
    ensure_dir(out)
    for name, b64 in project.get("assets", {}).items():
        dest = os.path.join(out, name)
        ensure_dir(os.path.dirname(dest))
        with open(dest, "wb") as f:
            f.write(base64.b64decode(b64))
    return out


def embed_asset(project: dict, logical_name: str, filepath: str):
    """Read a file from disk and embed it into the project as base64."""
    with open(filepath, "rb") as f:
        project["assets"][logical_name] = base64.b64encode(f.read()).decode()


# ── Helpers ───────────────────────────────────────────────────────────────────

import uuid
def _uid():
    return uuid.uuid4().hex[:12]
