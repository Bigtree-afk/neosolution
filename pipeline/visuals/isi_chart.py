"""ISI 차트 생성기 — 업종별 경기체감지수 바 차트"""

import logging
from pathlib import Path

import plotly.graph_objects as go

logger = logging.getLogger(__name__)

LABELS = {
    'general_restaurant': '일반음식점',
    'cafe_bakery': '카페/제과',
    'convenience': '편의점',
    'supermarket': '슈퍼/마트',
    'food_distribution': '식자재유통',
    'clothing': '의류/잡화',
}


def generate_isi_chart(isi_scores: dict, date_str: str, output_dir: Path) -> Path:
    """ISI 바 차트 생성"""
    output_dir.mkdir(parents=True, exist_ok=True)

    categories = list(isi_scores.keys())
    values = list(isi_scores.values())
    labels = [LABELS.get(c, c) for c in categories]

    # 50 기준선 색상 분류
    colors = ['#16a34a' if v >= 50 else '#dc2626' for v in values]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=labels,
        y=values,
        marker_color=colors,
        text=[f'{v:.0f}' for v in values],
        textposition='outside',
        textfont=dict(size=13, color='#1e293b'),
    ))

    # 50 기준선
    fig.add_hline(y=50, line_dash='dash', line_color='#94a3b8',
                  annotation_text='기준선(50)', annotation_position='bottom right')

    fig.update_layout(
        title=dict(text=f'업종별 경기체감지수 (ISI) — {date_str}', font=dict(size=16)),
        xaxis=dict(title=''),
        yaxis=dict(title='ISI', range=[0, 100]),
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=50, r=30, t=50, b=30),
        height=300,
        width=700,
        font=dict(family='sans-serif'),
    )

    filepath = output_dir / f'isi_{date_str}.png'
    fig.write_image(str(filepath), scale=2)
    logger.info(f"  ISI chart: {filepath}")
    return filepath
