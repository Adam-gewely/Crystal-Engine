"""Crystal Engine - Export project as a standalone Python/Pygame project."""
import os
import base64

from runtime.compiler import Compiler
from engine.utils import ensure_dir


class PythonExporter:
    """
    Exports a Crystal project to a directory as a self-contained
    Pygame Python project with assets extracted.
    """

    def __init__(self, project: dict):
        self._project = project

    def export(self, output_dir: str):
        p = self._project
        name = p.get("name", "crystal_game").replace(" ", "_")

        root = os.path.join(output_dir, name)
        ensure_dir(root)

        # Write assets
        assets_dir = os.path.join(root, "assets")
        ensure_dir(assets_dir)
        for logical, b64 in p.get("assets", {}).items():
            dest = os.path.join(assets_dir, logical.replace("/", os.sep))
            ensure_dir(os.path.dirname(dest))
            with open(dest, "wb") as f:
                f.write(base64.b64decode(b64))

        # Write main.py (modified to load assets from disk instead of base64)
        main_src = self._build_main_with_file_assets(root)
        with open(os.path.join(root, "main.py"), "w", encoding="utf-8") as f:
            f.write(main_src)

        # requirements.txt
        with open(os.path.join(root, "requirements.txt"), "w") as f:
            f.write("pygame>=2.5.0\n")

        # README
        with open(os.path.join(root, "README.md"), "w") as f:
            f.write(f"# {p.get('name', 'Crystal Game')}\\n\\n"
                    f"Run with: `python main.py`\\n\\n"
                    f"Requires: `pip install pygame`\\n")

        return root

    def _build_main_with_file_assets(self, root: str) -> str:
        """Compile but swap asset loader to use disk files."""
        compiler  = Compiler(self._project)
        full_src  = compiler.compile()

        # Replace the base64 asset section with file-based loading
        asset_header = (
            "import os\\n"
            "_ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')\\n\\n"
            "def _load_surface(name):\\n"
            "    path = os.path.join(_ASSET_DIR, *name.split('/'))\\n"
            "    if not os.path.exists(path): return None\\n"
            "    return pygame.image.load(path).convert_alpha()\\n"
        )

        # Find and replace asset loader section
        start_marker = "# ── Embedded assets"
        end_marker   = "def _find_sprite"
        s_idx = full_src.find(start_marker)
        e_idx = full_src.find(end_marker)
        if s_idx != -1 and e_idx != -1:
            full_src = full_src[:s_idx] + asset_header + "\\n" + full_src[e_idx:]
        return full_src
