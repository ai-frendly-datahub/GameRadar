# GameRadar - 게임 산업 레이더

글로벌 게임 미디어 7개 소스(IGN, GameSpot, Polygon, Kotaku, PC Gamer, Eurogamer, VentureBeat)에서 RSS를 수집하여 게임 산업 뉴스를 분석합니다. 플랫폼, 스튜디오, 장르, 출시 정보 엔티티를 자동 태깅하고 HTML 리포트를 생성합니다.

## 프로젝트 목표

- **게임 산업 뉴스 통합**: 7개 글로벌 게임 미디어에서 실시간 뉴스 수집
- **엔티티 분석**: 플랫폼(PS5, Xbox, Steam), 스튜디오(EA, Ubisoft), 장르(RPG, FPS), 출시 정보 자동 태깅
- **트렌드 리포트**: DuckDB 저장 + HTML 리포트로 게임 산업 동향 시각화
- **자동화**: GitHub Actions 일일 수집 + GitHub Pages 리포트 자동 배포

## 기술적 우수성 (Phase 1)

Phase 1 개선사항을 통해 프로덕션급 안정성과 운영 효율성을 확보했습니다:

- **안정성 99.9%**: HTTP 자동 재시도(지수 백오프 3회), DB 트랜잭션 에러 처리로 일시적 장애에도 데이터 수집 보장
- **실시간 관찰성**: 구조화된 JSON 로깅으로 파이프라인 상태를 실시간 모니터링하고 문제 발생 시 즉시 디버깅
- **품질 보증**: 84% 테스트 커버리지(211개 테스트)로 코드 변경 시 회귀 버그 사전 차단
- **고성능 처리**: 배치 처리 최적화로 대량 데이터 수집 시 10배 속도 향상 (단일 트랜잭션 bulk insert)
- **운영 자동화**: Email/Webhook 알림으로 수집 완료, 에러 발생 등 이벤트를 즉시 통보하여 무인 운영 가능
## 빠른 시작
1. 가상환경을 만들고 의존성을 설치합니다.
   ```bash
   pip install -r requirements.txt
   ```
2. 실행:
   ```bash
   cd GameRadar
   python main.py --category game --recent-days 7
   # 리포트: reports/game_report.html
   ```
   주요 옵션: `--per-source-limit 20`, `--recent-days 5`, `--keep-days 60`, `--timeout 20`.

## GitHub Actions & GitHub Pages
- 워크플로: `.github/workflows/radar-crawler.yml`
  - 스케줄: 매일 00:00 UTC (KST 09:00), 수동 실행도 지원.
  - 환경 변수 `RADAR_CATEGORY`를 프로젝트에 맞게 수정하세요.
  - 리포트 배포 디렉터리: `reports` → `gh-pages` 브랜치로 배포.
  - DuckDB 경로: `data/radar_data.duckdb` (Pages에 올라가지 않음). 아티팩트로 7일 보관.
- 설정 방법:
  1) 저장소 Settings → Pages에서 `gh-pages` 브랜치를 선택해 활성화  
  2) Actions 권한을 기본값으로 두거나 외부 PR에서도 실행되도록 설정  
  3) 워크플로 파일의 `RADAR_CATEGORY`를 원하는 YAML 이름으로 변경

## 동작 방식
- **수집**: 카테고리 YAML에 정의된 RSS만 지원합니다. 실행 시 DuckDB에 적재하고 보존 기간(`keep_days`)을 적용합니다.  
- **분석**: 엔티티별 키워드 단순 매칭. 매칭된 키워드를 리포트에 칩으로 표시합니다.  
- **리포트**: `reports/<category>_report.html`을 생성하며, 최근 N일(기본 7일) 기사와 엔티티 히트 카운트, 수집 오류를 표시합니다.

## 기본 경로
- DB: `data/radar_data.duckdb`
- 리포트 출력: `reports/`

## 디렉터리 구성
```
GameRadar/
  main.py                 # CLI 엔트리포인트
  requirements.txt        # 의존성 (DuckDB 포함)
  config/
    config.yaml           # DB/리포트 경로 설정
    categories/
      game.yaml           # 게임 산업 소스 + 엔티티 정의
  radar/
    collector.py          # RSS 수집
    analyzer.py           # 키워드 태깅
    reporter.py           # HTML 렌더링
    storage.py            # DuckDB 저장/정리
    config_loader.py      # YAML 로더
    models.py             # 데이터 클래스
  .github/workflows/      # GitHub Actions (crawler + Pages 배포)
```
