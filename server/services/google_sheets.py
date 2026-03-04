"""Async Google Sheets logging for analysis results."""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

from server.config import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class GoogleSheetsLogger:
    """Log analysis results to Google Sheets."""

    def __init__(self) -> None:
        self._client: gspread.Client | None = None
        self._sheet = None

    def _connect(self) -> bool:
        """Connect to Google Sheets using service account."""
        if self._client:
            return True

        creds_path = settings.google_sheets_credentials
        if not creds_path or not Path(creds_path).exists():
            logger.warning("Google Sheets credentials not configured")
            return False

        try:
            with open(creds_path) as f:
                sa_info = json.load(f)
            creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
            self._client = gspread.authorize(creds)

            if settings.google_sheets_id:
                self._sheet = self._client.open_by_key(settings.google_sheets_id)
            return True
        except Exception:
            logger.exception("Failed to connect to Google Sheets")
            return False

    def log_analysis(self, domain: str, score: int, grade: str, details: dict) -> bool:
        """Log an analysis result to Google Sheets."""
        if not self._connect() or not self._sheet:
            return False

        try:
            worksheet = self._sheet.sheet1
            row = [
                datetime.now(tz=UTC).isoformat(),
                domain,
                score,
                grade,
                json.dumps(details.get("category_scores", {})),
                str(details.get("site_blocked", False)),
                details.get("website_provider", ""),
                details.get("analysis_time", ""),
            ]
            worksheet.append_row(row)
            return True
        except Exception:
            logger.exception("Failed to log to Google Sheets")
            return False
