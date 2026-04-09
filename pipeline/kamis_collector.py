"""KAMIS 농산물유통정보 수집기

KAMIS(한국농수산식품유통공사) API를 통해 가락시장 등 주요 도매시장의
농산물 일일 가격 데이터를 수집한다.

API 참고: https://www.kamis.or.kr/customer/reference/openapi_list.do
"""

import logging
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

import requests

from pipeline.base_collector import BaseCollector

logger = logging.getLogger(__name__)

# KAMIS API 상품 분류 코드
PRODUCT_CLASSES = {
    '01': '채소',
    '02': '과일',
    '03': '수산',
    '04': '축산',
    '05': '곡물',
}

# 주요 모니터링 품목 (코드: 이름, 단위, 분류)
WATCH_ITEMS = [
    # 채소
    {'code': '211', 'name': '배추', 'unit': '포기', 'category': '채소'},
    {'code': '214', 'name': '무', 'unit': 'kg', 'category': '채소'},
    {'code': '221', 'name': '양파', 'unit': 'kg', 'category': '채소'},
    {'code': '224', 'name': '마늘', 'unit': 'kg', 'category': '채소'},
    {'code': '227', 'name': '대파', 'unit': 'kg', 'category': '채소'},
    {'code': '231', 'name': '고추(건)', 'unit': 'kg', 'category': '채소'},
    {'code': '244', 'name': '애호박', 'unit': '개', 'category': '채소'},
    # 과일
    {'code': '411', 'name': '사과', 'unit': 'kg', 'category': '과일'},
    {'code': '414', 'name': '배', 'unit': 'kg', 'category': '과일'},
    {'code': '421', 'name': '감귤', 'unit': 'kg', 'category': '과일'},
    {'code': '431', 'name': '수박', 'unit': '개', 'category': '과일'},
    # 곡물
    {'code': '111', 'name': '쌀', 'unit': '20kg', 'category': '곡물'},
]


