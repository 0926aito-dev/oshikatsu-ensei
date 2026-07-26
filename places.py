import re

import requests

PREFECTURES = [
    "北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島",
    "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
    "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜",
    "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫",
    "奈良", "和歌山", "鳥取", "島根", "岡山", "広島", "山口",
    "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎",
    "熊本", "大分", "宮崎", "鹿児島", "沖縄",
]

MAJOR_CITIES = [
    "さいたま", "横浜", "川崎", "千葉市", "名古屋", "神戸",
    "札幌", "仙台", "京都市", "大阪市", "広島市", "福岡市",
    "北九州", "渋谷", "六本木", "有明", "幕張", "舞浜",
    "池袋", "新宿", "中野", "立川", "横須賀", "静岡市",
]

PLACE_KEYWORDS = sorted(set(PREFECTURES + MAJOR_CITIES), key=len, reverse=True)

VENUE_SUFFIXES = [
    "ホール", "アリーナ", "ドーム", "スタジアム", "会館",
    "劇場", "体育館", "センター", "公会堂",
]

VENUE_PATTERN = re.compile(
    r"[一-龥ぁ-んァ-ヶーA-Za-z0-9]{1,15}(?:" + "|".join(VENUE_SUFFIXES) + ")"
)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "oshikatsu-ensei (+https://github.com/0926aito-dev/oshikatsu-ensei)"


def _context(text, start, end, radius=15):
    return text[max(0, start - radius):min(len(text), end + radius)].strip()


def extract_place_candidates(text):
    if not text:
        return []

    candidates = {}

    for keyword in PLACE_KEYWORDS:
        index = text.find(keyword)
        if index != -1 and keyword not in candidates:
            candidates[keyword] = _context(text, index, index + len(keyword))

    for match in VENUE_PATTERN.finditer(text):
        place_text = match.group(0)
        if len(place_text) >= 2 and place_text not in candidates:
            candidates[place_text] = _context(text, match.start(), match.end())

    return [
        {"place_text": place_text, "context": context}
        for place_text, context in candidates.items()
    ]


def geocode(place_text, http_get=requests.get):
    try:
        response = http_get(
            NOMINATIM_URL,
            params={
                "q": place_text,
                "format": "json",
                "limit": 1,
                "accept-language": "ja",
            },
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        response.raise_for_status()
        results = response.json()
    except (requests.RequestException, ValueError):
        return None

    if not results:
        return None

    result = results[0]
    return float(result["lat"]), float(result["lon"]), result.get("display_name", place_text)
