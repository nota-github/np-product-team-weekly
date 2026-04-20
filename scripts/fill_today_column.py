#!/usr/bin/env python3
"""Fill today's column on this week's daily page with each person's Jira tickets.

Selects tickets whose assignee is listed in `config.json` (mentions) from the
projects implied by `config.json` (jira.boards), and whose status is In Progress,
In Review, Blocked, or Done-resolved-today.

Writes each ticket as one paragraph (title link + status label + due label) into
the today-column cell of each person's row. Weekend runs are a no-op.

Input  (stdin):  JSON { jira_issues, confluence_page_id, confluence_page_title,
                        confluence_page_body_adf }
Output (stdout): JSON { page_id, title, body_adf, updated_rows }
"""

from __future__ import annotations

import json
import re
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))

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
        f"OR (status = Done AND resolutiondate >= startOfDay('+0900')))"
    )


def week_monday(today: date) -> date:
    return today - timedelta(days=today.weekday())


def page_title(monday: date) -> str:
    friday = monday + timedelta(days=4)
    return f"{monday:%y%m%d}-{friday:%y%m%d} Daily"


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


def parse_tickets(issues: list) -> list[dict]:
    tickets = []
    for issue in issues:
        f = issue.get("fields", {})
        assignee = f.get("assignee") or {}
        tickets.append({
            "key": issue["key"],
            "summary": f.get("summary", ""),
            "status": (f.get("status") or {}).get("name", ""),
            "assigneeId": assignee.get("accountId"),
            "duedate": f.get("duedate"),
        })
    return tickets


def main() -> int:
    config = load_config()
    today = datetime.now(KST).date()
    if today.weekday() >= 5:
        print(f"Skip: {today} is a weekend")
        return 0

    monday = week_monday(today)
    title = page_title(monday)
    today_col = today.weekday() + 1
    jira_browse = f"{config['jira']['baseUrl']}/browse"

    data = json.load(sys.stdin)
    tickets = parse_tickets(data["jira_issues"])
    page_id = str(data["confluence_page_id"])
    page_title_val = data["confluence_page_title"]
    body = data["confluence_page_body_adf"]
    if isinstance(body, str):
        body = json.loads(body)

    by_assignee: dict[str, list[dict]] = {}
    for t in tickets:
        if t["assigneeId"]:
            by_assignee.setdefault(t["assigneeId"], []).append(t)

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

    payload = {
        "page_id": page_id,
        "title": page_title_val,
        "body_adf": json.dumps(body, ensure_ascii=False),
        "updated_rows": updated,
    }
    json.dump(payload, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
