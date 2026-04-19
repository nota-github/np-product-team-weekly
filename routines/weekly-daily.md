# Weekly Daily Report Routine

## Schedule
Weekly · Monday 06:00 (KST)

## Required access
- Atlassian MCP server must be connected.
- No HTTP API calls. No Atlassian tokens. No environment variables.
  `ATLASSIAN_EMAIL` / `ATLASSIAN_API_TOKEN` must NOT be read or used.

## Routine prompt

```
Create this week's daily-report Confluence page using ONLY the Atlassian
MCP server. Do NOT call any HTTP API directly and do NOT read
`ATLASSIAN_EMAIL` or `ATLASSIAN_API_TOKEN`. The page creation must go
through MCP `createConfluencePage`.

Steps:

1. Run the deterministic payload generator and capture its stdout:

       python scripts/create_daily_page.py --dry-run

   It prints a single JSON object:

       {
         "title":          "<YYMMDD_mon>-<YYMMDD_fri> Daily",
         "body":           "<ADF document as JSON string>",
         "spaceId":        "<space id>",
         "parentId":       "<parent page id>",
         "confluenceBase": "<https://…/wiki>"
       }

   The script is stdlib-only in this mode — no network, no token.
   Do not modify the script, the config, or the table layout.

2. Create the page via MCP `createConfluencePage` with:
       - spaceId:        payload.spaceId
       - parentId:       payload.parentId
       - title:          payload.title
       - body representation: `atlas_doc_format`
       - body value:     payload.body   (the ADF JSON string, as-is)
       - status:         `current`

3. Report the created page title and its URL
   (`payload.confluenceBase` + the webui link returned by MCP).

On any MCP or script failure, print the error verbatim and stop — do NOT
fall back to HTTP or token-based APIs, and do NOT edit the page manually.
```

## Notes
- `config.json` holds the editable settings: `parentId` (target folder),
  `spaceId`, `confluenceBase`, and the `mentions` list.
- Table structure is fixed in `scripts/create_daily_page.py`; only the
  Monday–Friday dates are computed from `date.today()`.
- To change the target folder or participants, edit `config.json` only.
  The script and routine prompt do not need to change.
- `--dry-run` mode uses the Python stdlib only; `requests` in
  `scripts/requirements.txt` is not needed for this routine.
