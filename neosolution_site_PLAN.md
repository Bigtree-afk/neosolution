# NeoSolution 웹사이트 구축 계획서

## Context

VAN 서비스 제공 및 POS 프로그램 판매 회사의 웹사이트를 단순 홈페이지가 아닌 **시장 인사이트 플랫폼**으로 구축한다.
목표는 유통/외식/식자재 업계에서 "소비 트렌드는 네오솔루션"이라는 인식을 만들어 업계 지명도를 확보하는 것.

**참조 프로젝트:**
- `narrative/` (retic.uk): AI 기반 금융 시장 분석 플랫폼 (Python pipeline + Hugo + Cloudflare Pages)
- `harness/`: narrative에서 추출한 4-Phase 파이프라인 하네스 구조

**핵심 전략:** NarrativeEdge가 "내러티브 지수(NI)"로 금융시장을 분석하듯, NeoSolution은 **"네오 소비지수(NCI)"와 "업종별 경기체감지수(ISI)"**로 소상공인 시장을 분석한다.

---

## 1. 사이트 구조

```
neosolution.co.kr/
├── /                              ← 메인 (히어로 + 최신 인사이트 + 서비스 요약)
├── /insights/                     ← 인사이트 허브
│   ├── /insights/weekly/          ← 주간 소비 트렌드 리포트
│   ├── /insights/monthly/         ← 월간 업종 심층 분석
│   └── /insights/special/         ← 특별 리포트 (명절, 시즌)
├── /index/                        ← 지수 대시보드
│   ├── /index/neo-consumption/    ← 네오 소비지수 (NCI)
│   ├── /index/industry-sentiment/ ← 업종별 경기체감지수 (ISI)
│   └── /index/regional/           ← 지역별 소비 동향
├── /services/                     ← 서비스 소개
│   ├── /services/van/             ← VAN 서비스
│   ├── /services/pos/             ← POS 제품 카탈로그
│   │   ├── retail/                ← 유통/소매 POS
│   │   ├── restaurant/            ← 외식업 POS
│   │   └── food-mart/             ← 식자재마트 POS
│   └── /services/pricing/         ← 요금 안내
├── /cases/                        ← 고객 성공 사례
├── /guides/                       ← 소상공인 가이드
│   ├── startup/                   ← 창업 가이드
│   ├── operations/                ← 운영 노하우
│   └── regulations/               ← 결제 규제 해설
├── /about/                        ← 회사 소개
├── /contact/                      ← 문의 / 가맹 신청
├── /newsletter/                   ← 뉴스레터 구독
└── /stats/                        ← 예측 정확도 통계
```

---

## 2. 독자적 지수 체계

### 네오 소비지수 (Neo Consumption Index, NCI) — 0~100
- **구성:** 소매판매액 변화율 + 카드결제 증감 + 소비자심리지수
- **세부 지수:** 외식업 NCI, 유통업 NCI, 식자재업 NCI
- Claude AI가 데이터 가중치와 상대적 모멘텀 분석

### 업종별 경기체감지수 (Industry Sentiment Index, ISI) — 업종별 0~100
- **업종:** 일반음식점, 카페/제과, 편의점, 슈퍼/마트, 식자재유통, 의류/잡화
- **기반:** 결제 건수 추이, 평균 객단가 변화, 점포 수 변화

### 소상공인 건강지표 (Small Business Health Score) — 분기별
- **구성:** 창업/폐업 비율, 평균 매출 변화, 대출 연체율

---

## 3. 데이터 파이프라인

하네스의 4-Phase 패턴을 적용. `--region` 대신 `--content-type weekly/monthly/guide/special` 사용.

### Phase 1: COLLECTION

**필수 수집기 (실패 시 파이프라인 중단):**

| 수집기 | 소스 | 데이터 |
|--------|------|--------|
| `KOSISCollector` | KOSIS API (statistics.go.kr) | 소매판매액지수, 서비스업생산지수, 소비자물가지수 |
| `BOKCollector` | 한국은행 경제통계시스템 | 기준금리, 소비자심리지수(CSI), 가계신용 |
| `NewsCollector` | NewsAPI + RSS (매경, 한경) | 유통/외식/결제 업계 뉴스 |

**선택 수집기 (실패해도 계속 — 하네스 Pattern 08):**

| 수집기 | 소스 | 용도 |
|--------|------|------|
| `CardDataCollector` | 카드사 빅데이터 포털 | 소비지수 보정 |
| `SMBACollector` | 소상공인시장진흥공단 | 상권분석, 폐업률 |
| `FoodPriceCollector` | KAMIS (농산물유통정보) | 식자재 가격 동향 |
| `WeatherCollector` | 기상청 API | 소비 패턴 상관분석 |

