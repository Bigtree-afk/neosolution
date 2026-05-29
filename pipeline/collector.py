"""NewsCollector — 뉴스 수집기

유통/외식/결제 업계 뉴스를 NewsAPI와 RSS 피드에서 수집합니다.
"""

import logging
import os
from datetime import datetime, timedelta

import feedparser
import requests

from pipeline.base_collector import BaseCollector

logger = logging.getLogger(__name__)

# RSS 피드 소스 (유통/외식/결제 관련)
RSS_FEEDS = {
    '매일경제': 'https://www.mk.co.kr/rss/30100041/',
    '한국경제': 'https://www.hankyung.com/feed/economy',
    '이데일리': 'https://rss.edaily.co.kr/edaily_economy.xml',
}

# 뉴스 검색 키워드
KEYWORDS = [
    '소비 트렌드', '외식업 매출', '소매판매', '식자재 가격',
    '소상공인', 'POS', 'VAN', '카드결제', '편의점 매출',
    '유통업 동향', '프랜차이즈', '배달 시장', '식품 물가',
]


class NewsCollector(BaseCollector):
    """뉴스 수집기 (NewsAPI + RSS)"""

    def collect(self, date_str: str, **kwargs) -> list:
        cached = self._load_cached(date_str, 'news')
        if cached:
            return cached

        articles = []

        # NewsAPI 수집
        api_key = os.getenv('NEWS_API_KEY')
        if api_key:
            try:
                articles.extend(self._fetch_newsapi(api_key, date_str))
            except Exception as e:
                logger.warning(f"  NewsAPI failed: {e}")

        # RSS 수집
        for source, url in RSS_FEEDS.items():
            try:
                articles.extend(self._fetch_rss(source, url, date_str))
            except Exception as e:
                logger.warning(f"  RSS {source} failed: {e}")

        logger.info(f"  Collected {len(articles)} articles")
        self._save(articles, date_str, 'news')
        return articles

    def _fetch_newsapi(self, api_key: str, date_str: str) -> list:
        """NewsAPI에서 관련 뉴스 검색"""
        from_date = (datetime.strptime(date_str, '%Y-%m-%d') - timedelta(days=7)).strftime('%Y-%m-%d')
        query = ' OR '.join(KEYWORDS[:5])

        resp = requests.get(
            'https://newsapi.org/v2/everything',
            params={
                'q': query,
                'from': from_date,
                'to': date_str,
                'language': 'ko',
                'sortBy': 'relevancy',
                'pageSize': 50,
                'apiKey': api_key,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        return [
            {
                'title': a['title'],
                'description': a.get('description', ''),
                'url': a['url'],
                'source': a['source']['name'],
                'published_at': a.get('publishedAt', ''),
                'collector': 'newsapi',
            }
            for a in data.get('articles', [])
        ]

    def _fetch_rss(self, source: str, url: str, date_str: str) -> list:
        """RSS 피드에서 기사 수집"""
        feed = feedparser.parse(url)
        articles = []

        for entry in feed.entries[:20]:
            articles.append({
                'title': entry.get('title', ''),
                'description': entry.get('summary', ''),
                'url': entry.get('link', ''),
                'source': source,
                'published_at': entry.get('published', ''),
                'collector': 'rss',
            })

        return articles
