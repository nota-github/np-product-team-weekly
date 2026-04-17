# np-product-team-weekly

NP Team Product 주간 Daily 페이지 자동 생성.

## 구조
- `config.json` — **편집 지점**. 폴더 경로(`parentId`)와 참여자 멘션(`mentions`) 등 설정 전체가 여기에 있습니다.
- `scripts/create_daily_page.py` — `config.json`을 읽어 이번 주 월~금 날짜로 표를 조립한 뒤 Confluence 페이지를 생성합니다.
- `routines/weekly-daily.md` — Claude Code Routine 스케줄 및 prompt.

## 설정 변경
- **다른 폴더로 옮기기**: `config.json`의 `parentId`(및 필요시 `spaceId`)만 수정.
- **참여자 추가/삭제**: `config.json`의 `mentions` 배열을 편집. `accountId`는 Atlassian 사용자 ID, `displayName`은 `@표시` 뒤에 붙을 이름.

표 구조(헤더·공유사항 행·5일 컬럼)는 의도적으로 스크립트에 고정해 두었습니다.
