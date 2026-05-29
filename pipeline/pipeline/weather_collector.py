"""날씨 수집기 — Open-Meteo API (무료, API키 불필요)

서울(가락시장 기준) 일일 날씨 데이터를 수집한다.
API: https://open-meteo.com/
"""

import logging
from datetime import datetime
from pathlib import Path

import requests

from pipeline.base_collector import BaseCollector

logger = logging.getLogger(__name__)

# 서울 좌표 (가락시장 인근)
SEOUL_LAT = 37.5665
SEOUL_LON = 126.9780

# WMO 날씨 코드 → 한국어 + 이모지
WMO_CODE_MAP = {
    0:  ('맑음',        '☀️'),
    1:  ('대체로 맑음', '🌤️'),
    2:  ('구름 많음',  '⛅'),
    3:  ('흐림',        '☁️'),
    45: ('안개',        '🌫️'),
    48: ('짙은 안개',  '🌫️'),
    51: ('이슬비',      '🌦️'),
    53: ('이슬비',      '🌦️'),
    55: ('강한 이슬비', '🌦️'),
    61: ('비',          '🌧️'),
    63: ('비',          '🌧️'),
    65: ('강한 비',     '🌧️'),
    71: ('눈',          '🌨️'),
    73: ('눈',          '🌨️'),
    75: ('강한 눈',     '🌨️'),
    77: ('싸락눈',      '🌨️'),
    80: ('소나기',      '🌦️'),
    81: ('소나기',      '🌦️'),
    82: ('강한 소나기', '⛈️'),
    85: ('눈 소나기',   '🌨️'),
    86: ('눈 소나기',   '🌨️'),
    95: ('뇌우',        '⛈️'),
    96: ('우박 뇌우',   '⛈️'),
    99: ('우박 뇌우',   '⛈️'),
}


class WeatherCollector(BaseCollector):
    """Open-Meteo 날씨 수집기 (서울 기준)"""

    BASE_URL = 'https://api.open-meteo.com/v1/forecast'

    def collect(self, date_str: str, **kwargs) -> dict:
        """일일 날씨 데이터 수집

        Returns:
            {
                'date': str,
                'temp_max': float,   # 최고기온 (°C)
                'temp_min': float,   # 최저기온 (°C)
                'precipitation': float,  # 강수량 (mm)
                'weathercode': int,
                'condition': str,    # 한국어 날씨 설명
                'condition_icon': str,  # 이모지
                'source': 'open-meteo'
            }
        """
        cached = self._load_cached(date_str, 'weather')
        if cached:
            return cached

        logger.info(f"  Weather: Collecting for {date_str}")

        try:
            params = {
                'latitude': SEOUL_LAT,
                'longitude': SEOUL_LON,
                'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode',
                'timezone': 'Asia/Seoul',
                'start_date': date_str,
                'end_date': date_str,
            }
            resp = requests.get(self.BASE_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            daily = data.get('daily', {})
            dates = daily.get('time', [])

            if not dates:
                logger.warning("  Weather: No data returned")
                return self._fallback(date_str)

            idx = 0
            weathercode = int(daily['weathercode'][idx])
            condition, icon = WMO_CODE_MAP.get(weathercode, ('알 수 없음', '❓'))

            result = {
                'date': date_str,
                'temp_max': round(daily['temperature_2m_max'][idx], 1),
                'temp_min': round(daily['temperature_2m_min'][idx], 1),
                'precipitation': round(daily['precipitation_sum'][idx] or 0.0, 1),
                'weathercode': weathercode,
                'condition': condition,
                'condition_icon': icon,
                'source': 'open-meteo',
            }

            self._save(result, date_str, 'weather')
            return result

        except Exception as e:
            logger.warning(f"  Weather: Failed ({e}) — using fallback")
            return self._fallback(date_str)

    def _fallback(self, date_str: str) -> dict:
        """API 실패 시 기본값"""
        return {
            'date': date_str,
            'temp_max': None,
            'temp_min': None,
            'precipitation': None,
            'weathercode': None,
            'condition': '정보 없음',
            'condition_icon': '—',
            'source': 'fallback',
        }
