"""
规则解析器：把用户自然语言 prompt 解析成结构化搜索参数。
不依赖 LLM，完全靠关键词匹配，作为 MVP 第一版使用。
"""

import re


# 高德 POI 类型码
CATEGORY_MAP = {
    "park":       ("公园|广场|绿地|草地|湖|河边|骑行", "110100|110101|110102|110103"),
    "cafe":       ("咖啡|coffee|拿铁|下午茶|奶茶|茶饮|果茶", "050118|050000"),
    "bookstore":  ("书店|书|图书馆|阅读",              "060100|080703"),
    "museum":     ("博物馆|展览|美术馆|展馆",           "080300|080301|080302"),
    "restaurant": ("餐厅|吃饭|饭|烤肉|火锅|面|饺子|麦当劳|mcdonald|肯德基|kfc|汉堡|炸鸡|快餐", "050000"),
    "mall":       ("商场|购物|逛街|超市",               "060200|060201"),
    "outdoor":    ("户外|爬山|自然|风景",               "110100|110200"),
    "gym":        ("健身|运动|游泳|跑步",               "090301|090302"),
}

# 默认兜底：涵盖公园+咖啡+书店+博物馆
DEFAULT_TYPES = "110100|050118|060100|080300"
FOOD_FOCUS_TYPES = "050000|050118"

KEYWORD_INTENT_RULES = [
    {
        "pattern": r"奶茶|茶饮|果茶|喜茶|奈雪|茶百道|沪上阿姨|霸王茶姬|益禾堂|一点点|coco|ko(i|ï)",
        "must_keywords": ["奶茶", "茶饮", "饮品", "果茶"],
        "exclude_keywords": ["棋牌", "棋牌室", "足疗", "洗浴", "网吧"],
        "poi_types": FOOD_FOCUS_TYPES,
    },
    {
        "pattern": r"麦当劳|mcdonald|麦麦|肯德基|kfc|汉堡王|burger\s*king|快餐|汉堡|炸鸡",
        "must_keywords": ["麦当劳", "mcdonald", "肯德基", "kfc", "汉堡", "快餐"],
        "exclude_keywords": ["棋牌", "棋牌室", "足疗", "洗浴", "网吧"],
        "poi_types": FOOD_FOCUS_TYPES,
    },
]

TRANSPORT_SPEED = {
    "walk":   83,   # m/min (约5km/h)
    "bike":   250,  # m/min (约15km/h)
    "subway": 500,  # m/min (地铁+步行综合)
}

TRANSPORT_DEFAULT_RADIUS = {
    "walk":   1500,
    "bike":   4000,
    "subway": 8000,
}

TRANSPORT_LABEL = {
    "walk": "步行",
    "bike": "骑车",
    "subway": "地铁",
}


