"""ConsumptionAnalyzer — NCI/ISI 산출 + Claude AI 분석

네오 소비지수(NCI)와 업종별 경기체감지수(ISI)를 산출하고,
Claude API를 통해 소비 트렌드를 분석합니다.

분석 모델: claude-opus-4-6 (심층 분석 품질 우선)
글쓰기 모델: claude-sonnet-4-6 (generator.py)
"""

import json
import logging
import os
from pathlib import Path

import anthropic
import yaml

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent.parent

# 분석은 Opus — 데이터 해석·인과관계·예측 품질 최우선
ANALYSIS_MODEL = 'claude-opus-4-6'
ANALYSIS_MAX_TOKENS = 4000


class ConsumptionAnalyzer:
    """소비 트렌드 분석기"""

    def __init__(self):
        self.client = None
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            self.client = anthropic.Anthropic(api_key=api_key)

        # 업종 설정 로드
        sectors_path = ROOT_DIR / 'config' / 'sectors.yaml'
        if sectors_path.exists():
            self.sectors = yaml.safe_load(sectors_path.read_text(encoding='utf-8'))
        else:
            self.sectors = {}

        # NCI 가중치 로드
        weights_path = ROOT_DIR / 'config' / 'nci_weights.yaml'
        if weights_path.exists():
            self.weights = yaml.safe_load(weights_path.read_text(encoding='utf-8'))
        else:
            self.weights = {}

    def analyze(self, collected: dict, date_str: str, content_type: str) -> dict:
        """수집 데이터를 분석하여 NCI/ISI + 인사이트 생성"""

        # 1. NCI 산출
        nci_scores = self._calculate_nci(collected)

        # 2. ISI 산출 (뉴스 감성 포함)
        isi_scores, news_sentiment = self._calculate_isi_with_sentiment(collected)

        # 3. 통계 지표 요약 (원데이터 → 분석용 정리)
        stats_summary = self._build_stats_summary(collected)

        # 4. Claude Opus AI 심층 분석
        ai_analysis = self._run_ai_analysis(
            collected, nci_scores, isi_scores,
            stats_summary, news_sentiment,
            date_str, content_type,
        )

        return {
            'date': date_str,
            'content_type': content_type,
            'nci_scores': nci_scores,
            'isi_scores': isi_scores,
            'stats_summary': stats_summary,
            'news_sentiment': news_sentiment,
            'ai_analysis': ai_analysis,
            'news_summary': self._summarize_news(collected.get('news', [])),
        }

    # ── NCI 산출 ────────────────────────────────────────────────────────────

    def _calculate_nci(self, collected: dict) -> dict:
        """네오 소비지수(NCI) 산출

        NCI = (소매판매액지수×0.35 + CSI×0.30 + 서비스업생산지수×0.20 + 뉴스감성×0.15)
        각 요소를 0~100 스케일로 정규화
        """
        nci = {
            'overall': 50.0,
            'restaurant': 50.0,
            'retail': 50.0,
            'food_mart': 50.0,
            'food_price_pressure': 50.0,
            'consumer_spending_power': 50.0,
        }

        weights = {
            'retail': 0.35,
            'csi': 0.30,
            'service_prod': 0.20,
            'news': 0.15,
        }

        scores = {}

        # KOSIS: 소매판매액지수
        kosis = collected.get('kosis', {})
        retail_vals = kosis.get('retail_sales_index', {}).get('values', [])
        if retail_vals:
            try:
                latest = float(retail_vals[-1].get('DT', 100))
                # 기준 100 → NCI 50, ±20포인트 범위
                scores['retail'] = min(100, max(0, 50 + (latest - 100) * 1.5))
            except (ValueError, IndexError, KeyError):
                scores['retail'] = 50.0

        # BOK: 소비자심리지수(CSI)
        bok = collected.get('bok', {})
        csi_vals = bok.get('consumer_sentiment', {}).get('values', [])
        if csi_vals:
            try:
                latest_csi = float(csi_vals[-1].get('DATA_VALUE', 100))
                # CSI 100 = NCI 50, 1포인트 차이 = NCI 0.7포인트
                scores['csi'] = min(100, max(0, 50 + (latest_csi - 100) * 0.7))
            except (ValueError, IndexError, KeyError):
                scores['csi'] = 50.0

        # KOSIS: 서비스업생산지수
        service_vals = kosis.get('service_production_index', {}).get('values', [])
        if service_vals:
            try:
                latest_svc = float(service_vals[-1].get('DT', 100))
                scores['service_prod'] = min(100, max(0, 50 + (latest_svc - 100) * 1.2))
            except (ValueError, IndexError, KeyError):
                scores['service_prod'] = 50.0

        # 뉴스 감성 (단순 키워드 기반; AI 분석 후 갱신 가능)
        scores['news'] = self._calc_news_sentiment_score(collected.get('news', []))

        # 가중 합산
        total_weight = 0.0
        weighted_sum = 0.0
        for key, w in weights.items():
            if key in scores:
                weighted_sum += scores[key] * w
                total_weight += w

        if total_weight > 0:
            nci['overall'] = round(weighted_sum / total_weight, 1)

        # 업종별 서브지수 (overall 기반으로 업종 특성 보정)
        nci['restaurant'] = round(min(100, max(0, nci['overall'] + scores.get('restaurant_adj', 0))), 1)
        nci['retail'] = round(min(100, max(0, nci['overall'] + scores.get('retail_adj', 0))), 1)
        nci['food_mart'] = round(min(100, max(0, nci['overall'] - 2)), 1)

        # 서브지수: 식자재가격압력지수 (KAMIS 데이터 있을 때 갱신)
        kamis = collected.get('food_price', {})
        if kamis:
            nci['food_price_pressure'] = self._calc_food_price_pressure(kamis)

        # 서브지수: 실질소비여력지수
        nci['consumer_spending_power'] = round(
            min(100, max(0, (scores.get('csi', 50) * 0.5 + scores.get('retail', 50) * 0.5))), 1
        )

        return nci

    def _calc_news_sentiment_score(self, articles: list) -> float:
        """뉴스 키워드 기반 감성 점수 (0~100)"""
        positive = ['증가', '상승', '호조', '활성화', '회복', '성장', '확대', '개선']
        negative = ['감소', '하락', '부진', '침체', '위축', '악화', '둔화', '하락세']

        pos_count = neg_count = 0
        for a in articles:
            text = a.get('title', '') + a.get('description', '')
            pos_count += sum(1 for w in positive if w in text)
            neg_count += sum(1 for w in negative if w in text)

        total = pos_count + neg_count
        if total == 0:
            return 50.0
        sentiment_ratio = pos_count / total  # 0~1
        return round(30 + sentiment_ratio * 40, 1)  # 30~70 범위

    def _calc_food_price_pressure(self, kamis: dict) -> float:
        """식자재가격압력지수 (0=저압, 100=고압)"""
        changes = kamis.get('price_changes', [])
        if not changes:
            return 50.0
        avg_change = sum(c.get('change_pct', 0) for c in changes) / len(changes)
        # 0% 변동 = 50, +5% = 75, -5% = 25
        return round(min(100, max(0, 50 + avg_change * 5)), 1)

    # ── ISI 산출 ────────────────────────────────────────────────────────────

    def _calculate_isi_with_sentiment(self, collected: dict) -> tuple[dict, dict]:
        """업종별 경기체감지수(ISI) + 뉴스 감성 산출

        ISI = base(50) + 뉴스감성보정(30%) + 통계지표보정(70%)
        """
        isi = {
            'general_restaurant': 50.0,
            'cafe_bakery': 50.0,
            'convenience': 50.0,
            'supermarket': 50.0,
            'food_distribution': 50.0,
            'clothing': 50.0,
        }

        # 업종별 키워드 감성 집계
        sector_keywords = {
            'general_restaurant': (['외식', '음식점', '한식', '식당', '맛집'], ['배달', '예약']),
            'cafe_bakery': (['카페', '커피', '베이커리', '제과', '디저트'], ['스타벅스', '투썸']),
            'convenience': (['편의점', 'CU', 'GS25', '세븐일레븐', '간편식'], []),
            'supermarket': (['마트', '슈퍼마켓', '이마트', '홈플러스', '대형마트'], ['코스트코']),
            'food_distribution': (['식자재', '도매', '농산물', '수산물', '축산물'], ['가락시장', '식품원료']),
            'clothing': (['의류', '패션', '잡화', 'SPA', '아울렛'], ['패딩', '봄옷']),
        }

        positive_words = ['증가', '호조', '성장', '상승', '인기', '급증', '확대', '회복']
        negative_words = ['감소', '부진', '하락', '침체', '위축', '둔화', '폐업', '경영난']

        news_sentiment = {}
        articles = collected.get('news', [])

        for sector, (primary, secondary) in sector_keywords.items():
            pos = neg = total = 0
            for a in articles:
                text = a.get('title', '') + a.get('description', '')
                # 해당 업종 관련 기사인지 확인
                if not any(kw in text for kw in primary + secondary):
                    continue
                total += 1
                pos += sum(1 for w in positive_words if w in text)
                neg += sum(1 for w in negative_words if w in text)

            if total > 0:
                sentiment = (pos - neg) / max(total, 1)
                adj = sentiment * 8  # ±8점 보정
                isi[sector] = round(min(100, max(0, 50 + adj)), 1)
                news_sentiment[sector] = {
                    'articles': total, 'positive': pos, 'negative': neg,
                    'score': round(sentiment, 3),
                }
            else:
                news_sentiment[sector] = {'articles': 0, 'positive': 0, 'negative': 0, 'score': 0}

        # 0~100 범위로 클램핑
        for key in isi:
            isi[key] = round(min(100, max(0, isi[key])), 1)

        return isi, news_sentiment

    # ── 통계 요약 ────────────────────────────────────────────────────────────

    def _build_stats_summary(self, collected: dict) -> dict:
        """분석에 사용할 통계 지표 요약 (원데이터 → 의미있는 수치로 정리)"""
        summary = {}

        kosis = collected.get('kosis', {})
        bok = collected.get('bok', {})

        # 소매판매액지수 — 최근 3개월 추이
        retail_vals = kosis.get('retail_sales_index', {}).get('values', [])
        if retail_vals:
            recent = retail_vals[-3:]
            summary['retail_sales'] = {
                'latest': self._safe_float(recent[-1], 'DT'),
                'prev': self._safe_float(recent[-2], 'DT') if len(recent) >= 2 else None,
                'prev2': self._safe_float(recent[-3], 'DT') if len(recent) >= 3 else None,
                'unit': '(2020=100)',
            }

        # 소비자심리지수
        csi_vals = bok.get('consumer_sentiment', {}).get('values', [])
        if csi_vals:
            recent = csi_vals[-3:]
            summary['consumer_sentiment'] = {
                'latest': self._safe_float(recent[-1], 'DATA_VALUE'),
                'prev': self._safe_float(recent[-2], 'DATA_VALUE') if len(recent) >= 2 else None,
                'baseline': 100,
                'note': '100 초과 = 소비 낙관, 미만 = 비관',
            }

        # 서비스업생산지수
        svc_vals = kosis.get('service_production_index', {}).get('values', [])
        if svc_vals:
            recent = svc_vals[-2:]
            summary['service_production'] = {
                'latest': self._safe_float(recent[-1], 'DT'),
                'prev': self._safe_float(recent[-2], 'DT') if len(recent) >= 2 else None,
                'unit': '(2020=100)',
            }

        # KAMIS 식자재 가격 (있을 때만)
        food_price = collected.get('food_price', {})
        if food_price:
            summary['food_prices'] = food_price.get('price_changes', [])[:10]

        # 뉴스 기사 수 및 주요 출처
        news = collected.get('news', [])
        summary['news_count'] = len(news)
        summary['news_sources'] = list({a.get('source', '') for a in news if a.get('source')})[:5]

        return summary

    def _safe_float(self, item: dict, key: str) -> float | None:
        if not item:
            return None
        try:
            return float(item.get(key, ''))
        except (ValueError, TypeError):
            return None

    # ── Claude Opus 2단계 분석 ──────────────────────────────────────────────

    def _run_ai_analysis(self, collected: dict, nci: dict, isi: dict,
                         stats: dict, news_sentiment: dict,
                         date_str: str, content_type: str) -> dict:
        """Claude Opus 2단계 심층 분석

        Stage 1: Opus가 이번 주 데이터에서 핵심 신호를 식별하고 분석 포커스 결정
        Stage 2: Opus가 Stage 1 결과를 바탕으로 전체 소비 트렌드 심층 분석 실행
        """
        if not self.client:
            logger.warning("  No Anthropic client, skipping AI analysis")
            return {}

        # 공통 입력값 준비
        news_text = '\n'.join([
            f"- [{a.get('source', '')}] {a.get('title', '')}"
            + (f" | {a.get('description', '')[:80]}" if a.get('description') else '')
            for a in collected.get('news', [])[:30]
        ])
        sentiment_text = '\n'.join([
            f"  {k}: 기사 {v['articles']}건, 긍정 {v['positive']}/부정 {v['negative']}, "
            f"감성점수 {v['score']:+.2f}"
            for k, v in news_sentiment.items()
        ])
        common_vars = dict(
            date=date_str,
            nci_scores=json.dumps(nci, ensure_ascii=False, indent=2),
            isi_scores=json.dumps(isi, ensure_ascii=False, indent=2),
            stats_summary=json.dumps(stats, ensure_ascii=False, indent=2),
            news_sentiment_table=sentiment_text,
            news_headlines=news_text,
        )

        # ── Stage 1: 분석 포커스 결정 ──────────────────────────────────────
        plan_path = ROOT_DIR / 'prompts' / 'analysis_plan.txt'
        if not plan_path.exists():
            logger.warning("  analysis_plan.txt 없음, Stage 1 건너뜀")
            analysis_plan = '{}'
        else:
            plan_template = plan_path.read_text(encoding='utf-8')
            plan_prompt = plan_template.format(**common_vars)

            logger.info(f"  [Stage 1] {ANALYSIS_MODEL} — 이번 주 신호 식별 중...")
            try:
                resp = self.client.messages.create(
                    model=ANALYSIS_MODEL,
                    max_tokens=1000,
                    messages=[{'role': 'user', 'content': plan_prompt}],
                )
                analysis_plan = self._extract_json_text(resp.content[0].text)
                logger.info(f"  [Stage 1] 완료 — 분석 포커스 결정됨")

                # Stage 1 결과를 파싱해서 로그
                try:
                    plan_data = json.loads(analysis_plan)
                    logger.info(f"  이번 주: {plan_data.get('week_character', '-')}")
                    logger.info(f"  각도: {plan_data.get('analysis_angle', '-')}")
                except json.JSONDecodeError:
                    pass

            except Exception as e:
                logger.error(f"  [Stage 1] Claude API error: {e}")
                analysis_plan = '{}'

        # ── Stage 2: 심층 분석 실행 ────────────────────────────────────────
        analysis_path = ROOT_DIR / 'prompts' / 'consumption_analysis.txt'
        if not analysis_path.exists():
            logger.warning(f"  consumption_analysis.txt 없음")
            return {}

        analysis_template = analysis_path.read_text(encoding='utf-8')
        analysis_prompt = analysis_template.format(
            content_type=content_type,
            analysis_plan=analysis_plan,
            **common_vars,
        )

        logger.info(f"  [Stage 2] {ANALYSIS_MODEL} — 심층 분석 실행 중...")
        try:
            resp = self.client.messages.create(
                model=ANALYSIS_MODEL,
                max_tokens=ANALYSIS_MAX_TOKENS,
                messages=[{'role': 'user', 'content': analysis_prompt}],
            )
            content = resp.content[0].text
            logger.info(f"  [Stage 2] 완료 ({len(content)}자)")

            try:
                result = json.loads(self._extract_json_text(content))
                result['_plan'] = json.loads(analysis_plan) if analysis_plan != '{}' else {}
                return result
            except json.JSONDecodeError:
                return {'raw_analysis': content}

        except Exception as e:
            logger.error(f"  [Stage 2] Claude API error: {e}")
            return {}

    @staticmethod
    def _extract_json_text(text: str) -> str:
        """응답에서 JSON 블록 추출"""
        if '```json' in text:
            return text.split('```json')[1].split('```')[0].strip()
        if '```' in text:
            return text.split('```')[1].split('```')[0].strip()
        return text.strip()

    # ── 뉴스 요약 ────────────────────────────────────────────────────────────

    def _summarize_news(self, articles: list) -> list:
        """뉴스 헤드라인 요약 (상위 10개)"""
        return [
            {
                'title': a.get('title', ''),
                'source': a.get('source', ''),
                'url': a.get('url', ''),
                'description': a.get('description', '')[:120] if a.get('description') else '',
            }
            for a in articles[:10]
        ]
