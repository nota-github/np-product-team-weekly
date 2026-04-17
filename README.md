# np-product-team-weekly

NP Team Product 주간 Daily 페이지 자동화.

## 파일 구조
- `config.json` — **편집 지점**. Confluence 폴더 경로(`parentId`), Jira 보드(`jira.boards`), 참여자(`mentions`) 설정 전체.
- `scripts/create_daily_page.py` — 매주 월요일, 이번 주 월~금 날짜로 표 페이지 생성.
- `scripts/fill_today_column.py` — 매 평일 말, 오늘 컬럼에 각자 할당된 Jira 티켓 채우기.
- `routines/weekly-daily.md` — 주간 페이지 생성 Routine (월 09:00).
- `routines/daily-fill.md` — 매일 티켓 채우기 Routine (월–금 23:45).

## 설정 변경
- **다른 Confluence 폴더로 이동**: `config.json`의 `parentId`(필요시 `spaceId`) 수정.
- **Jira 보드 추가/제거**: `config.json`의 `jira.boards` 배열 편집. 프로젝트 키는 URL에서 자동 추출.
- **참여자 변경**: `config.json`의 `mentions` 배열 편집.

표 구조(헤더·공유사항 행·5일 컬럼)는 의도적으로 스크립트에 고정되어 있습니다.

## 환경 변수 (Routine 설정에서 주입)
- `ATLASSIAN_EMAIL`
- `ATLASSIAN_API_TOKEN` — https://id.atlassian.com/manage-profile/security/api-tokens
