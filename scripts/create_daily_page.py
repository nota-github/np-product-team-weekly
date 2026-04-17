#!/usr/bin/env python3
"""Create the weekly daily-report Confluence page.

Folder path (`parentId`) and participant mentions are loaded from
`config.json` at the repo root. The table structure is fixed in this
script; only Monday–Friday dates are computed from today.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config.json"

DAY_LABELS = ["월", "화", "수", "목", "금"]


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def week_monday(today: date) -> date:
    return today - timedelta(days=today.weekday())


def build_title(monday: date) -> str:
    friday = monday + timedelta(days=4)
    return f"{monday:%y%m%d}-{friday:%y%m%d} Daily"


def text_cell(text: str, *, strong: bool = False, header: bool = False) -> dict:
    node: dict = {"type": "text", "text": text}
    if strong:
        node["marks"] = [{"type": "strong"}]
    return {
        "type": "tableHeader" if header else "tableCell",
        "content": [{"type": "paragraph", "content": [node]}],
    }


def empty_cell() -> dict:
    return {"type": "tableCell", "content": [{"type": "paragraph"}]}


def mention_cell(account_id: str, display_name: str) -> dict:
    return {
        "type": "tableCell",
        "content": [{
            "type": "paragraph",
            "content": [{
                "type": "mention",
                "attrs": {"id": account_id, "text": f"@{display_name}"},
            }],
        }],
    }


def build_adf_body(monday: date, mentions: list[dict]) -> str:
    days = [monday + timedelta(days=i) for i in range(5)]
    rows = [
        {
            "type": "tableRow",
            "content": [text_cell("이름", strong=True, header=True)] + [
                text_cell(f"({label}) {day:%m/%d}", strong=True, header=True)
                for label, day in zip(DAY_LABELS, days)
            ],
        },
        {
            "type": "tableRow",
            "content": [text_cell("공유사항")] + [empty_cell() for _ in range(5)],
        },
    ]
    for m in mentions:
        rows.append({
            "type": "tableRow",
            "content": [mention_cell(m["accountId"], m["displayName"])]
            + [empty_cell() for _ in range(5)],
        })
    doc = {
        "version": 1,
        "type": "doc",
        "content": [{
            "type": "table",
            "attrs": {"isNumberColumnEnabled": False, "layout": "default"},
            "content": rows,
        }],
    }
    return json.dumps(doc, ensure_ascii=False)


def create_page(config: dict, title: str, body_adf: str) -> dict:
    email = os.environ["ATLASSIAN_EMAIL"]
    token = os.environ["ATLASSIAN_API_TOKEN"]
    payload = {
        "spaceId": config["spaceId"],
        "parentId": config["parentId"],
        "status": "current",
        "title": title,
        "body": {"representation": "atlas_doc_format", "value": body_adf},
    }
    response = requests.post(
        f"{config['confluenceBase']}/api/v2/pages",
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
    config = load_config()
    monday = week_monday(date.today())
    title = build_title(monday)
    body = build_adf_body(monday, config["mentions"])
    result = create_page(config, title, body)
    webui = result.get("_links", {}).get("webui", "")
    print(f"Created: {title}")
    if webui:
        print(f"URL: {config['confluenceBase']}{webui}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
