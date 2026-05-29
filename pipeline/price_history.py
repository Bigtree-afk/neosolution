"""가격 이력 관리 — 일/주/월 단위 집계 저장

품목별 가격 데이터를 data/prices.json에 축적한다.
Hugo의 .Site.Data.prices 로 직접 접근 가능.

보존 기간: daily 90일 / weekly 52주 / monthly 24개월
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# data/prices.json — Hugo site/data/ 에도 복사해서 빌드에 포함
PRICES_FILE = Path(__file__).parent.parent / 'site' / 'data' / 'prices.json'

# 보존 기간
DAILY_KEEP = 90
WEEKLY_KEEP = 52
MONTHLY_KEEP = 24


def _week_label(date_str: str) -> str:
    """YYYY-Www 형식 주 레이블"""
    d = datetime.strptime(date_str, '%Y-%m-%d')
    return f"{d.isocalendar().year}-W{d.isocalendar().week:02d}"


def _month_label(date_str: str) -> str:
    """YYYY-MM 형식 월 레이블"""
    return date_str[:7]


def load_prices() -> list:
    """prices.json 로드 (없으면 빈 리스트)"""
    if PRICES_FILE.exists():
        try:
            return json.loads(PRICES_FILE.read_text(encoding='utf-8'))
        except Exception:
            pass
    return []


def save_prices(data: list):
    """prices.json 저장"""
    PRICES_FILE.parent.mkdir(parents=True, exist_ok=True)
    PRICES_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )


def update(kamis_items: list, date_str: str, weather: dict = None):
    """KAMIS 수집 품목 리스트로 가격 이력 업데이트

    Args:
        kamis_items: KAMISCollector.collect() 반환값의 'items' 키
        date_str: 'YYYY-MM-DD'
        weather: WeatherCollector.collect() 반환값 (선택, daily 레코드에 포함)
    """
    prices = load_prices()

    # 기존 데이터를 slug→dict 인덱스로 변환
    index = {p['slug']: p for p in prices}

    week_label = _week_label(date_str)
    month_label = _month_label(date_str)

    for item in kamis_items:
        slug = _make_slug(item['name'])
        entry = index.get(slug) or {
            'slug': slug,
            'name': item['name'],
            'unit': item['unit'],
            'category': item['category'],
            'market': item.get('market', '가락시장'),
            'daily': [],
            'weekly': [],
            'monthly': [],
        }

        price = item.get('wholesale_price', 0)
        change_pct = item.get('change_pct', 0.0)

        # ── daily ──────────────────────────────────────────
        daily_record = {
            'date': date_str,
            'price': price,
            'change_pct': round(change_pct, 1),
            'direction': item.get('change_direction', 'neutral'),
        }
        if weather:
            daily_record['weather'] = {
                'condition': weather.get('condition', ''),
                'icon': weather.get('condition_icon', ''),
                'temp_max': weather.get('temp_max'),
                'temp_min': weather.get('temp_min'),
            }
        # 중복 날짜 제거 후 앞에 삽입 (최신 → 과거 순)
        entry['daily'] = [d for d in entry['daily'] if d['date'] != date_str]
        entry['daily'].insert(0, daily_record)
        entry['daily'] = entry['daily'][:DAILY_KEEP]

        # ── weekly ─────────────────────────────────────────
        week_prices = [
            d['price'] for d in entry['daily']
            if _week_label(d['date']) == week_label and d['price'] > 0
        ]
        if week_prices:
            weekly_record = {
                'week': week_label,
                'avg': round(sum(week_prices) / len(week_prices)),
                'min': min(week_prices),
                'max': max(week_prices),
            }
            entry['weekly'] = [w for w in entry['weekly'] if w['week'] != week_label]
            entry['weekly'].insert(0, weekly_record)
            entry['weekly'] = sorted(
                entry['weekly'], key=lambda x: x['week'], reverse=True
            )[:WEEKLY_KEEP]

        # ── monthly ────────────────────────────────────────
        month_prices = [
            d['price'] for d in entry['daily']
            if d['date'][:7] == month_label and d['price'] > 0
        ]
        if month_prices:
            monthly_record = {
                'month': month_label,
                'avg': round(sum(month_prices) / len(month_prices)),
                'min': min(month_prices),
                'max': max(month_prices),
            }
            entry['monthly'] = [m for m in entry['monthly'] if m['month'] != month_label]
            entry['monthly'].insert(0, monthly_record)
            entry['monthly'] = sorted(
                entry['monthly'], key=lambda x: x['month'], reverse=True
            )[:MONTHLY_KEEP]

        index[slug] = entry

    # 리스트로 변환 후 저장
    updated = list(index.values())
    save_prices(updated)
    logger.info(f"  PriceHistory: Updated {len(kamis_items)} items → {PRICES_FILE}")
    return updated


def _make_slug(name: str) -> str:
    """품목명 → ASCII slug (Hugo data key 호환)

    한글 품목명을 영문 슬러그로 변환.
    매핑에 없는 품목은 'item-HASH' 형식 사용.
    """
    slug_map = {
        '배추': 'baechoo',
        '무': 'moo',
        '양파': 'yangpa',
        '마늘': 'maneul',
        '대파': 'daepa',
        '고추(건)': 'gochu-dried',
        '애호박': 'aehobak',
        '사과': 'sagwa',
        '배': 'bae',
        '감귤': 'gamgyul',
        '수박': 'subak',
        '쌀': 'ssal',
        '고등어': 'godeungeo',
        '갈치': 'galchi',
        '삼겹살': 'samgyeopsal',
        '달걀': 'dalgyal',
        '두부': 'dubu',
    }
    return slug_map.get(name, f"item-{abs(hash(name)) % 100000}")
