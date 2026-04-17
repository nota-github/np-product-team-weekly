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

Do not modify the script, config, or any part of the table.
The table layout is fixed in the repository.
```

## Notes
- `config.json` holds the editable settings: `parentId` (target folder),
  `spaceId`, `confluenceBase`, and the `mentions` list.
- Table structure is fixed in `scripts/create_daily_page.py`; only the
  Monday–Friday dates are computed from `date.today()`.
- To change the target folder or participants, edit `config.json` only.
  The script and routine prompt do not need to change.
