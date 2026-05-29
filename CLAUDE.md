# NeoSolution — 프로젝트 가이드

## 전체 구조

```
publish_weekly.yml    → post_sns.yml   (workflow_run 트리거)
publish_monthly.yml   → post_sns.yml   (workflow_run 트리거)
monitor.yml                             (일간 상태 체크)
```

배포: Hugo → Cloudflare Pages → `neosolution.co.kr`
이미지: Cloudflare R2
사이트: `site/` 디렉토리

## 파이프라인 데이터 흐름 (4-Phase)

```
Phase 1: Collection (필수: KOSIS, BOK, News / 선택: CardData, SMBA, FoodPrice, Weather)
Phase 2: Analysis (NCI/ISI 산출 → Claude AI 소비 트렌드 분석)
Phase 3: Generation (콘텐츠 타입별 프롬프트 → Claude 포스트 생성 → 차트 → 품질 검증)
Phase 4: Publishing (Hugo 마크다운 → git push → Cloudflare 배포)
```

## 핵심 차이점 (vs narrative/harness)

- `--region asia/us` 대신 `--content-type weekly/monthly/guide/special` 사용
- 다국어 대신 한국어 단일 언어
- NI(Narrative Index) 대신 NCI(Neo Consumption Index) / ISI(Industry Sentiment Index)
- SNS: X/Bluesky/LinkedIn 대신 Telegram/Naver Blog/KakaoTalk

## 타임존 규칙

| 파이프라인 | cron (UTC) | 의미 |
|---|---|---|
| publish_weekly | `0 0 * * 1` | UTC 월 00:00 = **KST 월 09:00** |
| publish_monthly | `0 0 1-7 * 1` | 매월 첫째 월요일 KST 09:00 |
| monitor | `0 3 * * *` | UTC 03:00 = KST 12:00 |

**날짜 계산**: 반드시 `TZ=Asia/Seoul date +%Y-%m-%d` 사용.

## 알려진 함정

### Hugo
- `nci_scores` JSON → 반드시 `| jsonify | safeJS` 사용
- `git add`는 경로 명시: `git add site/content/ site/data/ data/`

### GitHub Actions
- `if: success()`는 이전 skip에서 false → `if: ${{ !cancelled() }}` 사용
- Cloudflare deploy 커밋 메시지에 한글 불가 → 영문 사용

### 파이프라인
- 선택 수집기는 non-fatal: 실패해도 파이프라인 계속
- 분석 결과 캐시: `data/analysis_{date}_{type}.json` (재실행 시 캐시 사용)
- NCI/ISI는 0~100 범위로 클램핑

### SNS
- 각 SNS 포스터는 독립적 (하나 실패해도 다른 것 계속)
- Telegram: Markdown 파싱 모드 사용

## 파이프라인 수동 실행

```bash
# 주간 리포트 (로컬 테스트)
python pipeline/main.py --content-type weekly --date 2026-04-07 --no-push

# 수집만
python pipeline/main.py --content-type weekly --collect-only

# 분석까지만
python pipeline/main.py --content-type weekly --analyze-only

# 월간 리포트
python pipeline/main.py --content-type monthly --date 2026-04-01 --no-push
```

## Hugo 로컬 개발

```bash
cd site
hugo serve
# → http://localhost:1313/
```

## 프로젝트 디렉토리

```
neosolution/
├── pipeline/          ← Python 파이프라인
│   ├── main.py        ← 엔트리포인트
│   ├── base_collector.py ← 수집기 베이스 클래스
│   ├── collector.py   ← 뉴스 수집
│   ├── kosis_collector.py ← 통계청 API
│   ├── bok_collector.py ← 한국은행 API
│   ├── analyzer.py    ← NCI/ISI 산출 + Claude 분석
│   ├── generator.py   ← 콘텐츠 생성
│   ├── publisher.py   ← Hugo 마크다운 발행
│   ├── tracker.py     ← 예측 추적 (Brier Score)
│   ├── monitor.py     ← R2/상태 모니터링
│   ├── visuals/       ← 차트 생성 (Plotly)
│   └── *_poster.py    ← SNS 포스터
├── prompts/           ← Claude 프롬프트 템플릿
├── config/            ← 업종/데이터소스/가중치 설정
├── data/              ← 중간 데이터 (gitignored)
├── site/              ← Hugo 사이트
└── .github/workflows/ ← CI/CD
```
