"""Naver Blog 포스터 — 네이버 블로그 자동 포스팅

Naver Blog API를 통해 인사이트 콘텐츠를 자동 발행합니다.
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)


def post_to_naver_blog(title: str, body_html: str, tags: list = None):
    """네이버 블로그에 글 작성

    네이버 블로그 API는 OAuth 2.0 인증이 필요합니다.
    https://developers.naver.com/docs/blog/post/
    """
    client_id = os.getenv('NAVER_CLIENT_ID')
    client_secret = os.getenv('NAVER_CLIENT_SECRET')
    blog_id = os.getenv('NAVER_BLOG_ID')

    if not all([client_id, client_secret, blog_id]):
        logger.warning("Naver Blog credentials not set")
        return False

    # TODO: OAuth 2.0 토큰 갱신 로직 구현
    # 네이버 블로그 API는 사용자 인증이 필요하므로
    # 별도의 토큰 관리 시스템이 필요합니다.

    tag_str = ','.join(tags) if tags else ''

    try:
        # 네이버 블로그 글쓰기 API
        resp = requests.post(
            'https://openapi.naver.com/blog/writePost.json',
            headers={
                'Authorization': f'Bearer {os.getenv("NAVER_ACCESS_TOKEN", "")}',
            },
            data={
                'title': title,
                'contents': body_html,
                'categoryNo': '',
                'tags': tag_str,
            },
            timeout=30,
        )
        resp.raise_for_status()
        logger.info("Naver Blog post published")
        return True
    except Exception as e:
        logger.error(f"Naver Blog post failed: {e}")
        return False
