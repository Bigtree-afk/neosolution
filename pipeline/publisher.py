"""HugoPublisher — Hugo 마크다운 발행기

생성된 콘텐츠를 Hugo 마크다운 파일로 작성합니다.
"""

import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

# 콘텐츠 타입별 디렉토리 매핑
CONTENT_DIRS = {
    'weekly': 'ko/insights/weekly',
    'monthly': 'ko/insights/monthly',
    'guide': 'ko/guides/operations',
    'special': 'ko/insights/special',
}

# 콘텐츠 타입별 카테고리
CONTENT_CATEGORIES = {
    'weekly': ['주간분석'],
    'monthly': ['월간분석'],
    'guide': ['소상공인가이드'],
    'special': ['특별리포트'],
}


class HugoPublisher:
    """Hugo 마크다운 발행기"""

    def __init__(self, site_dir: Path):
        self.site_dir = site_dir
        self.content_dir = site_dir / 'content'

    def publish(self, post: dict, date_str: str, content_type: str) -> Path:
        """콘텐츠를 Hugo 마크다운 파일로 발행"""

        # 디렉토리 결정
        rel_dir = CONTENT_DIRS.get(content_type, 'ko/insights')
        target_dir = self.content_dir / rel_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        # 파일명 생성
        slug = post.get('slug', f'{content_type}-{date_str}')
        filename = f'{date_str}-{slug}.md'
        filepath = target_dir / filename

        # Front matter 구성
        front_matter = self._build_front_matter(post, date_str, content_type)

        # 마크다운 작성
        body = post.get('body', '')
        content = f"---\n{yaml.dump(front_matter, allow_unicode=True, default_flow_style=False)}---\n\n{body}\n"

        filepath.write_text(content, encoding='utf-8')
        logger.info(f"  Published: {filepath}")

        # NCI 데이터 업데이트
        self._update_nci_data(post, date_str)

        return filepath

    def _build_front_matter(self, post: dict, date_str: str, content_type: str) -> dict:
        """YAML front matter 구성"""
        now_kst = datetime.now(KST)
        publish_date = f"{date_str}T09:00:00+09:00"

        fm = {
            'title': post.get('title', ''),
            'date': publish_date,
            'slug': post.get('slug', ''),
            'description': post.get('description', ''),
            'content_type': content_type,
            'tags': post.get('tags', []),
            'categories': CONTENT_CATEGORIES.get(content_type, []),
            'draft': False,
        }

        # NCI/ISI 점수 (있으면 포함)
        if 'nci_scores' in post:
            fm['nci_scores'] = post['nci_scores']
        if 'isi_scores' in post:
            fm['isi_scores'] = post['isi_scores']

        # 예측 (있으면 포함)
        if 'predictions' in post:
            fm['predictions'] = post['predictions']

        # 핵심 숫자 (있으면 포함)
        if 'key_numbers' in post:
            fm['key_numbers'] = post['key_numbers']

        # 인사이트 (있으면 포함)
        if 'insight' in post:
            fm['insight'] = post['insight']

        # 내일 시그널 (있으면 포함)
        if 'tomorrow_signals' in post:
            fm['tomorrow_signals'] = post['tomorrow_signals']

        # Opus 분석 결과 필드 (있으면 포함)
        for field in ['macro_context', 'cross_sector_dynamics',
                      'food_price_snapshot', 'seasonal_context']:
            if field in post:
                fm[field] = post[field]

        # 차트 이미지 (있으면 포함)
        if 'chart_images' in post:
            fm['chart_images'] = post['chart_images']

        # OG 이미지 (있으면 포함)
        if 'og_image' in post:
            fm['og_image'] = post['og_image']

        return fm

    def _update_nci_data(self, post: dict, date_str: str):
        """site/data/nci_history.json 업데이트"""
        import json

        data_dir = self.site_dir / 'data'
        data_dir.mkdir(exist_ok=True)

        history_path = data_dir / 'nci_history.json'
        history = {}
        if history_path.exists():
            history = json.loads(history_path.read_text(encoding='utf-8'))

        nci = post.get('nci_scores')
        if nci:
            history[date_str] = nci

            # nci_latest.json 도 업데이트 (홈페이지 표시용)
            latest_path = data_dir / 'nci_latest.json'
            latest_path.write_text(
                json.dumps(nci, ensure_ascii=False, indent=2), encoding='utf-8'
            )

        history_path.write_text(
            json.dumps(history, ensure_ascii=False, indent=2), encoding='utf-8'
        )