### Phase 2: ANALYSIS
- NCI/ISI 산출 알고리즘 (NI 알고리즘 적용)
- Claude API로 트렌드 분석 + 인사이트 추출
- 예측 생성 (소비 방향, 업종별 전망)

### Phase 3: GENERATION
- 콘텐츠 타입별 프롬프트로 Claude 호출
- 주간 리포트: 1500~2000자, 월간: 3000~4000자, 가이드: 1000~1500자
- 차트 생성 (Plotly → PNG → R2 업로드)
- 품질 검증 (본문 길이, 구조 확인)

### Phase 4: PUBLISHING
- Hugo 마크다운 생성 + YAML 프론트매터
- Git commit/push → Cloudflare Pages 자동 배포
- SNS 배포 워크플로우 트리거

---

## 4. 콘텐츠 전략

| 콘텐츠 | 주기 | 요일 | 파이프라인 |
|--------|------|------|-----------|
| 주간 소비 트렌드 | 매주 | 월요일 09:00 | 자동 |
| 소상공인 가이드 | 주 2회 | 화, 목 10:00 | AI 보조 + 편집 |
| 월간 업종 심층분석 | 매월 | 첫째 월요일 | 자동 + 편집 |
| 규제 해설 | 비정기 | - | 수동 + AI 초안 |
| 고객 사례 | 월 1~2건 | - | 수동 |
| 특별 리포트 | 연 4~6회 | - | 자동 + 편집 |

### SNS 배포 (한국 시장 맞춤)

| 플랫폼 | 구현 | 목적 |
|--------|------|------|
| Telegram | `telegram_poster.py` (재사용) | 관리자 알림 + 채널 |
| Naver Blog | `naver_poster.py` (신규) | SEO + 검색 노출 |
| KakaoTalk 채널 | `kakao_poster.py` (신규) | 구독자 직접 도달 |
| Instagram | `instagram_poster.py` (재사용) | 인포그래픽 카드 |

### SEO 타겟 키워드
- "소비 트렌드", "외식업 매출 동향", "식자재 가격 전망"
- "소상공인 창업 가이드", "POS 프로그램 비교", "VAN 수수료 비교"

---

## 5. 기술 스택

| 레이어 | 기술 | 비용 |
|--------|------|------|
| 정적 사이트 | Hugo + Cloudflare Pages | 무료 |
| 이미지 저장 | Cloudflare R2 | 무료 (10GB) |
| AI | Claude API (Sonnet) | ~$5-15/월 |
| 데이터 수집 | KOSIS, BOK, KAMIS API | 무료 (공공 API) |
| CI/CD | GitHub Actions | 무료 |
| 뉴스레터 | Stibee | 무료 (500명까지) |
| **월 총 비용** | | **~$10-20** |

---

## 6. 프로젝트 디렉토리 구조

```
neosolution/
├── CLAUDE.md
├── README.md
├── requirements.txt
├── .env / .env.example
├── .gitignore
├── pipeline/
│   ├── main.py                    ← 엔트리포인트 (harness/templates/pipeline_main.py 기반)
│   ├── collector.py               ← 뉴스 수집기
│   ├── kosis_collector.py         ← KOSIS API
│   ├── bok_collector.py           ← 한국은행 API
│   ├── card_data_collector.py     ← 카드사 데이터
│   ├── smba_collector.py          ← 소상공인진흥공단
│   ├── food_price_collector.py    ← KAMIS 농산물가격
│   ├── analyzer.py                ← NCI/ISI 산출 + Claude 분석
│   ├── generator.py               ← 콘텐츠 생성
│   ├── publisher.py               ← Hugo 마크다운 생성
│   ├── visuals/
│   │   ├── nci_chart.py           ← NCI 게이지/트렌드 차트
│   │   ├── isi_chart.py           ← ISI 바 차트
│   │   └── sector_chart.py        ← 업종별 차트
│   ├── tracker.py                 ← 예측 추적 (Brier Score)
│   ├── telegram_poster.py
│   ├── naver_poster.py
│   ├── kakao_poster.py
│   └── instagram_poster.py
├── prompts/
│   ├── consumption_analysis.txt
│   ├── blog_writer_weekly_ko.txt
│   ├── blog_writer_monthly_ko.txt
│   ├── blog_writer_guide_ko.txt
│   └── blog_writer_special_ko.txt
├── config/
│   ├── sectors.yaml               ← 업종 정의 + 키워드
│   ├── data_sources.yaml          ← API 엔드포인트
│   └── nci_weights.yaml           ← NCI 가중치
├── data/                          ← 중간 데이터 (gitignored)
├── site/
│   ├── hugo.toml
│   ├── content/ko/                ← 한국어 단일 언어
│   ├── layouts/
│   │   ├── _default/ (baseof, single, list)
│   │   ├── index.html             ← 홈페이지
│   │   ├── insights/ (single, list)
│   │   ├── services/ (single)
│   │   ├── cases/ (single)
│   │   ├── guides/ (single)
│   │   └── partials/
│   │       ├── nci-gauge.html     ← 소비지수 게이지
│   │       ├── isi-bars.html      ← 경기체감 바 차트
│   │       ├── trend-chart.html
│   │       ├── cta-contact.html   ← 문의 CTA
│   │       └── newsletter-signup.html
│   ├── data/ (nci_history.json, isi_latest.json, stats.json)
│   └── static/ (css, js, images)
├── .github/workflows/
│   ├── publish_weekly.yml
│   ├── publish_monthly.yml
│   ├── publish_guide.yml
│   ├── post_sns.yml
│   ├── update_dashboard.yml
│   └── monitor.yml
└── scripts/
    └── setup.sh
```

