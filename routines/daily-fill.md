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

5. Fetch Jira issues via MCP `searchJiraIssuesUsingJql` with the JQL
   from step 3. Request at least the fields
   `summary,status,assignee,duedate` and page through all results so
   nothing is truncated.

   ⚠️ CRITICAL — do NOT read the Jira response into context. The
   response is large enough to blow the context window. Do not print,
   summarise, enumerate, or Read the JSON contents. Instead:

   - If the Atlassian MCP automatically persists the response as a
     file (a path such as `/tmp/…` returned by the tool), use that
     path directly.
   - Otherwise, immediately persist the raw tool response to
     `/tmp/jira_issues.json` using the `Write` tool and DO NOT echo
     it back afterwards.
   - If pagination is needed, save each page as
     `/tmp/jira_issues.<N>.json` (N starting at 0) and let step 8
     merge them in bash. Never concatenate pages in context.

   After this step you must hold only a list of local file paths
   (`JIRA_FILES`) — never the issue payloads themselves.

6. Locate the target Confluence page id by title under `parentId`. Use
   MCP `searchConfluenceUsingCql` with
       cql = parent = <parentId> AND title = "<title>" AND type = page
   or MCP `getPagesInConfluenceSpace` scoped to `spaceId` with the
   `title` filter. If no matching page exists, report the error and
   stop — do NOT create the page from this routine.

7. Fetch the page via MCP `getConfluencePage` asking for the body in
   Atlas Doc Format (ADF). Capture only the page id (`PAGE_ID`) and
   title (`PAGE_TITLE`) into context.

   The ADF body arrives in context as part of the tool result.
   Immediately write it to `/tmp/adf_body.json` with the `Write` tool
   (as a JSON object if the MCP returned an object, or as the raw JSON
   string if that's what it returned — the transformer accepts both).
   From this point on, refer to the body only by its path
   (`ADF_FILE=/tmp/adf_body.json`). Do not repeat, quote, or summarise
   its contents.

8. Assemble the stdin bundle entirely in bash — never in Claude
   context — and pipe it to the deterministic transformer:

       python3 -c '
       import json, sys
       def load(p):
           with open(p, encoding="utf-8") as f:
               return json.load(f)
       def issues_of(obj):
           if isinstance(obj, list):
               return obj
           for k in ("nodes", "issues", "results", "values"):
               v = obj.get(k)
               if isinstance(v, list):
                   return v
           return []
       jira_paths = sys.argv[1].split(",")
       adf_path   = sys.argv[2]
       page_id    = sys.argv[3]
       page_title = sys.argv[4]
       all_issues = []
       for p in jira_paths:
           all_issues.extend(issues_of(load(p)))
       json.dump({
           "jira_issues": all_issues,
           "confluence_page_id": page_id,
           "confluence_page_title": page_title,
           "confluence_page_body_adf": load(adf_path),
       }, sys.stdout, ensure_ascii=False)
       ' "$JIRA_FILES_CSV" "$ADF_FILE" "$PAGE_ID" "$PAGE_TITLE" \
         | python3 scripts/fill_today_column.py \
         > /tmp/fill_result.json

   `$JIRA_FILES_CSV` is the comma-separated list of paths from step 5
   (a single path is fine). `scripts/fill_today_column.py` is a pure
   stdin→stdout transformer (stdlib only, no network, no token). Do
   not modify the script, config, or JQL logic. Its output is JSON
   `{page_id, title, body_adf, updated_rows}` written to
   `/tmp/fill_result.json`.

9. Read `/tmp/fill_result.json` and write the updated body back via
   MCP `updateConfluencePage`:
       - pageId: `page_id` from the result
       - title:  `title`   from the result
       - body representation `atlas_doc_format`
       - body value: `body_adf` from the result (pass through as-is)
       - version: bump by 1 if the MCP tool requires it

   The `body_adf` is a JSON string; pass it straight to the MCP tool
   without re-parsing or re-stringifying it in context.

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
- Context-size guard: the Jira MCP response and the Confluence ADF body
  are both too large for Claude's working context. Steps 5, 7, and 8
  deliberately keep those payloads on disk (`/tmp/jira_issues*.json`,
  `/tmp/adf_body.json`) and let bash/`python3 -c` assemble the
  transformer's stdin bundle. The only values the model ever needs to
  hold are the page id and title.
