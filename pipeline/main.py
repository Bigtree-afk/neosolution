"""NeoSolution 콘텐츠 파이프라인 — 4-Phase 오케스트레이션

Phase 1: Collection  — 공공 데이터 + 뉴스 수집
Phase 2: Analysis    — NCI/ISI 산출 + Claude AI 분석
Phase 3: Generation  — 콘텐츠 생성 (주간/월간/가이드)
Phase 4: Publishing  — Hugo 마크다운 발행 + git push
"""

import argparse
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / 'data'
SITE_DIR = ROOT_DIR / 'site'

KST = timezone(timedelta(hours=9))

# 콘텐츠 타입별 프롬프트 매핑
CONTENT_PROMPTS = {
    'weekly': 'prompts/blog_writer_weekly_ko.txt',
    'monthly': 'prompts/blog_writer_monthly_ko.txt',
    'guide': 'prompts/blog_writer_guide_ko.txt',
    'special': 'prompts/blog_writer_special_ko.txt',
}

# 선택 수집기 (실패해도 파이프라인 계속)
OPTIONAL_COLLECTORS = {
    # 'card_data': CardDataCollector,
    # 'smba': SMBACollector,
    # 'food_price': FoodPriceCollector,
    # 'weather': WeatherCollector,
}


def run_collection(date_str: str, content_type: str) -> dict:
    """Phase 1: 데이터 수집"""
    logger.info(f"Phase 1: Collection ({date_str}, {content_type})")

    from pipeline.collector import NewsCollector
    from pipeline.kosis_collector import KOSISCollector
    from pipeline.bok_collector import BOKCollector

    # 필수 수집 (실패 시 중단)
    news = NewsCollector().collect(date_str)
    kosis = KOSISCollector().collect(date_str)
    bok = BOKCollector().collect(date_str)

    # 선택 수집 (실패 시 None)
    optional = {}
    for name, collector_cls in OPTIONAL_COLLECTORS.items():
        try:
            optional[name] = collector_cls().collect(date_str)
            logger.info(f"  {name}: OK")
        except Exception as e:
            logger.warning(f"  {name} failed (non-fatal): {e}")
            optional[name] = None

    return {
        'news': news,
        'kosis': kosis,
        'bok': bok,
        **optional,
    }


def run_analysis(collected: dict, date_str: str, content_type: str) -> dict:
    """Phase 2: NCI/ISI 산출 + AI 분석"""
    logger.info(f"Phase 2: Analysis ({date_str}, {content_type})")

    from pipeline.analyzer import ConsumptionAnalyzer

    # 캐시 확인
    cache_path = DATA_DIR / f'analysis_{date_str}_{content_type}.json'
    if cache_path.exists():
        logger.info("  Using cached analysis")
        return json.loads(cache_path.read_text(encoding='utf-8'))

    analyzer = ConsumptionAnalyzer()
    analysis = analyzer.analyze(collected, date_str, content_type)

    # 중간 저장
    DATA_DIR.mkdir(exist_ok=True)
    cache_path.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    return analysis


def run_generation(analysis: dict, collected: dict, date_str: str,
                   content_type: str) -> dict:
    """Phase 3: 콘텐츠 생성"""
    logger.info(f"Phase 3: Generation ({date_str}, {content_type})")

    from pipeline.generator import ContentGenerator

    prompt_path = ROOT_DIR / CONTENT_PROMPTS[content_type]
    generator = ContentGenerator(prompt_path)

    try:
        post = generator.generate(analysis, collected, date_str, content_type)
        quality = generator.validate(post)
        return {'post': post, 'quality': quality}
    except Exception as e:
        logger.error(f"  Generation failed: {e}")
        return {'post': None, 'quality': {'passed': False, 'issues': [str(e)]}}


def run_publishing(gen_result: dict, date_str: str, content_type: str,
                   analysis: dict) -> dict:
    """Phase 4: Hugo 발행"""
    logger.info(f"Phase 4: Publishing ({date_str}, {content_type})")

    from pipeline.publisher import HugoPublisher

    result = {'date': date_str, 'content_type': content_type, 'published': False}

    post = gen_result.get('post')
    quality = gen_result.get('quality', {})

    if not post or not quality.get('passed', False):
        result['skipped'] = quality.get('issues', ['No post generated'])
        logger.warning(f"  Skipped: {result['skipped']}")
        return result

    try:
        publisher = HugoPublisher(SITE_DIR)
        filepath = publisher.publish(post, date_str, content_type)
        result['published'] = True
        result['filepath'] = str(filepath)
        logger.info(f"  Published: {filepath}")
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"  Publish failed: {e}")

    return result


