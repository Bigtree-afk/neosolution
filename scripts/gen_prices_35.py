"""35개 품목 prices.json 생성 — 도매가 + 산지가 포함, 90일치 이력"""
import json, random, math
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

# ─────────────────────────────────────────────
# 품목 정의: (slug, name, unit, category, base_price, origin_ratio)
# origin_ratio: 산지가 / 도매가 비율 (0.55~0.75)
# ─────────────────────────────────────────────
ITEMS = [
    # 채소 (13개)
    ("baechoo",   "배추",      "포기", "채소", 3200,  0.62),
    ("moo",       "무",        "kg",   "채소",  850,  0.60),
    ("yangpa",    "양파",      "kg",   "채소", 1300,  0.63),
    ("maneul",    "마늘",      "kg",   "채소", 7500,  0.65),
    ("daepa",     "대파",      "kg",   "채소", 2200,  0.60),
    ("gochu",     "고추(건)",  "kg",   "채소",25000,  0.68),
    ("aehobak",   "애호박",    "개",   "채소",  900,  0.58),
    ("sigeumchi", "시금치",    "kg",   "채소", 4500,  0.60),
    ("ooi",       "오이",      "개",   "채소",  450,  0.62),
    ("danggeun",  "당근",      "kg",   "채소", 1800,  0.63),
    ("sangchu",   "상추",      "kg",   "채소", 5500,  0.58),
    ("kkaennip",  "깻잎",      "100g", "채소", 2200,  0.60),
    ("paprika",   "파프리카",  "kg",   "채소", 6500,  0.65),

    # 과일 (7개)
    ("sagwa",     "사과",      "kg",   "과일", 5500,  0.65),
    ("bae",       "배",        "kg",   "과일", 3500,  0.63),
    ("gamgyul",   "감귤",      "kg",   "과일", 2000,  0.62),
    ("subak",     "수박",      "개",   "과일",24000,  0.60),
    ("ttalgi",    "딸기",      "kg",   "과일", 9000,  0.65),
    ("podo",      "포도",      "kg",   "과일", 8500,  0.67),
    ("banana",    "바나나",    "kg",   "과일", 2800,  0.70),

    # 수산물 (8개)
    ("godeungeo", "고등어",    "kg",   "수산물", 6500,  0.68),
    ("galchi",    "갈치",      "kg",   "수산물",15000,  0.65),
    ("ojingeo",   "오징어",    "마리", "수산물", 2800,  0.66),
    ("jogi",      "조기",      "kg",   "수산물",12000,  0.67),
    ("saeu",      "새우(흰다리)", "kg","수산물",18000,  0.68),
    ("kkotge",    "꽃게",      "kg",   "수산물",22000,  0.65),
    ("dongtae",   "명태(동태)", "kg",  "수산물", 5500,  0.70),
    ("gul",       "굴",        "kg",   "수산물",15000,  0.63),

    # 축산물 (4개)
    ("samgyeopsal","삼겹살",   "100g", "축산물", 2400,  0.72),
    ("hanwoo",    "한우(등심)", "100g","축산물", 9800,  0.75),
    ("dak",       "닭고기",    "kg",   "축산물", 5200,  0.70),
    ("dalgyul",   "달걀",      "10개", "축산물", 2800,  0.73),

    # 곡물 (3개)
    ("ssal",      "쌀",        "20kg", "곡물",  58000, 0.72),
    ("milgaru",   "밀가루",    "kg",   "곡물",   1200, 0.70),
    ("gochugaru", "고춧가루",  "kg",   "곡물",  28000, 0.68),
]

# ─────────────────────────────────────────────
# 날씨 데이터 (계절 기반)
# ─────────────────────────────────────────────
WEATHER_POOL = {
    "winter":  [
        {"condition": "맑음",   "icon": "☀️",  "temp_max": 3,  "temp_min": -5},
        {"condition": "흐림",   "icon": "☁️",  "temp_max": 1,  "temp_min": -4},
        {"condition": "눈",     "icon": "❄️",  "temp_max": 0,  "temp_min": -6},
        {"condition": "구름많음","icon": "🌤️", "temp_max": 4,  "temp_min": -3},
    ],
    "spring":  [
        {"condition": "맑음",   "icon": "☀️",  "temp_max": 18, "temp_min": 7},
        {"condition": "구름많음","icon": "🌤️", "temp_max": 15, "temp_min": 6},
        {"condition": "흐림",   "icon": "☁️",  "temp_max": 13, "temp_min": 5},
        {"condition": "비",     "icon": "🌧️", "temp_max": 11, "temp_min": 6},
        {"condition": "맑음",   "icon": "☀️",  "temp_max": 20, "temp_min": 8},
    ],
    "summer":  [
        {"condition": "맑음",   "icon": "☀️",  "temp_max": 33, "temp_min": 24},
        {"condition": "소나기", "icon": "⛈️",  "temp_max": 28, "temp_min": 23},
        {"condition": "흐림",   "icon": "☁️",  "temp_max": 29, "temp_min": 22},
        {"condition": "맑음",   "icon": "☀️",  "temp_max": 35, "temp_min": 25},
    ],
    "autumn":  [
        {"condition": "맑음",   "icon": "☀️",  "temp_max": 22, "temp_min": 10},
        {"condition": "구름많음","icon": "🌤️", "temp_max": 18, "temp_min": 9},
        {"condition": "흐림",   "icon": "☁️",  "temp_max": 16, "temp_min": 8},
        {"condition": "비",     "icon": "🌧️", "temp_max": 14, "temp_min": 9},
    ],
}

