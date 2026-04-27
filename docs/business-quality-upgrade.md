# Business Quality Upgrade

- Generated: `2026-04-14T04:48:11.525239+00:00`
- Portfolio verdict: `충분`
- Business value score: `82.3`
- Upgrade phase: P2 운영 순위/패치 신호 강화
- Primary motion: `intelligence`
- Weakest dimension: `authority`

## Current Evidence

- Primary rows: `5489`
- Today raw rows: `36`
- Latest report items: `53`
- Match rate: `100.0%`
- Collection errors: `0`
- Freshness gap: `1`

## Upgrade Actions

- Steam charts, store ranking, patch note source를 운영 레이어 후보로 유지하고 fixture/parser 검증 후 활성화한다.
- game/platform/edition canonical key로 같은 게임의 버전/플랫폼 중복을 분리한다.
- release_schedule과 patch_note를 단순 뉴스가 아닌 행동 가능한 이벤트로 리포트한다.

## Quality Contracts

- `config/categories/game.yaml`: output `reports/game_quality.json`, tracked `steam_chart, store_ranking, patch_note, release_schedule`, backlog items `4`

## Contract Gaps

- None.
