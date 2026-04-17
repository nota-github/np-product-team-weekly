#!/usr/bin/env python3
"""Create the weekly daily-report Confluence page from a fixed ADF template.

The table layout, mention account IDs, space, and parent folder are all fixed
in code and template — only the five weekday dates are computed from today.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import requests

CONFLUENCE_BASE = "https://nota-dev.atlassian.net/wiki"
SPACE_ID = "951091308"
PARENT_ID = "1918533635"

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = REPO_ROOT / "templates" / "daily_page.adf.json"


def week_monday(today: date) -> date:
    return today - timedelta(days=today.weekday())


def render_body(monday: date) -> str:
    raw = TEMPLATE_PATH.read_text(encoding="utf-8")
    days = [monday + timedelta(days=i) for i in range(5)]
    replacements = {
        "{{MON_MMDD}}": f"{days[0]:%m/%d}",
        "{{TUE_MMDD}}": f"{days[1]:%m/%d}",
        "{{WED_MMDD}}": f"{days[2]:%m/%d}",
        "{{THU_MMDD}}": f"{days[3]:%m/%d}",
        "{{FRI_MMDD}}": f"{days[4]:%m/%d}",
    }
    for placeholder, value in replacements.items():
        raw = raw.replace(placeholder, value)
    # Validate that the result is still valid JSON.
    json.loads(raw)
    return raw


def build_title(monday: date) -> str:
    friday = monday + timedelta(days=4)
    return f"{monday:%y%m%d}-{friday:%y%m%d} Daily"


def create_page(title: str, body_adf: str) -> dict:
    email = os.environ["ATLASSIAN_EMAIL"]
    token = os.environ["ATLASSIAN_API_TOKEN"]
    payload = {
        "spaceId": SPACE_ID,
        "parentId": PARENT_ID,
        "status": "current",
        "title": title,
        "body": {
            "representation": "atlas_doc_format",
            "value": body_adf,
        },
    }
    response = requests.post(
        f"{CONFLUENCE_BASE}/api/v2/pages",
        auth=(email, token),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    if not response.ok:
        sys.stderr.write(f"Confluence API error {response.status_code}: {response.text}\n")
        response.raise_for_status()
    return response.json()


def main() -> int:
    monday = week_monday(date.today())
    title = build_title(monday)
    body = render_body(monday)
    result = create_page(title, body)
    webui = result.get("_links", {}).get("webui", "")
    print(f"Created: {title}")
    if webui:
        print(f"URL: {CONFLUENCE_BASE}{webui}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
