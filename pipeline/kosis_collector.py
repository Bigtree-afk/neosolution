"""KOSISCollector — 통계청 KOSIS API 수집기

소매판매액지수, 서비스업생산지수, 소비자물가지수 등을 수집합니다.
"""

import logging
import os

import requests

from pipeline.base_collector import BaseCollector

logger = logging.getLogger(__name__)

# KOSIS API 지표 정의
INDICATORS = {
    'retail_sales_index': {
        'name': '소매판매액지수',
        'orgId': '101',
        'tblId': 'DT_1KE10041',
        'itmId': 'T10',
        'objL1': '00',
    },
    'service_production_index': {
        'name': '서비스업생산지수',
        'orgId': '101',
        'tblId': 'DT_1KE20051',
        'itmId': 'T10',
        'objL1': '00',
    },
    'consumer_price_index': {
        'name': '소비자물가지수',
        'orgId': '101',
        'tblId': 'DT_1J20003',
        'itmId': 'T10',
        'objL1': '00',
    },
}


class KOSISCollector(BaseCollector):
    """통계청 KOSIS API 수집기"""

    API_BASE = 'https://kosis.kr/openapi/Param/statisticsParameterData.do'

    def collect(self, date_str: str, **kwargs) -> dict:
        cached = self._load_cached(date_str, 'kosis')
        if cached:
            return cached

        api_key = os.getenv('KOSIS_API_KEY')
        if not api_key:
            logger.warning("  KOSIS_API_KEY not set, using empty data")
            return {}

        data = {}
        for key, indicator in INDICATORS.items():
            try:
                result = self._fetch_indicator(api_key, indicator, date_str)
                data[key] = {
                    'name': indicator['name'],
                    'values': result,
                }
                logger.info(f"  KOSIS {indicator['name']}: {len(result)} records")
            except Exception as e:
                logger.warning(f"  KOSIS {indicator['name']} failed: {e}")
                data[key] = {'name': indicator['name'], 'values': []}

        self._save(data, date_str, 'kosis')
        return data

    def _fetch_indicator(self, api_key: str, indicator: dict, date_str: str) -> list:
        """KOSIS API에서 지표 데이터 조회"""
        # 최근 12개월 데이터 요청
        year = date_str[:4]
        start_period = f'{int(year) - 1}01'
        end_period = date_str[:4] + date_str[5:7]

        resp = requests.get(
            self.API_BASE,
            params={
                'method': 'getList',
                'apiKey': api_key,
                'itmId': indicator['itmId'],
                'objL1': indicator['objL1'],
                'orgId': indicator['orgId'],
                'tblId': indicator['tblId'],
                'format': 'json',
                'jsonVD': 'Y',
                'prdSe': 'M',
                'startPrdDe': start_period,
                'endPrdDe': end_period,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