def get_season(d: date) -> str:
    m = d.month
    if m in (12, 1, 2):  return "winter"
    if m in (3, 4, 5):   return "spring"
    if m in (6, 7, 8):   return "summer"
    return "autumn"

def pick_weather(d: date) -> dict:
    pool = WEATHER_POOL[get_season(d)]
    w = random.choice(pool)
    var = random.uniform(-2, 2)
    return {
        "condition": w["condition"],
        "icon":      w["icon"],
        "temp_max":  round(w["temp_max"] + var, 1),
        "temp_min":  round(w["temp_min"] + var, 1),
    }

# ─────────────────────────────────────────────
# 가격 시계열 생성 (sine wave + noise)
# ─────────────────────────────────────────────
def gen_prices(base: int, days: int = 90) -> list[int]:
    prices = []
    p = float(base)
    for i in range(days):
        # 계절 사이클 + 랜덤 노이즈
        seasonal = math.sin(2 * math.pi * i / 90) * base * 0.08
        noise = random.gauss(0, base * 0.015)
        p = max(base * 0.5, min(base * 1.8, p + seasonal * 0.3 + noise))
        prices.append(int(round(p / 10) * 10))
    return prices

# ─────────────────────────────────────────────
# 메인 생성 로직
# ─────────────────────────────────────────────
today = date(2026, 4, 9)
START = today - timedelta(days=89)   # 90일치

result = []

for slug, name, unit, category, base_price, origin_ratio in ITEMS:
    daily_prices = gen_prices(base_price, 90)

    # daily 레코드 (최신순)
    daily = []
    for i in range(90):
        d = START + timedelta(days=i)
        price = daily_prices[i]
        prev  = daily_prices[i - 1] if i > 0 else price
        chg   = round((price - prev) / prev * 100, 1) if prev else 0.0
        origin = int(round(price * origin_ratio / 10) * 10)

        rec = {
            "date":        d.isoformat(),
            "price":       price,
            "change_pct":  chg,
            "direction":   "up" if chg > 0 else ("down" if chg < 0 else "neutral"),
            "origin_price": origin,
            "weather":     pick_weather(d),
        }
        daily.append(rec)

    daily.reverse()  # 최신이 앞으로

    # weekly 집계 (최신 12주)
    weekly = []
    for w in range(12):
        week_days = [daily_prices[-(7 * w + j + 1)] for j in range(7) if (7 * w + j + 1) <= 90]
        if not week_days: continue
        week_start = today - timedelta(days=7 * w + 6)
        iso_week   = week_start.isocalendar()
        weekly.append({
            "week": f"{iso_week[0]}-W{iso_week[1]:02d}",
            "avg":  int(sum(week_days) / len(week_days)),
            "min":  min(week_days),
            "max":  max(week_days),
        })

    # monthly 집계 (최신 3개월)
    monthly = []
    for m_off in range(3):
        month_date = today.replace(day=1)
        for _ in range(m_off):
            month_date = (month_date - timedelta(days=1)).replace(day=1)
        m_prices = [
            daily_prices[i]
            for i in range(90)
            if (START + timedelta(days=i)).replace(day=1) == month_date
        ]
        if not m_prices: continue
        monthly.append({
            "month": month_date.strftime("%Y-%m"),
            "avg":   int(sum(m_prices) / len(m_prices)),
            "min":   min(m_prices),
            "max":   max(m_prices),
        })

    result.append({
        "slug":     slug,
        "name":     name,
        "unit":     unit,
        "category": category,
        "market":   "가락시장",
        "daily":    daily,
        "weekly":   weekly,
        "monthly":  monthly,
    })

out_path = Path(__file__).parent.parent / "site" / "data" / "prices.json"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"✅ prices.json 생성 완료: {len(result)}개 품목, 출력: {out_path}")

# 카테고리별 요약 출력
from collections import Counter
cats = Counter(item[3] for item in ITEMS)
for cat, cnt in sorted(cats.items()):
    print(f"   {cat}: {cnt}개")
