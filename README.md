# NeoSolution

VAN 서비스 + POS 솔루션 전문기업 네오솔루션의 웹사이트 겸 소비 인사이트 플랫폼.

## 개요

단순한 회사 홈페이지가 아닌, AI 기반 소비 트렌드 분석으로 **업계 인사이트 리더**로 포지셔닝하기 위한 플랫폼입니다.

### 핵심 기능

- **네오 소비지수 (NCI)** — 공공 경제 데이터와 AI 분석으로 산출하는 소비 트렌드 지수
- **업종별 경기체감지수 (ISI)** — 외식/유통/식자재 등 업종별 경기 체감 지표
- **자동 인사이트 발행** — 주간/월간 소비 트렌드 리포트 자동 생성 및 발행
- **서비스 소개** — VAN 서비스, 업종별 POS 솔루션 안내

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 정적 사이트 | Hugo + Cloudflare Pages |
| 데이터 파이프라인 | Python 3.12 |
| AI | Claude API (Anthropic) |
| 데이터 소스 | KOSIS, 한국은행, NewsAPI |
| 이미지 | Cloudflare R2 |
| CI/CD | GitHub Actions |
| SNS | Telegram, Naver Blog, KakaoTalk |

## 로컬 개발

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일 편집

# 파이프라인 테스트
python pipeline/main.py --content-type weekly --no-push

# Hugo 로컬 서버
cd site && hugo serve
```

## 프로젝트 구조

```
neosolution/
├── pipeline/          # Python 데이터 파이프라인
├── prompts/           # Claude AI 프롬프트
├── config/            # 업종/데이터소스 설정
├── site/              # Hugo 정적 사이트
├── .github/workflows/ # GitHub Actions CI/CD
└── PLAN.md            # 상세 구축 계획서
```

## 라이선스

Proprietary - NeoSolution
