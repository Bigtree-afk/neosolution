"""Telegram 포스터 — 관리자 알림 + 채널 포스팅"""

import logging
import os

import requests

logger = logging.getLogger(__name__)


def send_alert(message: str):
    """관리자 알림 전송"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        logger.warning("Telegram credentials not set")
        return

    try:
        requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json={'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'},
            timeout=10,
        )
    except Exception as e:
        logger.error(f"Telegram alert failed: {e}")


def post_to_channel(title: str, description: str, url: str):
    """채널에 포스트 알림 전송"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    channel = os.getenv('TELEGRAM_CHANNEL_KO')
    if not token or not channel:
        logger.warning("Telegram channel credentials not set")
        return

    message = f"*{title}*\n\n{description}\n\n[전문 보기]({url})"

    try:
        requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json={'chat_id': channel, 'text': message, 'parse_mode': 'Markdown'},
            timeout=10,
        )
        logger.info("Telegram channel post sent")
    except Exception as e:
        logger.error(f"Telegram channel post failed: {e}")
