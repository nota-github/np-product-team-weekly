#!/usr/bin/env python3
"""Fill today's column on this week's daily page with each person's Jira tickets.

Selects tickets whose assignee is listed in `config.json` (mentions) from the
projects implied by `config.json` (jira.boards), and whose status is In Progress,
In Review, Blocked, or Done-resolved-today.

Writes each ticket as one paragraph (title link + status label + due label) into
the today-column cell of each person's row. Weekend runs are a no-op.
"""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config.json"

DAY_LABELS = ["월", "화", "수", "목", "금"]
STATUS_COLOR = {
    "In Progress": "yellow",
    "In Review":   "blue",
    "Blocked":     "red",
    "Done":        "green",
}
TRACKED_STATUSES = ("In Progress", "In Review", "Blocked")
BOARD_PROJECT_RE = re.compile(r"/projects/([A-Z0-9]+)/")


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def auth() -> tuple[str, str]:
    return (os.environ["ATLASSIAN_EMAIL"], os.environ["ATLASSIAN_API_TOKEN"])


def project_keys(config: dict) -> list[str]:
    keys: list[str] = []
    for url in config["jira"]["boards"]:
        m = BOARD_PROJECT_RE.search(url)
        if not m:
            raise ValueError(f"Cannot extract project key from board URL: {url}")
        keys.append(m.group(1))
    return keys


def build_jql(config: dict) -> str:
    projects = ", ".join(project_keys(config))
    assignees = ", ".join(f'"{m["accountId"]}"' for m in config["mentions"])
    tracked = ", ".join(f'"{s}"' for s in TRACKED_STATUSES)
    return (
        f"project in ({projects}) "
        f"AND assignee in ({assignees}) "
        f"AND (status in ({tracked}) "
        f"OR (status = Done AND resolutiondate >= startOfDay()))"
    )


def search_tickets(config: dict) -> list[dict]:
    url = f"{config['jira']['baseUrl']}/rest/api/3/search/jql"
    payload = {
        "jql": build_jql(config),
        "fields": ["summary", "status", "assignee", "duedate", "resolutiondate"],
        "maxResults": 100,
    }
    r = requests.post(url, auth=auth(), json=payload, timeout=30)
    r.raise_for_status()
    tickets = []
    for issue in r.json().get("issues", []):
        f = issue["fields"]
        assignee = f.get("assignee") or {}
        tickets.append({
            "key": issue["key"],
            "summary": f["summary"],
            "status": f["status"]["name"],
            "assigneeId": assignee.get("accountId"),
            "duedate": f.get("duedate"),
        })
    return tickets


def week_monday(today: date) -> date:
    return today - timedelta(days=today.weekday())


def page_title(monday: date) -> str:
    friday = monday + timedelta(days=4)
    return f"{monday:%y%m%d}-{friday:%y%m%d} Daily"


def find_page_id(config: dict, title: str) -> str:
    url = f"{config['confluenceBase']}/api/v2/pages"
    params = {"space-id": config["spaceId"], "title": title, "limit": 25}
    r = requests.get(url, auth=auth(), params=params, timeout=30)
    r.raise_for_status()
    results = r.json().get("results", [])
    match = next((p for p in results if p.get("parentId") == config["parentId"]), None)
    if match is None and results:
        match = results[0]
    if match is None:
        raise RuntimeError(f"Page not found under space {config['spaceId']}: {title}")
    return match["id"]


def get_page(config: dict, page_id: str) -> dict:
    url = f"{config['confluenceBase']}/api/v2/pages/{page_id}"
    r = requests.get(url, auth=auth(), params={"body-format": "atlas_doc_format"}, timeout=30)
    r.raise_for_status()
    return r.json()


def status_node(text: str, color: str) -> dict:
    return {"type": "status", "attrs": {"text": text, "color": color, "localId": str(uuid.uuid4())}}


def due_color(due_str: str | None, today: date) -> str:
    if not due_str:
        return "neutral"
    d = date.fromisoformat(due_str)
    if d < today:
        return "red"
    if d == today:
        return "yellow"
    return "neutral"


def ticket_paragraph(ticket: dict, today: date, jira_browse: str) -> dict:
    nodes = [
        {
            "type": "text",
            "text": f"{ticket['key']}: {ticket['summary']}",
            "marks": [{"type": "link", "attrs": {"href": f"{jira_browse}/{ticket['key']}"}}],
        },
        {"type": "text", "text": " "},
        status_node(ticket["status"], STATUS_COLOR.get(ticket["status"], "neutral")),
    ]
    if ticket["duedate"]:
        nodes += [
            {"type": "text", "text": " "},
            status_node(f"Due {ticket['duedate']}", due_color(ticket["duedate"], today)),
        ]
    return {"type": "paragraph", "content": nodes}


def build_cell(tickets: list[dict], today: date, jira_browse: str) -> dict:
    attrs = {"colspan": 1, "rowspan": 1}
    if not tickets:
        return {"type": "tableCell", "attrs": attrs, "content": [{"type": "paragraph"}]}
    return {
        "type": "tableCell",
        "attrs": attrs,
        "content": [ticket_paragraph(t, today, jira_browse) for t in tickets],
    }


def assignee_of_row(cell: dict, mention_ids: set[str]) -> str | None:
    try:
        first = cell["content"][0]["content"][0]
    except (KeyError, IndexError, TypeError):
        return None
    if first.get("type") != "mention":
        return None
    aid = first.get("attrs", {}).get("id")
    return aid if aid in mention_ids else None


def update_page(config: dict, page: dict, body_doc: dict) -> dict:
    page_id = page["id"]
    url = f"{config['confluenceBase']}/api/v2/pages/{page_id}"
    payload = {
        "id": page_id,
        "status": "current",
        "title": page["title"],
        "body": {
            "representation": "atlas_doc_format",
            "value": json.dumps(body_doc, ensure_ascii=False),
        },
        "version": {
            "number": page["version"]["number"] + 1,
            "message": "Auto: fill today's column with Jira tickets",
        },
    }
    r = requests.put(url, auth=auth(), json=payload, timeout=30)
    if not r.ok:
        sys.stderr.write(f"Update failed {r.status_code}: {r.text}\n")
        r.raise_for_status()
    return r.json()


def main() -> int:
    config = load_config()
    today = date.today()
    if today.weekday() >= 5:
        print(f"Skip: {today} is a weekend")
        return 0

    monday = week_monday(today)
    title = page_title(monday)
    today_col = today.weekday() + 1
    jira_browse = f"{config['jira']['baseUrl']}/browse"

    tickets = search_tickets(config)
    by_assignee: dict[str, list[dict]] = {}
    for t in tickets:
        if t["assigneeId"]:
            by_assignee.setdefault(t["assigneeId"], []).append(t)

    page_id = find_page_id(config, title)
    page = get_page(config, page_id)
    body = json.loads(page["body"]["atlas_doc_format"]["value"])

    table = next(n for n in body["content"] if n["type"] == "table")
    mention_ids = {m["accountId"] for m in config["mentions"]}

    updated = 0
    for row in table["content"]:
        if row.get("type") != "tableRow":
            continue
        cells = row["content"]
        aid = assignee_of_row(cells[0], mention_ids)
        if aid is None:
            continue
        cells[today_col] = build_cell(by_assignee.get(aid, []), today, jira_browse)
        updated += 1

    update_page(config, page, body)
    print(f"Updated {title}: {updated} row(s) in ({DAY_LABELS[today.weekday()]}) column")
    print(f"URL: {config['confluenceBase']}/spaces/{config['spaceId']}/pages/{page_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
