import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"

# App settings
APP_TITLE = "Seamless Dashboard"
APP_PORT = 8420

# ClickUp API
CLICKUP_API_TOKEN = os.environ.get("CLICKUP_API_TOKEN", "")
CLICKUP_API_BASE = "https://api.clickup.com/api/v2"
CLICKUP_LIST_ID = "901318968458"
CLICKUP_WORKSPACE_ID = "90132317650"
CLICKUP_SPACE_ID = "90139879792"
