"""KakaoTalk 채널 포스터 — 카카오톡 채널 메시지 발송

카카오 비즈메시지 API를 통해 채널 친구에게 알림톡을 발송합니다.
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)


def post_to_kakao_channel(title: str, description: str, url: str):
    """카카오톡 채널 메시지 발송

    카카오 비즈메시지 API를 통해 채널 친구에게 피드형 메시지를 발송합니다.
    https://developers.kakao.com/docs/latest/ko/message/rest-api
    """
    rest_api_key = os.getenv('KAKAO_REST_API_KEY')
    access_token = os.getenv('KAKAO_ACCESS_TOKEN')

    if not rest_api_key or not access_token:
        logger.warning("Kakao credentials not set")
        return False

    try:
        # 카카오 피드 메시지 템플릿
        template_object = {
            'object_type': 'feed',
            'content': {
                'title': title,
                'description': description,
                'image_url': '',
                'link': {
                    'web_url': url,
                    'mobile_web_url': url,
                },
            },
            'buttons': [
                {
                    'title': '자세히 보기',
                    'link': {
                        'web_url': url,
                        'mobile_web_url': url,
                    },
                }
            ],
        }

        resp = requests.post(
            'https://kapi.kakao.com/v2/api/talk/memo/default/send',
            headers={'Authorization': f'Bearer {access_token}'},
            data={'template_object': str(template_object)},
            timeout=30,
        )
        resp.raise_for_status()
        logger.info("Kakao channel message sent")
        return True
    except Exception as e:
        logger.error(f"Kakao channel post failed: {e}")
        return False
