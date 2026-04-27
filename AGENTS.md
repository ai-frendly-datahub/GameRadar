# GAMERADAR

게임 뉴스, 플랫폼 공지, 브라우저 기반 한국 게임 미디어, Reddit 커뮤니티를 함께 수집해 출시/패치/흥행 신호를 분석합니다.

## STRUCTURE

```
GameRadar/
├── radar/
│   ├── collector.py              # collect_sources() — RSS + browser + Reddit
│   ├── analyzer.py               # apply_entity_rules() — 게임 장르별 키워드 매칭 (RPG, FPS, 모바일, 인디 등)
│   ├── reporter.py               # generate_report() — Jinja2 HTML
│   ├── storage.py                # RadarStorage — DuckDB upsert/query/retention
│   ├── models.py                 # Source, Article, EntityDefinition, CategoryConfig
│   ├── config_loader.py          # YAML 로딩
│   ├── logger.py                 # structlog 구조화 로깅
│   ├── notifier.py               # Email/Webhook 알림
│   ├── raw_logger.py             # JSONL 원시 로깅
│   ├── search_index.py           # SQLite FTS5 전문 검색
│   ├── nl_query.py               # 자연어 쿼리 파서
│   ├── common/                   # 공유 유틸리티
│   └── mcp_server/               # MCP 서버 (server.py + tools.py)
├── config/
│   ├── config.yaml               # database_path, report_dir, raw_data_dir, search_db_path
│   └── categories/{domain}.yaml  # 소스 + 엔티티 정의
├── data/                         # DuckDB, search_index.db, raw/ JSONL
├── reports/                      # 생성된 HTML 리포트
├── tests/unit/                   # pytest 단위 테스트
├── main.py                       # CLI 엔트리포인트
└── .github/workflows/radar-crawler.yml
```

## ENTITIES

| Entity | Examples |
|--------|----------|
| `Platform` | PlayStation, Xbox, Steam, Nintendo, Epic Games |
| `Genre` | RPG, FPS, 오픈월드, 로그라이크, 모바일 |
| `BusinessSignal` | patch, release, game pass, sale, top seller |

## DEVIATIONS FROM TEMPLATE

- `javascript` 소스와 Reddit 소스를 collector에서 별도 pass로 처리
- `config_loader.py`가 Source 메타데이터와 browser `config`를 실제 런타임으로 전달
- 플랫폼 공지와 한국 게임 미디어를 operational signal 관점으로 함께 사용

## COMMANDS

```bash
python main.py --category game --recent-days 7
python main.py --category game --per-source-limit 50 --keep-days 90
```
