"""Crystal Engine - Constants and configuration."""

APP_NAME    = "Crystal Engine"
APP_VERSION = "1.0.0"

# UI proportions (fraction of screen)
LAUNCHER_W  = 0.55
LAUNCHER_H  = 0.65
EDITOR_W    = 0.90
EDITOR_H    = 0.88

# Editor layout proportions
SIDEBAR_W_FRAC    = 0.17   # left panel fraction of editor width
CANVAS_W_FRAC     = 0.52
BLOCKS_W_FRAC     = 0.31

# Canvas background
CANVAS_BG = "#1a1a2e"

# Block palette categories
BLOCK_CATEGORIES = [
    "Events",
    "Motion",
    "Appearance",
    "Screen",
    "Control",
    "Variables",
    "Lists",
    "Operators",
    "Sensing",
    "Drawing",
    "Sound",
    "Window",
    "Debug",
    "Network",
    "Python",
]

# Block category colors
CATEGORY_COLORS = {
    "Events":     "#e74c3c",
    "Motion":     "#3498db",
    "Appearance": "#9b59b6",
    "Screen":     "#c0392b",
    "Control":    "#f39c12",
    "Variables":  "#27ae60",
    "Lists":      "#16a085",
    "Operators":  "#2ecc71",
    "Sensing":    "#1abc9c",
    "Drawing":    "#8e44ad",
    "Sound":      "#e67e22",
    "Window":     "#1a6b8a",
    "Debug":      "#636e72",
    "Network":    "#4a90d9",
    "Python":     "#95a5a6",
}

# Default new-project settings
DEFAULT_TITLE      = "My Crystal Game"
DEFAULT_WIDTH      = 1280
DEFAULT_HEIGHT     = 720
DEFAULT_FPS        = 60
DEFAULT_BG_COLOR   = "#1a1a2e"

# Crystal file format
CRYSTAL_FILE_EXT    = ".crystal"
CRYSTAL_MAGIC       = b"CRYS"
CRYSTAL_VERSION     = 1

# Temp dir for decompressed assets
import tempfile, os
TEMP_DIR = os.path.join(tempfile.gettempdir(), "crystal_engine")
