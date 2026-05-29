"""ContentGenerator — Claude AI를 통한 콘텐츠 생성

분석 결과를 바탕으로 주간/월간/가이드 콘텐츠를 생성합니다.
"""

import json
import logging
import os
from pathlib import Path

import anthropic

logger = logging.getLogger(__name__)


class ContentGenerator:
    """콘텐츠 생성기"""

    def __init__(self, prompt_path: Path):
        self.prompt_template = prompt_path.read_text(encoding='utf-8')
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate(self, analysis: dict, collected: dict, date_str: str,
                 content_type: str) -> dict:
        """분석 결과를 바탕으로 콘텐츠 생성"""

        prompt = self.prompt_template.format(
            date=date_str,
            content_type=content_type,
            nci_scores=json.dumps(analysis.get('nci_scores', {}), ensure_ascii=False),
            isi_scores=json.dumps(analysis.get('isi_scores', {}), ensure_ascii=False),
            ai_analysis=json.dumps(analysis.get('ai_analysis', {}), ensure_ascii=False),
            news_summary=json.dumps(analysis.get('news_summary', []), ensure_ascii=False),
        )

        response = self.client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=4000,
            messages=[{'role': 'user', 'content': prompt}],
        )

        content = response.content[0].text

        # JSON 응답 파싱
        try:
            # ```json ... ``` 블록 추출
            if '```json' in content:
                start = content.index('```json') + 7
                end = content.index('```', start)
                content = content[start:end].strip()
            return json.loads(content)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"  Failed to parse JSON response: {e}")
            # 폴백: 원문 텍스트를 body로 사용
            return {
                'title': f'{date_str} 소비 트렌드',
                'slug': f'trend-{date_str}',
                'description': '',
                'tags': [],
                'body': content,
            }

    def validate(self, post: dict) -> dict:
        """생성된 콘텐츠 품질 검증"""
        issues = []

        title = post.get('title', '')
        body = post.get('body', '')

        if len(title) < 5:
            issues.append('제목이 너무 짧습니다 (5자 미만)')
        if len(title) > 100:
            issues.append('제목이 너무 깁니다 (100자 초과)')
        if len(body) < 300:
            issues.append('본문이 너무 짧습니다 (300자 미만)')
        if not post.get('slug'):
            issues.append('slug가 없습니다')

        return {
            'passed': len(issues) == 0,
            'issues': issues,
            'title_length': len(title),
            'body_length': len(body),
        }
