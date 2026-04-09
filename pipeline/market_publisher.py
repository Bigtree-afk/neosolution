"""시장 가격 페이지 발행기 — Hugo 마크다운 생성

일일 가락시장 가격 분석 결과를 Hugo 마크다운 파일로 발행한다.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))


class MarketPublisher:
    """일일 시장 가격 Hugo 마크다운 발행기"""

    def __init__(self, site_dir: Path):
        self.site_dir = Path(site_dir)
        self.content_dir = self.site_dir / 'content' / 'ko' / 'distribution' / 'daily'
        self.content_dir.mkdir(parents=True, exist_ok=True)

    def publish(self, analysis: dict, date_str: str) -> Path:
        """분석 결과를 Hugo 마크다운으로 저장

        Returns:
            생성된 파일 경로
        """
        front_matter = self._build_front_matter(analysis, date_str)
        body = self._build_body(analysis, date_str)

        # 파일명: 2026-04-09-market-prices.md
        filename = f"{date_str}-market-prices.md"
        filepath = self.content_dir / filename

        content = '---\n' + yaml.dump(
            front_matter,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        ) + '---\n\n' + body

        filepath.write_text(content, encoding='utf-8')
        logger.info(f"  Market page published: {filepath}")
        return filepath

    def _build_front_matter(self, analysis: dict, date_str: str) -> dict:
        """Hugo 프론트매터 구성"""
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        weekday = ['월', '화', '수', '목', '금', '토', '일'][date_obj.weekday()]
        date_iso = date_obj.replace(tzinfo=KST).strftime('%Y-%m-%dT07:00:00+09:00')

        summary = analysis.get('market_summary', {})
        alert = analysis.get('price_alert', {})

        fm = {
            'title': f"{date_str} ({weekday}) 가락시장 주요 가격 동향",
            'date': date_iso,
            'slug': f"market-{date_str}",
            'description': alert.get('message', '오늘의 가락시장 농산물 가격 동향'),
            'content_type': 'market-daily',
            'draft': False,
            'market_summary': {
                'price_up_count': summary.get('price_up_count', 0),
                'price_down_count': summary.get('price_down_count', 0),
                'neutral_count': summary.get('neutral_count', 0),
                'big_movers': summary.get('big_movers', []),
                'avg_change_pct': summary.get('avg_change_pct', 0),
                'food_price_pressure': summary.get('food_price_pressure', 50),
            },
            'market_prices': analysis.get('market_prices', []),
            'price_alert': alert,
            'ai_comment': analysis.get('ai_comment', ''),
        }
        return fm

    def _build_body(self, analysis: dict, date_str: str) -> str:
        """마크다운 본문 (간단한 데이터 설명)"""
        summary = analysis.get('market_summary', {})
        alert = analysis.get('price_alert', {})
        ai_comment = analysis.get('ai_comment', '')
        pressure = summary.get('food_price_pressure', 50)

        lines = []
        lines.append(f"## 오늘의 시장 요약\n")
        lines.append(f"{ai_comment}\n")
        lines.append(
            f"오늘 가락시장에서는 총 {summary.get('total_items', 0)}개 품목을 모니터링했습니다. "
            f"전일 대비 **{summary.get('price_up_count', 0)}개 품목 상승**, "
            f"**{summary.get('price_down_count', 0)}개 품목 하락**, "
            f"**{summary.get('neutral_count', 0)}개 품목 보합**이었습니다.\n"
        )

        movers = summary.get('big_movers', [])
        if movers:
            lines.append(f"특히 **{'**, **'.join(movers)}** 등의 변동 폭이 컸습니다.\n")

        lines.append(f"\n## 식자재가격압력지수\n")
        pressure_label = (
            '고압 (원가 부담 증가)' if pressure >= 65 else
            '주의 (일부 상승)' if pressure >= 55 else
            '안정' if pressure >= 45 else
            '완화 (원가 부담 감소)'
        )
        lines.append(f"**{pressure:.0f}/100** — {pressure_label}\n")
        lines.append(
            "식자재가격압력지수는 도매가격 변동을 종합한 원가 압력 지표입니다. "
            "50이 중립이며, 높을수록 식자재 원가 부담이 크다는 뜻입니다.\n"
        )

        lines.append(f"\n## 구매 참고 정보\n")
        alert_msg = alert.get('message', '')
        if alert_msg:
            lines.append(f"> {alert_msg}\n")

        lines.append("\n---\n")
        lines.append(
            "*본 가격 정보는 KAMIS(농산물유통정보)를 기반으로 자동 수집된 데이터입니다. "
            "실제 거래 시에는 현장 가격을 반드시 확인하세요.*\n"
        )

        return '\n'.join(lines)
