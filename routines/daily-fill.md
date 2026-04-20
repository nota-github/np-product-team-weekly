# Daily Fill Routine

## Schedule
Weekdays (Mon–Fri) · 23:30 (KST)

Cron (UTC, KST–9h): `45 14 * * 1-5`

## Required access
- Atlassian MCP server must be connected.
- No HTTP API calls. No Atlassian tokens. No environment variables.
  `ATLASSIAN_EMAIL` / `ATLASSIAN_API_TOKEN` must NOT be read or used.

## Routine prompt

```
Fill today's column on this week's daily page with each person's Jira tickets,
using ONLY the Atlassian MCP server. Do NOT call any HTTP API directly and do
NOT read `ATLASSIAN_EMAIL` or `ATLASSIAN_API_TOKEN`. Every Jira and Confluence
read/write in this routine must go through the Atlassian MCP tools
(`searchJiraIssuesUsingJql`, `searchConfluenceUsingCql` /
`getPagesInConfluenceSpace`, `getConfluencePage`, `updateConfluencePage`).

Steps:

1. Weekend check. If today (KST) is Saturday or Sunday, print
   "Skip: <YYYY-MM-DD> is a weekend" and stop.

2. Read `config.json` from the repo root. Extract:
   - `spaceId`, `parentId`, `confluenceBase`
   - `jira.baseUrl`
   - project keys from each `jira.boards` URL via the regex
     `/projects/([A-Z0-9]+)/`
   - assignee account ids from `mentions[].accountId`

3. Build the JQL deterministically (identical to
   `fill_today_column.build_jql`):

       project in (<keys>)
       AND assignee in ("<id1>","<id2>",...)
       AND (status in ("In Progress","In Review","Blocked")
            OR (status = Done AND resolutiondate >= startOfDay("+0900")))

4. Compute this week's page title:
   - Monday  = today − today.weekday()
   - Friday  = Monday + 4 days
   - Title   = `<YYMMDD_mon>-<YYMMDD_fri> Daily`

5. Fetch Jira issues via MCP `searchJiraIssuesUsingJql` with the JQL from
   step 3. Request at least the fields `summary,status,assignee,duedate`,
   and page through all results so nothing is truncated.

6. Locate the target Confluence page id by title under `parentId`. Use
   MCP `searchConfluenceUsingCql` with
       cql = parent = <parentId> AND title = "<title>" AND type = page
   or MCP `getPagesInConfluenceSpace` scoped to `spaceId` with the
   `title` filter. If no matching page exists, report the error and
   stop — do NOT create the page from this routine.

7. Fetch the page via MCP `getConfluencePage` asking for the body in
   Atlas Doc Format (ADF). Capture the page id, title, and the ADF body.

8. Pipe a JSON bundle to the deterministic transformer on stdin and
   capture its stdout:

       python scripts/fill_today_column.py

   Stdin payload (single JSON object):

       {
         "jira_issues": <issues array returned by MCP, unchanged>,
         "confluence_page_id": "<page id from step 7>",
         "confluence_page_title": "<page title from step 7>",
         "confluence_page_body_adf": <ADF body as object OR its JSON string>
       }

   The script is a pure stdin→stdout transformer (no network, no token,
   stdlib only). It returns JSON `{page_id, title, body_adf,
   updated_rows}`. Do not modify the script, config, or JQL logic.

9. Write the updated body back via MCP `updateConfluencePage`:
       - pageId: returned `page_id`
       - title:  returned `title`
       - body representation `atlas_doc_format`
       - body value: returned `body_adf`
       - version: bump by 1 if the MCP tool requires it

10. Report the page title, `updated_rows` from the script, and the page
    URL (`confluenceBase` + the webui link returned by MCP). On any MCP
    or script failure, print the error verbatim and stop — do NOT fall
    back to HTTP or token-based APIs.
```

## Notes
- Target page is located by title: `yymmdd-yymmdd Daily` for the week
  containing today's date in KST (Asia/Seoul, UTC+9), under `config.parentId`.
- Today's column = today's weekday (월=1 … 금=5). Weekends no-op.
- Tickets selected: `status in (In Progress, In Review, Blocked)` OR
  (`status = Done AND resolutiondate >= startOfDay("+0900")`). All date/time
  boundaries are KST (Asia/Seoul, UTC+9).
- Edit `config.json → jira.boards` to change which projects are scanned;
  project keys are extracted from board URLs.
- `scripts/fill_today_column.py` depends only on the Python stdlib;
  `scripts/requirements.txt` (`requests`) is only needed by the weekly
  routine.
