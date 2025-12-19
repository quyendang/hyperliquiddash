import os

APP_TITLE = os.getenv("APP_TITLE", "HyperDash Lite")
DATABASE_URL = os.getenv("DATABASE_URL")
REFRESH_SNAPSHOT_SECONDS = int(os.getenv("REFRESH_SNAPSHOT_SECONDS", "30"))
UI_POLL_SECONDS = int(os.getenv("UI_POLL_SECONDS", "2"))

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required")
