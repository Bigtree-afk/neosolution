"""NCI 차트 생성기 — 네오 소비지수 게이지/트렌드 차트"""

import json
import logging
from pathlib import Path

import plotly.graph_objects as go

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent.parent.parent

COLORS = {
    'overall': '#2563eb',
    'restaurant': '#059669',
    'retail': '#8b5cf6',
    'food_mart': '#f59e0b',
}

LABELS = {
    'overall': '종합',
    'restaurant': '외식업',
    'retail': '유통/소매',
    'food_mart': '식자재',
}


def generate_nci_gauge(nci_scores: dict, date_str: str, output_dir: Path) -> Path:
    """NCI 게이지 바 차트 생성"""
    output_dir.mkdir(parents=True, exist_ok=True)

    categories = list(nci_scores.keys())
    values = list(nci_scores.values())
    colors = [COLORS.get(c, '#64748b') for c in categories]
    labels = [LABELS.get(c, c) for c in categories]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=labels,
        x=values,
        orientation='h',
        marker_color=colors,
        text=[f'{v:.0f}' for v in values],
        textposition='outside',
        textfont=dict(size=14, color='#1e293b'),
    ))

    fig.update_layout(
        title=dict(text=f'네오 소비지수 (NCI) — {date_str}', font=dict(size=16)),
        xaxis=dict(range=[0, 100], title='', showgrid=True, gridcolor='#e2e8f0'),
        yaxis=dict(title='', autorange='reversed'),
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=100, r=60, t=50, b=30),
        height=250,
        width=700,
        font=dict(family='sans-serif'),
    )

    filepath = output_dir / f'nci_{date_str}.png'
    fig.write_image(str(filepath), scale=2)
    logger.info(f"  NCI gauge: {filepath}")
    return filepath


def generate_nci_trend(history: dict, output_dir: Path) -> Path:
    """NCI 시계열 트렌드 차트 생성"""
    output_dir.mkdir(parents=True, exist_ok=True)

    dates = sorted(history.keys())
    fig = go.Figure()

    for category in ['overall', 'restaurant', 'retail', 'food_mart']:
        values = [history[d].get(category, 0) for d in dates]
        fig.add_trace(go.Scatter(
            x=dates,
            y=values,
            name=LABELS.get(category, category),
            line=dict(color=COLORS.get(category, '#64748b'), width=2),
            mode='lines+markers',
            marker=dict(size=5),
        ))

    fig.update_layout(
        title=dict(text='네오 소비지수 추이', font=dict(size=16)),
        xaxis=dict(title=''),
        yaxis=dict(title='NCI', range=[0, 100]),
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(orientation='h', y=-0.15),
        margin=dict(l=50, r=30, t=50, b=60),
        height=350,
        width=700,
        font=dict(family='sans-serif'),
    )

    filepath = output_dir / 'nci_trend.png'
    fig.write_image(str(filepath), scale=2)
    logger.info(f"  NCI trend: {filepath}")
    return filepath
