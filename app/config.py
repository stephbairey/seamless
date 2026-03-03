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

# Gmail API (OAuth2)
GMAIL_CLIENT_ID = os.environ.get("GMAIL_CLIENT_ID", "")
GMAIL_CLIENT_SECRET = os.environ.get("GMAIL_CLIENT_SECRET", "")
GMAIL_REFRESH_TOKEN = os.environ.get("GMAIL_REFRESH_TOKEN", "")
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users"

# Google Calendar (separate refresh token per calendar, same OAuth app)
GCAL_LINGUAINKMEDIA_TOKEN = os.environ.get("GCAL_LINGUAINKMEDIA_TOKEN", "")
GCAL_MJBAIREY_TOKEN = os.environ.get("GCAL_MJBAIREY_TOKEN", "")
GCAL_STEPHBAIREY_TOKEN = os.environ.get("GCAL_STEPHBAIREY_TOKEN", "")

# Anthropic API (for reply drafting)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# File Management
INTAKE_DIR = Path(os.environ.get("INTAKE_DIR", "/intake"))
GDRIVE_DIR = Path(os.environ.get("GDRIVE_DIR", "/gdrive"))
SORT_LOG_FILE = DATA_DIR / "sort-history.json"
