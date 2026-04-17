# Daily Fill Routine

## Schedule
Weekdays (Mon–Fri) · 23:45 (KST)

Cron (UTC, KST–9h): `45 14 * * 1-5`

## Required environment variables
- `ATLASSIAN_EMAIL`
- `ATLASSIAN_API_TOKEN`

## Routine prompt

```
Run the deterministic Jira → daily-page fill script.

Steps:
1. Install dependencies:  pip install -r scripts/requirements.txt
2. Execute:               python scripts/fill_today_column.py
3. Report the exact stdout (page title, row count, URL).
   On non-zero exit, report stderr verbatim and stop — do NOT
   attempt to fix the page manually or call any MCP tool.

Do not modify the script, config, or JQL logic. All configurable
settings (Jira boards, Confluence folder, participants) live in
config.json.
```

## Notes
- Target page is located by title: `yymmdd-yymmdd Daily` for the week
  containing `date.today()`, under `config.parentId`.
- Today's column = today's weekday (월=1 … 금=5). Weekends no-op.
- Tickets selected: `status in (In Progress, In Review, Blocked)` OR
  (`status = Done AND resolutiondate >= startOfDay()`).
- Edit `config.json → jira.boards` to change which projects are scanned;
  project keys are extracted from board URLs.
