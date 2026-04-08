"""Monitor — R2 스토리지 및 파이프라인 상태 모니터링"""

import logging
import os

logger = logging.getLogger(__name__)


def check_r2_usage():
    """Cloudflare R2 스토리지 사용량 확인"""
    import boto3

    access_key = os.getenv('R2_ACCESS_KEY')
    secret_key = os.getenv('R2_SECRET_KEY')
    endpoint = os.getenv('R2_ENDPOINT')

    if not all([access_key, secret_key, endpoint]):
        logger.warning("R2 credentials not set")
        return

    s3 = boto3.client(
        's3',
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )

    # 버킷 목록 조회
    try:
        response = s3.list_buckets()
        for bucket in response.get('Buckets', []):
            name = bucket['Name']
            # 오브젝트 수 카운트
            objects = s3.list_objects_v2(Bucket=name)
            count = objects.get('KeyCount', 0)
            logger.info(f"  R2 bucket '{name}': {count} objects")

            if count > 5000:
                from pipeline.telegram_poster import send_alert
                send_alert(f"R2 bucket '{name}' has {count} objects (threshold: 5000)")

    except Exception as e:
        logger.error(f"R2 check failed: {e}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    check_r2_usage()