def main():
    parser = argparse.ArgumentParser(description='NeoSolution Content Pipeline')
    parser.add_argument('--date', type=str, default=None,
                        help='Target date YYYY-MM-DD (default: today KST)')
    parser.add_argument('--content-type',
                        choices=['weekly', 'monthly', 'guide', 'special', 'market-daily'],
                        default='weekly', help='Content type to generate')
    parser.add_argument('--collect-only', action='store_true',
                        help='Run collection phase only')
    parser.add_argument('--analyze-only', action='store_true',
                        help='Run collection + analysis only')
    parser.add_argument('--no-push', action='store_true',
                        help='Skip git push (local testing)')
    args = parser.parse_args()

    # 날짜: KST 기준 오늘
    target_date = args.date or datetime.now(KST).strftime('%Y-%m-%d')

    logger.info(f"=== NeoSolution Pipeline Start ===")
    logger.info(f"  Date: {target_date}")
    logger.info(f"  Content Type: {args.content_type}")

    # market-daily는 별도 파이프라인으로 처리
    if args.content_type == 'market-daily':
        _run_market_daily_pipeline(target_date, args.no_push)
        return

    # Phase 1: Collection
    collected = run_collection(target_date, args.content_type)
    if args.collect_only:
        logger.info("collect-only mode, stopping here")
        return

    # Phase 2: Analysis
    analysis = run_analysis(collected, target_date, args.content_type)
    if args.analyze_only:
        logger.info("analyze-only mode, stopping here")
        return

    # Phase 3: Generation
    gen_result = run_generation(analysis, collected, target_date, args.content_type)

    # Phase 4: Publishing
    pub_result = run_publishing(gen_result, target_date, args.content_type, analysis)

    # Git push (CI 환경에서만)
    if not args.no_push and os.getenv('GITHUB_ACTIONS'):
        _git_commit_and_push(pub_result)

    logger.info(f"=== Pipeline Complete ===")
    logger.info(f"  Published: {pub_result.get('published', False)}")


def _run_market_daily_pipeline(date_str: str, no_push: bool):
    """유통정보 일일 파이프라인 (market-daily 전용)"""
    logger.info(f"=== Market Daily Pipeline ({date_str}) ===")

    from pipeline.kamis_collector import KAMISCollector
    from pipeline.market_analyzer import MarketAnalyzer
    from pipeline.market_publisher import MarketPublisher

    # Step 1: 가격 수집
    logger.info("Step 1: KAMIS 가격 수집")
    kamis_data = KAMISCollector().collect(date_str)

    # Step 2: 분석 + AI 해설
    logger.info("Step 2: 시장 분석")
    analyzer = MarketAnalyzer()
    analysis = analyzer.analyze(kamis_data, date_str)

    # Step 3: Hugo 마크다운 발행
    logger.info("Step 3: Hugo 페이지 발행")
    publisher = MarketPublisher(SITE_DIR)
    filepath = publisher.publish(analysis, date_str)
    logger.info(f"  Published: {filepath}")

    # Step 4: Git push
    if not no_push and os.getenv('GITHUB_ACTIONS'):
        _git_commit_and_push({
            'published': True,
            'date': date_str,
            'content_type': 'market-daily',
            'filepath': str(filepath),
        })

    logger.info("=== Market Daily Pipeline Complete ===")


def _git_commit_and_push(pub_result: dict):
    """CI 환경에서 Hugo 콘텐츠를 커밋하고 푸시"""
    import subprocess

    if not pub_result.get('published'):
        logger.info("  Nothing to push")
        return

    try:
        subprocess.run(['git', 'add', 'site/content/', 'site/data/', 'data/'],
                       check=True, cwd=str(ROOT_DIR))
        subprocess.run(
            ['git', 'diff', '--staged', '--quiet'],
            cwd=str(ROOT_DIR)
        )
        logger.info("  No changes to commit")
    except subprocess.CalledProcessError:
        # Changes exist, commit them
        date_str = pub_result['date']
        content_type = pub_result['content_type']
        subprocess.run(
            ['git', 'commit', '-m', f'Publish {content_type} {date_str}'],
            check=True, cwd=str(ROOT_DIR)
        )
        subprocess.run(['git', 'push'], check=True, cwd=str(ROOT_DIR))
        logger.info("  Pushed to remote")


if __name__ == '__main__':
    main()
