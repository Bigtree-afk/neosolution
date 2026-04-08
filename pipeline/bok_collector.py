"""BOKCollector — 한국은행 경제통계시스템 API 수집기

기준금리, 소비자심리지수(CSI), 가계신용 등을 수집합니다.
"""

import logging
import os

import requests

from pipeline.base_collector import BaseCollector

logger = logging.getLogger(__name__)

# BOK API 지표 정의
INDICATORS = {
    'base_rate': {
        'name': '기준금리',
        'stat_code': '722Y001',
        'item_code': '0101000',
    },
    'consumer_sentiment': {
        'name': '소비자심리지수(CSI)',
        'stat_code': '511Y002',
        'item_code': 'FME',
    },
    'household_credit': {
        'name': '가계신용',
        'stat_code': '151Y013',
        'item_code': 'BBAA00',
    },
}


class BOKCollector(BaseCollector):
    """한국은행 경제통계시스템 API 수집기"""

    API_BASE = 'https://ecos.bok.or.kr/api'

    def collect(self, date_str: str, **kwargs) -> dict:
        cached = self._load_cached(date_str, 'bok')
        if cached:
            return cached

        api_key = os.getenv('BOK_API_KEY')
        if not api_key:
            logger.warning("  BOK_API_KEY not set, using empty data")
            return {}

        data = {}
        for key, indicator in INDICATORS.items():
            try:
                result = self._fetch_indicator(api_key, indicator, date_str)
                data[key] = {
                    'name': indicator['name'],
                    'values': result,
                }
                logger.info(f"  BOK {indicator['name']}: {len(result)} records")
            except Exception as e:
                logger.warning(f"  BOK {indicator['name']} failed: {e}")
                data[key] = {'name': indicator['name'], 'values': []}

        self._save(data, date_str, 'bok')
        return data

    def _fetch_indicator(self, api_key: str, indicator: dict, date_str: str) -> list:
        """BOK API에서 지표 데이터 조회"""
        year = date_str[:4]
        start_date = f'{int(year) - 1}01'
        end_date = date_str[:4] + date_str[5:7]

        url = (
            f"{self.API_BASE}/StatisticSearch/{api_key}/json/kr/1/100/"
            f"{indicator['stat_code']}/M/{start_date}/{end_date}/{indicator['item_code']}"
        )

        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        result = resp.json()

        rows = result.get('StatisticSearch', {}).get('row', [])
        return rows