def _unique_keep_order(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        token = item.strip()
        if not token:
            continue
        norm = token.lower()
        if norm in seen:
            continue
        seen.add(norm)
        out.append(token)
    return out


def parse_intent(prompt: str) -> dict:
    """
    返回结构：
    {
        "radius_m": int,
        "poi_types": str,           # 高德类型码，"|" 分隔
        "keywords": str,            # 关键词搜索补充
        "transport": str,           # walk/bike/subway
        "budget_max": int | None,   # None = 不限
        "open_now": bool,
    }
    """
    text = prompt.lower()

    # 1. 通勤方式
    transport = "bike"  # 默认骑车
    if re.search(r"步行|走路|走过去|11路", text):
        transport = "walk"
    elif re.search(r"地铁|公交|坐车|开车|打车|taxi", text):
        transport = "subway"
    elif re.search(r"骑车|骑行|自行车|电动|单车", text):
        transport = "bike"

    # 2. 搜索半径（优先从时间推算，其次用通勤默认值）
    radius_m = TRANSPORT_DEFAULT_RADIUS[transport]
    time_match = re.search(r"(\d+)\s*(分钟|min)", text)
    if time_match:
        minutes = int(time_match.group(1))
        speed = TRANSPORT_SPEED[transport]
        radius_m = min(minutes * speed, 15000)  # 最大15km

    # 3. 预算
    budget_max = None
    if re.search(r"免费|¥0|0元|不花钱", text):
        budget_max = 0
    elif re.search(r"不限|随便|无所谓", text):
        budget_max = None
    else:
        budget_match = re.search(r"预算\s*[¥￥]?\s*(\d+)|[¥￥]\s*(\d+)|(\d+)\s*[元块]", text)
        if budget_match:
            val = next(v for v in budget_match.groups() if v is not None)
            budget_max = int(val)

    # 4. POI 类型（从氛围/场景关键词推断）
    matched_types = []
    matched_keywords = []
    must_keywords: list[str] = []
    exclude_keywords: list[str] = []
    forced_types: list[str] = []

    for rule in KEYWORD_INTENT_RULES:
        if re.search(rule["pattern"], text):
            must_keywords.extend(rule["must_keywords"])
            exclude_keywords.extend(rule["exclude_keywords"])
            forced_types.append(rule["poi_types"])

    for key, (pattern, type_code) in CATEGORY_MAP.items():
        if re.search(pattern, text):
            matched_types.append(type_code)
            matched_keywords.append(key)

    if forced_types:
        poi_types = "|".join(_unique_keep_order(forced_types))
    elif matched_types:
        poi_types = "|".join(matched_types)
    else:
        poi_types = DEFAULT_TYPES  # 兜底：公园+咖啡+书店+博物馆

    # 5. 补充关键词搜索（用于 Amap keywords 参数）
    keywords = ""
    if must_keywords:
        keywords = " ".join(_unique_keep_order(must_keywords))
    elif re.search(r"安静|一个人|独处|宁静", text):
        keywords = "公园 书店 咖啡"
    elif re.search(r"热闹|朋友|聚会|约", text):
        keywords = "商场 餐厅 咖啡"
    elif re.search(r"新鲜|探索|好玩|有意思", text):
        keywords = "展览 文化 创意园"

    return {
        "radius_m": radius_m,
        "poi_types": poi_types,
        "keywords": keywords,
        "transport": transport,
        "budget_max": budget_max,
        "open_now": True,
        "must_keywords": _unique_keep_order(must_keywords),
        "exclude_keywords": _unique_keep_order(exclude_keywords),
    }


def eta_min(distance_m: int, transport: str) -> int:
    speed = TRANSPORT_SPEED.get(transport, TRANSPORT_SPEED["bike"])
    return max(1, round(distance_m / speed))


def transport_label(transport: str) -> str:
    return TRANSPORT_LABEL.get(transport, TRANSPORT_LABEL["bike"])


def budget_text(price_level: str | None, budget_max: int | None) -> str:
    """把高德 price_level (0-4) + 用户预算上限转成显示文字。"""
    level_map = {
        "0": "¥0",
        "1": "¥0-30",
        "2": "¥30-80",
        "3": "¥80-150",
        "4": "¥150+",
    }
    if price_level in level_map:
        return level_map[price_level]
    if budget_max == 0:
        return "¥0"
    if budget_max is not None:
        return f"¥0-{budget_max}"
    return "不限"


# 规则模板：根据 POI 类型生成 ai_judgement 和 risk_label
_JUDGEMENT_TEMPLATES: dict[str, list[str]] = {
    "公园":     ["现在去比较轻松，适合随便走走", "绿化好，空气不错，适合放空"],
    "广场":     ["开放空间，人多但不逼你社交", "适合随便坐坐"],
    "咖啡":     ["坐一小时不会有负担", "距离近，点一杯可以待很久"],
    "书店":     ["安静，适合一个人翻翻书", "不买也可以逛，低压力"],
    "博物馆":   ["有新鲜感，适合随便逛逛", "展品多，可以只看感兴趣的"],
    "美术馆":   ["安静有质感，适合慢慢看", "视觉体验不错"],
    "图书馆":   ["最安静的选择，适合独处", "免费，可以待很久"],
    "餐厅":     ["适合和朋友去，环境热闹", "吃完可以附近溜达"],
    "商场":     ["逛累了可以坐下来，选择多", "适合漫无目的地走走"],
    "default":  ["适合现在去", "离你不远，可以试试"],
}

_RISK_TEMPLATES: dict[str, str] = {
    "公园":   "傍晚人会变多",
    "广场":   "周末人流量大",
    "咖啡":   "周末下午可能排队",
    "书店":   "营业时间注意确认",
    "博物馆": "节假日需要提前预约",
    "餐厅":   "用餐高峰期等位",
    "商场":   "节假日比较拥挤",
}


def make_judgement(poi_type: str) -> str:
    import random
    for key, templates in _JUDGEMENT_TEMPLATES.items():
        if key in poi_type:
            return random.choice(templates)
    return random.choice(_JUDGEMENT_TEMPLATES["default"])


def make_risk_label(poi_type: str) -> str | None:
    for key, risk in _RISK_TEMPLATES.items():
        if key in poi_type:
            return risk
    return None
