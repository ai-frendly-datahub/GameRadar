# GAMERADAR

게임 산업 뉴스 및 트렌드 분석 레이더. IGN, GameSpot, Polygon 등 7개 글로벌 게임 미디어에서 RSS 수집 → 키워드 엔티티 태깅 → DuckDB 저장 → HTML 리포트 생성.

## STRUCTURE

```
GameRadar/
├── radar/
│   ├── collector.py      # collect_sources() — RSS feeds only
│   ├── analyzer.py       # apply_entity_rules() — case-insensitive keyword matching
│   ├── reporter.py       # generate_report() — Jinja2 HTML with entity counts
│   ├── storage.py        # RadarStorage — DuckDB with upsert/query/retention
│   ├── models.py         # Source, Article, EntityDefinition, CategoryConfig
│   └── config_loader.py  # YAML: config.yaml + config/categories/*.yaml
├── config/
│   ├── config.yaml       # Global: database_path, report_dir
│   └── categories/
│       └── game.yaml     # 게임 산업 소스 + 엔티티 정의
└── main.py               # run(): load_config → collect → analyze → store → report
```

## ENTITIES

| Entity | Description | Examples |
|--------|-------------|----------|
| Platform | 게임 플랫폼 | PlayStation, Xbox, Nintendo, Steam |
| Studio | 개발사/퍼블리셔 | Activision, EA, Ubisoft, FromSoftware |
| Genre | 게임 장르 | RPG, FPS, Battle Royale, Indie |
| Release | 출시/업데이트 정보 | Launch, DLC, Early Access, Patch |

## COMMANDS

```bash
python main.py --category game --recent-days 7
python main.py --category game --per-source-limit 50 --keep-days 90
```