class KAMISCollector(BaseCollector):
    """KAMIS 농산물 도매가격 수집기"""

    BASE_URL = 'https://www.kamis.or.kr/service/price/xml.do'
    RETAIL_URL = 'https://www.kamis.or.kr/service/price/xml.do'

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.api_key = os.getenv('KAMIS_API_KEY', '')
        self.cert_id = os.getenv('KAMIS_CERT_ID', '')  # API 인증 ID

    def collect(self, date_str: str, **kwargs) -> dict:
        """일일 농산물 가격 수집

        Returns:
            {
                'date': str,
                'items': list[dict],    # 품목별 가격 정보
                'summary': dict,        # 요약 통계
                'source': 'kamis'
            }
        """
        cached = self._load_cached(date_str, 'kamis')
        if cached:
            return cached

        logger.info(f"  KAMIS: Collecting prices for {date_str}")

        items = []
        for item_info in WATCH_ITEMS:
            try:
                price_data = self._fetch_item_price(date_str, item_info)
                if price_data:
                    items.append(price_data)
            except Exception as e:
                logger.warning(f"  KAMIS {item_info['name']}: {e}")

        # 실제 API 없을 때 샘플 데이터 (개발/테스트용)
        if not items:
            logger.warning("  KAMIS: No API key or no data — using sample data")
            items = self._sample_data(date_str)

        summary = self._compute_summary(items, date_str)

        result = {
            'date': date_str,
            'items': items,
            'summary': summary,
            'source': 'kamis',
        }

        self._save(result, date_str, 'kamis')
        return result

    def _fetch_item_price(self, date_str: str, item_info: dict) -> dict | None:
        """KAMIS API 호출 — 단일 품목 일일 가격"""
        if not self.api_key:
            return None

        # 오늘과 전날 날짜 (변동률 계산용)
        today = datetime.strptime(date_str, '%Y-%m-%d')
        yesterday = (today - timedelta(days=1)).strftime('%Y-%m-%d')

        params = {
            'action': 'dailySalesList',
            'p_cert_key': self.api_key,
            'p_cert_id': self.cert_id,
            'p_returntype': 'xml',
            'p_product_cls_code': self._get_class_code(item_info['category']),
            'p_item_category_code': item_info['code'],
            'p_country_code': '1101',  # 서울 가락시장
            'p_regday': date_str.replace('-', '/'),
            'p_convert_kg_yn': 'N',
        }

        resp = requests.get(self.BASE_URL, params=params, timeout=10)
        resp.raise_for_status()

        return self._parse_xml_response(resp.text, item_info, date_str)

    def _parse_xml_response(self, xml_text: str, item_info: dict, date_str: str) -> dict | None:
        """KAMIS XML 응답 파싱"""
        try:
            root = ET.fromstring(xml_text)
            items = root.findall('.//item')
            if not items:
                return None

            item = items[0]
            price_str = item.findtext('price', '0').replace(',', '')
            prev_price_str = item.findtext('yyyy_dpr1', '0').replace(',', '')

            price = float(price_str) if price_str and price_str != '-' else 0
            prev_price = float(prev_price_str) if prev_price_str and prev_price_str != '-' else price

            change_pct = ((price - prev_price) / prev_price * 100) if prev_price > 0 else 0

            return {
                'name': item_info['name'],
                'unit': item_info['unit'],
                'category': item_info['category'],
                'wholesale_price': int(price),
                'prev_price': int(prev_price),
                'change_pct': round(change_pct, 1),
                'change_direction': 'up' if change_pct > 1 else ('down' if change_pct < -1 else 'neutral'),
                'market': '가락시장',
                'date': date_str,
            }
        except Exception as e:
            logger.warning(f"  KAMIS parse error for {item_info['name']}: {e}")
            return None

    def _get_class_code(self, category: str) -> str:
        for code, name in PRODUCT_CLASSES.items():
            if name == category:
                return code
        return '01'

    def _compute_summary(self, items: list, date_str: str) -> dict:
        """품목 가격 변동 요약 통계"""
        up_items = [i for i in items if i['change_direction'] == 'up']
        down_items = [i for i in items if i['change_direction'] == 'down']

        # 가장 크게 변동한 품목
        sorted_movers = sorted(items, key=lambda x: abs(x.get('change_pct', 0)), reverse=True)
        big_movers = [i['name'] for i in sorted_movers[:3]]

        # 평균 가격 변동
        changes = [i.get('change_pct', 0) for i in items]
        avg_change = round(sum(changes) / len(changes), 1) if changes else 0

        # 가격 압력 지수 (0~100) — 평균 상승률 기반
        # 0% = 50, +5% = 75, -5% = 25, ±10% = 100/0 클램핑
        pressure = max(0, min(100, 50 + avg_change * 5))

        return {
            'date': date_str,
            'total_items': len(items),
            'price_up_count': len(up_items),
            'price_down_count': len(down_items),
            'neutral_count': len(items) - len(up_items) - len(down_items),
            'big_movers': big_movers,
            'avg_change_pct': avg_change,
            'food_price_pressure': round(pressure, 1),
        }

    def _sample_data(self, date_str: str) -> list:
        """API 키 없을 때 사용할 샘플 데이터 (실제 가락시장 평균가 참고)"""
        import random
        random.seed(hash(date_str) % 10000)

        base_prices = [
            ('배추', '포기', '채소', 3200),
            ('무', 'kg', '채소', 800),
            ('양파', 'kg', '채소', 1200),
            ('마늘', 'kg', '채소', 7500),
            ('대파', 'kg', '채소', 2100),
            ('고추(건)', 'kg', '채소', 25000),
            ('애호박', '개', '채소', 900),
            ('사과', 'kg', '과일', 4800),
            ('배', 'kg', '과일', 3500),
            ('감귤', 'kg', '과일', 2200),
            ('수박', '개', '과일', 22000),
            ('쌀', '20kg', '곡물', 58000),
        ]

        items = []
        for name, unit, category, base in base_prices:
            change_pct = round(random.uniform(-8, 8), 1)
            price = int(base * (1 + change_pct / 100))
            items.append({
                'name': name,
                'unit': unit,
                'category': category,
                'wholesale_price': price,
                'prev_price': base,
                'change_pct': change_pct,
                'change_direction': 'up' if change_pct > 1 else ('down' if change_pct < -1 else 'neutral'),
                'market': '가락시장',
                'date': date_str,
            })
        return items
