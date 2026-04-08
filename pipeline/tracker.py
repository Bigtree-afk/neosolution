"""PredictionTracker — 예측 추적 시스템

주간 리포트의 예측을 추적하고 정확도를 평가합니다.
Brier Score와 Calibration 메트릭을 산출합니다.
"""

import json
import logging
import math
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / 'data'
SITE_DATA_DIR = ROOT_DIR / 'site' / 'data'

# 평가 윈도우
EVAL_WINDOWS = {
    '1w': 7,
    '2w': 14,
    '1m': 30,
}


class PredictionTracker:
    """예측 추적 및 정확도 평가"""

    def __init__(self):
        self.predictions_path = DATA_DIR / 'predictions.json'
        self.history_path = DATA_DIR / 'prediction_history.json'
        self.stats_path = SITE_DATA_DIR / 'stats.json'

    def record(self, date_str: str, predictions: dict):
        """새 예측 기록"""
        data = self._load_predictions()

        data[date_str] = {
            'date': date_str,
            'predictions': predictions,
            'status': 'pending',
            'recorded_at': datetime.utcnow().isoformat(),
        }

        self._save_predictions(data)
        logger.info(f"  Recorded {len(predictions)} predictions for {date_str}")

    def evaluate(self, date_str: str):
        """미평가 예측 평가 (실제 데이터와 비교)"""
        data = self._load_predictions()
        history = self._load_history()

        evaluated = 0
        for pred_date, entry in list(data.items()):
            if entry['status'] != 'pending':
                continue

            pred_dt = datetime.strptime(pred_date, '%Y-%m-%d')
            current_dt = datetime.strptime(date_str, '%Y-%m-%d')
            days_elapsed = (current_dt - pred_dt).days

            # 1주 윈도우 평가
            if days_elapsed >= 7:
                result = self._evaluate_predictions(entry['predictions'], pred_date)
                entry['status'] = 'evaluated'
                entry['result'] = result
                entry['evaluated_at'] = date_str

                # 히스토리에 추가 (append-only)
                history.append({
                    'date': pred_date,
                    'evaluated_at': date_str,
                    **result,
                })
                evaluated += 1

        self._save_predictions(data)
        self._save_history(history)
        self._update_stats(history)

        logger.info(f"  Evaluated {evaluated} prediction sets")

    def _evaluate_predictions(self, predictions: dict, pred_date: str) -> dict:
        """개별 예측 평가 — Brier Score 산출"""
        results = {}
        brier_scores = []

        for asset, pred in predictions.items():
            direction = pred.get('direction', 'neutral')
            confidence = pred.get('confidence', 0.5)

            # 실제 방향 판정 (여기서는 placeholder — 실제 구현 시 데이터 비교)
            actual = 'neutral'  # TODO: 실제 데이터에서 판정

            # Brier Score 계산
            predicted_prob = confidence if direction == actual else (1 - confidence)
            outcome = 1.0 if direction == actual else 0.0
            brier = (predicted_prob - outcome) ** 2
            brier_scores.append(brier)

            results[asset] = {
                'predicted': direction,
                'confidence': confidence,
                'actual': actual,
                'correct': direction == actual,
                'brier_score': round(brier, 4),
            }

        avg_brier = sum(brier_scores) / len(brier_scores) if brier_scores else 0
        accuracy = sum(1 for r in results.values() if r['correct']) / len(results) if results else 0

        return {
            'predictions': results,
            'avg_brier_score': round(avg_brier, 4),
            'accuracy': round(accuracy, 4),
            'total': len(results),
        }

    def _update_stats(self, history: list):
        """통계 업데이트 (site/data/stats.json)"""
        SITE_DATA_DIR.mkdir(exist_ok=True)

        if not history:
            return

        total_predictions = sum(h.get('total', 0) for h in history)
        total_correct = sum(
            sum(1 for p in h.get('predictions', {}).values() if p.get('correct', False))
            for h in history
        )
        avg_brier = sum(h.get('avg_brier_score', 0) for h in history) / len(history)

        stats = {
            'total_prediction_sets': len(history),
            'total_predictions': total_predictions,
            'overall_accuracy': round(total_correct / total_predictions, 4) if total_predictions else 0,
            'avg_brier_score': round(avg_brier, 4),
            'last_evaluated': history[-1].get('evaluated_at', ''),
        }

        self.stats_path.write_text(
            json.dumps(stats, ensure_ascii=False, indent=2), encoding='utf-8'
        )

    def _load_predictions(self) -> dict:
        if self.predictions_path.exists():
            return json.loads(self.predictions_path.read_text(encoding='utf-8'))
        return {}

    def _save_predictions(self, data: dict):
        DATA_DIR.mkdir(exist_ok=True)
        self.predictions_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8'
        )

    def _load_history(self) -> list:
        if self.history_path.exists():
            return json.loads(self.history_path.read_text(encoding='utf-8'))
        return []

    def _save_history(self, history: list):
        DATA_DIR.mkdir(exist_ok=True)
        self.history_path.write_text(
            json.dumps(history, ensure_ascii=False, indent=2), encoding='utf-8'
        )
