# Data Quality Plan

- 생성 시각: `2026-04-11T16:05:37.910248+00:00`
- 우선순위: `P2`
- 데이터 품질 점수: `84`
- 가장 약한 축: `권위성`
- Governance: `low`
- Primary Motion: `intelligence`

## 현재 이슈

- 가장 약한 품질 축은 권위성(62)

## 필수 신호

- Steam charts와 app/console store ranking
- 패치노트·릴리스 일정·DLC 공지
- 동접·매출·리뷰 변화 같은 흥행 신호

## 품질 게이트

- 게임명·플랫폼·edition을 canonical key로 분리
- 출시 전 관심 신호와 출시 후 운영 신호를 분리
- 패치일·출시일·수집일을 별도 필드로 유지

## 다음 구현 순서

- Steam charts, store ranking, patch note source를 운영 레이어로 추가
- 게임/플랫폼 canonicalization rule을 추가
- 흥행 신호와 커뮤니티 반응을 별도 score로 시각화

## 운영 규칙

- 원문 URL, 수집일, 이벤트 발생일은 별도 필드로 유지한다.
- 공식 source와 커뮤니티/시장 source를 같은 신뢰 등급으로 병합하지 않는다.
- collector가 인증키나 네트워크 제한으로 skip되면 실패를 숨기지 말고 skip 사유를 기록한다.
- 이 문서는 `scripts/build_data_quality_review.py --write-repo-plans`로 재생성한다.
