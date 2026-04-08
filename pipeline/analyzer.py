"""ConsumptionAnalyzer — NCI/ISI 산출 + Claude AI 분석

네오 소비지수(NCI)와 업종별 경기체감지수(ISI)를 산출하고,
Claude API를 통해 소비 트렌드를 분석합니다.
"""

import json
import logging
import os
from pathlib import Path

import anthropic
import yaml

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent.parent


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

        # 2. ISI 산출
        isi_scores = self._calculate_isi(collected)

        # 3. Claude AI 분석
        ai_analysis = self._run_ai_analysis(collected, nci_scores, isi_scores,
                                            date_str, content_type)

        return {
            'date': date_str,
            'content_type': content_type,
            'nci_scores': nci_scores,
            'isi_scores': isi_scores,
            'ai_analysis': ai_analysis,
            'news_summary': self._summarize_news(collected.get('news', [])),
        }

    def _calculate_nci(self, collected: dict) -> dict:
        """네오 소비지수(NCI) 산출

        NCI = weighted_sum(소매판매액변화율, 카드결제증감, 소비자심리지수) / 3
        각 요소를 0~100 스케일로 정규화
        """
        nci = {
            'overall': 50.0,
            'restaurant': 50.0,
            'retail': 50.0,
            'food_mart': 50.0,
        }

        # KOSIS 데이터에서 소매판매액지수 추출
        kosis = collected.get('kosis', {})
        retail_data = kosis.get('retail_sales_index', {}).get('values', [])
        if retail_data:
            # 최근값 기준 NCI 보정 (실제 구현 시 상세 로직 추가)
            try:
                latest = float(retail_data[-1].get('DT', 100))
                nci['retail'] = min(100, max(0, latest * 0.5))
                nci['overall'] = (nci['restaurant'] + nci['retail'] + nci['food_mart']) / 3
            except (ValueError, IndexError, KeyError):
                pass

        # BOK 데이터에서 소비자심리지수 반영
        bok = collected.get('bok', {})
        csi_data = bok.get('consumer_sentiment', {}).get('values', [])
        if csi_data:
            try:
                latest_csi = float(csi_data[-1].get('DATA_VALUE', 100))
                # CSI를 NCI에 반영 (CSI 100 = NCI 50 기준)
                csi_adj = (latest_csi - 100) * 0.3
                for key in nci:
                    nci[key] = min(100, max(0, nci[key] + csi_adj))
            except (ValueError, IndexError, KeyError):
                pass

        return nci

    def _calculate_isi(self, collected: dict) -> dict:
        """업종별 경기체감지수(ISI) 산출

        ISI = base(50) + 뉴스감성보정 + 통계지표보정
        """
        isi = {
            'general_restaurant': 50.0,
            'cafe_bakery': 50.0,
            'convenience': 50.0,
            'supermarket': 50.0,
            'food_distribution': 50.0,
            'clothing': 50.0,
        }

        # 뉴스 감성 분석으로 ISI 보정 (실제 구현 시 Claude 감성 분석 추가)
        news = collected.get('news', [])
        if news:
            # 업종별 관련 기사 수로 간단한 보정
            for article in news:
                title = article.get('title', '') + article.get('description', '')
                if '외식' in title or '음식점' in title:
                    isi['general_restaurant'] += 0.3
                if '카페' in title or '제과' in title:
                    isi['cafe_bakery'] += 0.3
                if '편의점' in title:
                    isi['convenience'] += 0.3
                if '마트' in title or '슈퍼' in title:
                    isi['supermarket'] += 0.3
                if '식자재' in title or '도매' in title:
                    isi['food_distribution'] += 0.3
                if '의류' in title or '패션' in title:
                    isi['clothing'] += 0.3

        # 0~100 범위로 클램핑
        for key in isi:
            isi[key] = round(min(100, max(0, isi[key])), 1)

        return isi

    def _run_ai_analysis(self, collected: dict, nci: dict, isi: dict,
                         date_str: str, content_type: str) -> dict:
        """Claude API를 통한 심층 분석"""
        if not self.client:
            logger.warning("  No Anthropic client, skipping AI analysis")
            return {}

        prompt_path = ROOT_DIR / 'prompts' / 'consumption_analysis.txt'
        if not prompt_path.exists():
            logger.warning(f"  Prompt not found: {prompt_path}")
            return {}

        prompt_template = prompt_path.read_text(encoding='utf-8')

        # 뉴스 요약 (최대 20개)
        news_text = '\n'.join([
            f"- [{a.get('source', '')}] {a.get('title', '')}"
            for a in collected.get('news', [])[:20]
        ])

        prompt = prompt_template.format(
            date=date_str,
            content_type=content_type,
            nci_scores=json.dumps(nci, ensure_ascii=False),
            isi_scores=json.dumps(isi, ensure_ascii=False),
            news_headlines=news_text,
        )

        try:
            response = self.client.messages.create(
                model='claude-sonnet-4-6',
                max_tokens=2000,
                messages=[{'role': 'user', 'content': prompt}],
            )
            content = response.content[0].text

            # JSON 파싱 시도
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {'raw_analysis': content}

        except Exception as e:
            logger.error(f"  Claude API error: {e}")
            return {}

    def _summarize_news(self, articles: list) -> list:
        """뉴스 헤드라인 요약"""
        return [
            {
                'title': a.get('title', ''),
                'source': a.get('source', ''),
                'url': a.get('url', ''),
            }
            for a in articles[:10]
        ]
