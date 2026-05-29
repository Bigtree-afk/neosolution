"""BaseCollector — 모든 수집기의 기본 인터페이스"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / 'data'


class BaseCollector:
    """모든 수집기의 기본 인터페이스

    사용법:
        class MyCollector(BaseCollector):
            def collect(self, date_str, **kwargs):
                cached = self._load_cached(date_str, 'my_data')
                if cached:
                    return cached
                data = self._fetch_data(date_str)
                self._save(data, date_str, 'my_data')
                return data
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.data_dir = DATA_DIR
        self.data_dir.mkdir(exist_ok=True)

    def collect(self, date_str: str, **kwargs) -> dict | list | None:
        """데이터 수집 — 서브클래스에서 구현"""
        raise NotImplementedError

    def _save(self, data, date_str: str, prefix: str) -> Path:
        """수집 데이터를 JSON으로 캐시 저장"""
        path = self.data_dir / f'{prefix}_{date_str}.json'
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8'
        )
        logger.info(f"  Saved: {path}")
        return path

    def _load_cached(self, date_str: str, prefix: str):
        """캐시된 데이터 로드 (없으면 None)"""
        path = self.data_dir / f'{prefix}_{date_str}.json'
        if path.exists():
            logger.info(f"  Using cached: {path}")
            return json.loads(path.read_text(encoding='utf-8'))
        return None