---

## 7. 단계별 구현 계획

### Phase 1: MVP 기반 (1~3주차)
- Hugo 사이트 스캐폴딩
- 정적 페이지: 홈, VAN 서비스, POS 카탈로그, 회사소개, 문의
- 기본 디자인 (전문적, 깔끔한 비즈니스 스타일)
- Cloudflare Pages 배포 + 도메인 연결
- **결과물:** neosolution.co.kr 라이브

### Phase 2: 데이터 파이프라인 MVP (4~6주차)
- `KOSISCollector`, `BOKCollector`, `NewsCollector` 구현
- `analyzer.py` — 기본 NCI 산출
- 주간 리포트 프롬프트 작성 + `generator.py` 구현
- `publisher.py` + GitHub Actions 주간 배포
- 기본 차트 생성 (NCI 게이지, ISI 바)
- **결과물:** 매주 월요일 자동 발행되는 주간 소비 트렌드 리포트

### Phase 3: 대시보드 + SNS (7~9주차)
- `/index/` 대시보드 페이지 + Chart.js 시각화
- NCI 시계열 추적
- Telegram, Naver Blog, KakaoTalk 채널 배포
- 뉴스레터 구독 페이지
- 선택 수집기 추가: `CardDataCollector`, `FoodPriceCollector`
- **결과물:** 인터랙티브 대시보드, 3개 플랫폼 SNS 배포

### Phase 4: 콘텐츠 확장 (10~13주차)
- 월간 심층분석 파이프라인
- 주 2회 소상공인 가이드 파이프라인
- 예측 추적 시스템 (Brier Score)
- 고객 사례 템플릿
- 나머지 수집기 추가: `SMBACollector`, `WeatherCollector`
- SEO 최적화: sitemap, 구조화 데이터
- **결과물:** 전체 콘텐츠 자동 발행 체계 완성

### Phase 5: 권위 구축 (14주차~)
- 특별 리포트 (추석, 설, 성수기)
- 이메일 뉴스레터 자동화
- Instagram 인포그래픽 카드
- NCI 과거 데이터 백필
- NCI API 엔드포인트 (파트너 임베드용)
- **결과물:** 업계 인사이트 리더 포지셔닝 확립

---

## 8. 검증 방법

1. **로컬 파이프라인 테스트:** `python pipeline/main.py --content-type weekly --no-push` → 마크다운 생성 확인
2. **Hugo 빌드:** `cd site && hugo --minify` → 에러 없이 빌드 확인
3. **차트 생성:** `python pipeline/visuals/nci_chart.py` → PNG 출력 확인
4. **Cloudflare Pages:** PR 생성 시 프리뷰 URL로 사이트 확인
5. **SNS 포스팅:** `--dry-run` 모드로 메시지 포맷 확인
6. **예측 추적:** 과거 데이터로 Brier Score 계산 로직 검증

---

## 9. 핵심 참조 파일

- `harness/templates/pipeline_main.py` → `pipeline/main.py` 기반
- `harness/patterns/08_data_collection.md` → BaseCollector 인터페이스
- `harness/patterns/09_hugo_publishing.md` → Hugo 구조 패턴
- `harness/checklists/new_project.md` → 9단계 프로젝트 설정 체크리스트
- `narrative/prompts/blog_writer_ko.txt` → 콘텐츠 생성 프롬프트 참조
- `narrative/pipeline/analyzer.py` → NI 알고리즘 → NCI 알고리즘 적용
- `narrative/site/layouts/partials/editorial-gauges.html` → NCI 게이지 UI 참조
