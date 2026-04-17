# Weekly Daily Report Routine

## Schedule
Weekly · Monday 06:00 (KST)

## Required environment variables
- `ATLASSIAN_EMAIL` — Atlassian account email (ex: `name@nota.ai`)
- `ATLASSIAN_API_TOKEN` — API token issued at
  https://id.atlassian.com/manage-profile/security/api-tokens

## Routine prompt

```
Run the deterministic daily-report script and report its result.

Steps:
1. Install dependencies:  pip install -r scripts/requirements.txt
2. Execute:               python scripts/create_daily_page.py
3. Report the exact stdout (title + URL). If the script exits non-zero,
   report the stderr verbatim and stop — do NOT attempt to fix the page
   manually or call any MCP tool as a fallback.

Do not modify the script, template, mention IDs, space ID, parent ID,
or any part of the table. The table layout is fixed in the repository.
```

## Notes
- Table structure, mention account IDs, `spaceId`, and `parentId` are
  hardcoded in `templates/daily_page.adf.json` and
  `scripts/create_daily_page.py`.
- Only the Monday–Friday dates are computed from `date.today()`.
- To change the participant list or structure, edit the template and
  script directly and commit — the routine prompt never changes.
