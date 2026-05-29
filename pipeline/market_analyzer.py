"""시장 가격 분석기 — 일일 유통정보 분석

KAMIS 가격 데이터를 분석하고 Claude AI로 시장 동향 해설을 생성한다.
"""

import json
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class MarketAnalyzer:
    """일일 시장 가격 분석 및 Claude AI 해설 생성"""

    def __init__(self):
        self.api_key = os.getenv('ANTHROPIC_API_KEY', '')

    def analyze(self, kamis_data: dict, date_str: str) -> dict:
        """
        Args:
            kamis_data: KAMISCollector.collect() 반환값
            date_str: 분석 날짜

        Returns:
            {
                'date': str,
                'market_summary': dict,
                'market_prices': list[{category, items}],
                'price_alert': dict,
                'ai_comment': str,
                'food_price_pressure': float,  # 0~100
            }
        """
        items = kamis_data.get('items', [])
        summary = kamis_data.get('summary', {})

        # 카테고리별 그룹핑
        market_prices = self._group_by_category(items)

        # 가격 경보 레벨 결정
        price_alert = self._compute_alert(summary, items)

        # Claude AI 해설 (API 키 있을 때만)
        ai_comment = ''
        if self.api_key:
            ai_comment = self._generate_ai_comment(items, summary, date_str)
        else:
            ai_comment = self._generate_fallback_comment(summary, items, date_str)

        return {
            'date': date_str,
            'market_summary': summary,
            'market_prices': market_prices,
            'price_alert': price_alert,
            'ai_comment': ai_comment,
            'food_price_pressure': summary.get('food_price_pressure', 50.0),
        }

    def _group_by_category(self, items: list) -> list:
        """품목을 카테고리별로 그룹핑"""
        categories = {}
        for item in items:
            cat = item.get('category', '기타')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)

        # 카테고리 순서: 채소 → 과일 → 수산 → 축산 → 곡물
        order = ['채소', '과일', '수산', '축산', '곡물', '기타']
        result = []
        for cat in order:
            if cat in categories:
                result.append({
                    'category': cat,
                    'items': categories[cat],
                })
        return result

    def _compute_alert(self, summary: dict, items: list) -> dict:
        """가격 경보 레벨 결정"""
        pressure = summary.get('food_price_pressure', 50)
        up_count = summary.get('price_up_count', 0)
        total = summary.get('total_items', 1)
        up_ratio = up_count / total if total > 0 else 0

        # 큰 변동 품목 (±10% 이상)
        big_movers = [i for i in items if abs(i.get('change_pct', 0)) >= 10]

        if pressure >= 70 or up_ratio >= 0.7:
            level = 'warning'
            biggest = max(items, key=lambda x: x.get('change_pct', 0), default={})
            name = biggest.get('name', '')
            change = biggest.get('change_pct', 0)
            message = f"{name} 가격 {abs(change):.1f}% 급등 — 원가 상승 압력 증가"
        elif pressure >= 60 or up_ratio >= 0.5:
            level = 'caution'
            movers = summary.get('big_movers', [])
            names = ', '.join(movers[:2]) if movers else '일부 품목'
            message = f"{names} 등 주요 식자재 가격 상승세 — 원가 주의 필요"
        elif pressure <= 35 or up_ratio <= 0.2:
            level = 'favorable'
            biggest_down = min(items, key=lambda x: x.get('change_pct', 0), default={})
            name = biggest_down.get('name', '')
            change = biggest_down.get('change_pct', 0)
            message = f"전반적 가격 안정 — {name} 등 식자재 원가 부담 완화"
        else:
            level = 'normal'
            message = "주요 식자재 가격 안정적 — 전일 대비 큰 변동 없음"

        return {'level': level, 'message': message}

    def _generate_ai_comment(self, items: list, summary: dict, date_str: str) -> str:
        """Claude AI 일일 시장 해설 생성"""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)

            items_summary = []
            for item in sorted(items, key=lambda x: abs(x.get('change_pct', 0)), reverse=True)[:6]:
                direction = '▲' if item['change_direction'] == 'up' else ('▼' if item['change_direction'] == 'down' else '→')
                items_summary.append(
                    f"{item['name']}: {item['wholesale_price']:,}원/{item['unit']} "
                    f"({direction}{abs(item.get('change_pct', 0)):.1f}%)"
                )

            prompt = f"""오늘({date_str}) 가락시장 주요 품목 가격 현황:
{chr(10).join(items_summary)}

전체 {summary['total_items']}개 품목 중 상승 {summary['price_up_count']}개, 하락 {summary['price_down_count']}개.
식자재가격압력지수: {summary['food_price_pressure']:.0f}/100

외식업 사장님과 식자재업체 담당자를 위해 오늘 시장 동향을 3문장으로 간결하게 해설해 주세요.
원가 영향과 구매 타이밍 힌트를 포함하세요. 한국어로 작성하세요."""

            response = client.messages.create(
                model='claude-haiku-4-5-20251001',  # 빠른 일일 해설에는 Haiku 사용
                max_tokens=300,
                messages=[{'role': 'user', 'content': prompt}],
            )
            return response.content[0].text.strip()

        except Exception as e:
            logger.warning(f"  AI comment generation failed: {e}")
            return self._generate_fallback_comment(summary, items, date_str)

    def _generate_fallback_comment(self, summary: dict, items: list, date_str: str) -> str:
        """API 없을 때 규칙 기반 해설 생성"""
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        weekday = ['월', '화', '수', '목', '금', '토', '일'][date_obj.weekday()]

        up = summary.get('price_up_count', 0)
        down = summary.get('price_down_count', 0)
        pressure = summary.get('food_price_pressure', 50)
        movers = summary.get('big_movers', [])
        movers_str = ', '.join(movers) if movers else '주요 품목'

        if pressure >= 65:
            trend = f"{movers_str} 중심으로 가격 상승세가 두드러집니다. 식자재 원가 부담이 커질 수 있어 사전 비축을 검토하세요."
        elif pressure <= 40:
            trend = f"전반적으로 가격이 안정되거나 하락했습니다. {movers_str} 등은 저가 구매 기회가 될 수 있습니다."
        else:
            trend = f"가격 등락이 혼조세입니다. {movers_str}의 변동 폭이 컸으며, 나머지 품목은 안정적입니다."

        return f"{date_str}({weekday}요일) 가락시장: {up}개 품목 상승, {down}개 하락. {trend}"
