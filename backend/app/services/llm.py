"""
DeepSeek LLM 客户端（OpenAI 兼容格式）。
调用方负责降级：所有函数失败时抛异常，不在这里 catch。
"""
import json
import logging
import os
import random
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

PERSONA_CHARS = {
    # ── 通用人格（周末去哪玩） ──
    "独处型": {
        "identity": "你极度需要独处充电，对被打扰这件事零容忍，连背景噪音都会影响你的状态。",
        "thinking": "你的第一反应是：这个地方会不会有人不断经过我身边、有没有需要应付的社交。",
        "voice": (
            "说话很短，句子之间不用连接词。"
            "常用「不会」「不用」「没有人」这类否定结构来表达你觉得好的地方。"
            "结论简短干脆，像给自己记笔记。"
        ),
    },
    "探索型": {
        "identity": "你把每次出门都当成一次小小的田野调查，讨厌重复去同一个地方。",
        "thinking": "你的第一反应是：这里有没有我没见过的东西，哪怕一个细节也好。",
        "voice": (
            "说话带着轻微兴奋，喜欢用问句结尾。"
            "常用「说不定」「可能有」「不知道会不会」这类不确定语气。"
            "结论像是在邀请自己：「去看看？」。"
        ),
    },
    "务实型": {
        "identity": "你把时间和金钱都当成有限资源，讨厌任何形式的浪费，包括情绪上的浪费。",
        "thinking": "你的第一反应是：算一下，值不值，有没有坑，下雨或者人多怎么办。",
        "voice": (
            "说话像做决策报告，喜欢给出具体数字或条件。"
            "常用「够用」「合理」「不亏」「就算X也Y」这类评判结构。"
            "结论像拍板：不超过五个字，直接给结论。"
        ),
    },
    "审美型": {
        "identity": "你对空间和光线有本能的感知，一个地方好不好看会直接影响你的心情和留存时长。",
        "thinking": "你的第一反应是：这个空间的光怎么样，座位舒不舒服，有没有值得看的细节。",
        "voice": (
            "说话有画面感，喜欢用感官动词（看、感觉、进去就）。"
            "常用「如果光线好的话」「这种空间通常」「氛围对了」这类条件感知句。"
            "结论带轻微情绪：「应该挺好看的」/「期待一下」。"
        ),
    },
    # ── 午饭专项人格 ──
    "老饕": {
        "identity": "你是认真对待每一顿饭的人，吃过很多地方，难吃的东西真的会让你情绪低落。",
        "thinking": "你的第一反应是：这个品类这个价位，正常水准在哪，这家能不能达到。",
        "voice": (
            "说话带专业感，会用品类术语或烹饪逻辑作为评判标准。"
            "常用「这种价位通常」「火候/食材/比例」这类行家判断。"
            "对风险直接点名，不委婉。结论只有「去」「不去」「看情况」三种。"
        ),
    },
    "效率党": {
        "identity": "你的午休只有45分钟，每一分钟都要算清楚，出门到回来不能超时。",
        "thinking": "你的第一反应是：几分钟能到、等餐几分钟、几点必须离开——倒推时间轴。",
        "voice": (
            "说话像时间表，喜欢拆分步骤。"
            "常用「去+回=X分钟」「点单后X分钟」「高峰期加Y分钟」这类时间推算句式。"
            "结论是时间判断：「时间够用」/「有点紧」/「不建议高峰去」。"
        ),
    },
    "精算师": {
        "identity": "你在脑子里永远开着一张隐形账单，人均、份量、隐形消费都要算进去。",
        "thinking": "你的第一反应是：这个价位的实际份量，有没有强制消费，和附近同类比怎样。",
        "voice": (
            "说话像比价App，喜欢给出相对判断。"
            "常用「这个价位能吃到」「比X便宜Y」「份量如果正常的话」这类比较结构。"
            "结论是性价比评级：「划算」/「平」/「偏贵」，不超过三个字。"
        ),
    },
    "氛围感": {
        "identity": "你对吃饭的环境和仪式感极度敏感，同样的菜，在好氛围里吃会觉得更好吃。",
        "thinking": "你的第一反应是：进去的感觉怎么样，光线座位音乐，有没有让人想拍照的瞬间。",
        "voice": (
            "说话像在描述一种体验，喜欢用「进去」「坐下来」「那种感觉」作为句子主干。"
            "常用「如果环境对了」「这类地方通常」「坐下来之后」这类沉浸式描述句式。"
            "结论带情绪期待：「应该挺有感觉的」/「普通但够用」/「不是我要的氛围」。"
        ),
    },
}

_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
_BASE_URL = "https://api.deepseek.com/chat/completions"
_MODEL = "deepseek-chat"
_TIMEOUT = 8.0  # 与 engineering-bootstrap REQUEST_TIMEOUT_MS=8000 对齐

# 命运叙事角度：每次随机选一个，让每张卡片的理由都有不同切入点
NARRATIVE_ANGLES = [
    "从今天的时间节点或季节切入",
    "从用户说的那句话里，找到一个他没意识到的信号",
    "用一个反直觉的理由——为什么不是别的地方偏偏是这里",
    "从感官细节切入（光线、声音、气味、温度中的某一种）",
    "像命运在平静解释自己的选择",
    "从这个地点今天最特别的一面说起",
]


def _load_celebrity_skill(name: str) -> str:
    """Load and return skill file content with YAML frontmatter stripped."""
    skill_path = Path(__file__).parent.parent / "skills" / f"{name}.skill"
    if not skill_path.exists():
        raise FileNotFoundError(f"Celebrity skill file not found: {name}.skill")
    content = skill_path.read_text(encoding="utf-8")
    # Strip YAML frontmatter (--- ... ---)
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            content = content[end + 4:].lstrip("\n")
    return content


async def _chat(system: str, user: str, max_tokens: int = 200, temperature: float = 0.9, timeout: float | None = None) -> str:
    if not _API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY 未配置")
    async with httpx.AsyncClient(timeout=timeout or _TIMEOUT, trust_env=False) as client:
        resp = await client.post(
            _BASE_URL,
            headers={
                "Authorization": f"Bearer {_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": _MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
        )
        resp.raise_for_status()
        try:
            return resp.json()["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, ValueError) as e:
            raise RuntimeError(f"DeepSeek API 响应格式异常: {e}") from e


async def persona_review(
    *,
    poi_name: str,
    poi_type: str,
    eta_min: int,
    budget: str,
    persona: str,
    user_prompt: str,
) -> dict:
    """
    生成人格视角切片评价。
    返回 {
        "summary": str,           # 一句话结论 ≤20字，供分享卡片用
        "slices": [               # 4个场景切片
            {"scene": "to_door",  "tag": "到门口", "text": str, "emotion": str},
            {"scene": "enter",    "tag": "进入后", "text": str, "emotion": str},
            {"scene": "during",   "tag": "体验中", "text": str, "emotion": str},
            {"scene": "leave",    "tag": "总结",   "text": str, "emotion": str},
        ],
        # 向后兼容字段（从 slices 派生）
        "review": str,
        "risk": str | None,
        "conclusion": str,
    }
    """
    user_prompt = user_prompt[:300]  # 防止 prompt injection / 超长输入
    p = PERSONA_CHARS.get(persona)
    if isinstance(p, dict):
        identity = p["identity"]
        thinking = p["thinking"]
        voice    = p["voice"]
    else:
        identity = "你是一个普通都市白领。"
        thinking = "你的第一反应是这个地方合不合适。"
        voice    = "说话直接，给出简短评价。"

    scene_emoji = {
        "公园": "🌳", "咖啡": "☕", "书店": "📚",
        "博物馆": "🏛️", "餐厅": "🍽️", "商场": "🛍️",
    }
    enter_emoji = next((v for k, v in scene_emoji.items() if k in poi_type), "🚪")

    system = (
        f"你正在扮演「{persona}」。\n"
        f"{identity}\n"
        f"思维方式：{thinking}\n"
        f"说话方式：{voice}\n"
        "严格输出 JSON，不加任何其他文字，不加代码块符号。"
    )
    user = (
        f"用户说：「{user_prompt}」\n"
        f"他要去：{poi_name}（{poi_type}），{eta_min} 分钟路程，人均 {budget}。\n"
        f"以「{persona}」的角度，用你特有的说话方式，生成 4 个场景切片评价。\n"
        "每个切片 text ≤30字，emotion ≤6字（如：值得等、有点期待、不亏、随便看看）。\n"
        "summary 是一句话结论 ≤20字，供分享用。\n"
        '{"summary":"结论","slices":['
        '{"scene":"to_door","tag":"到门口","text":"...","emotion":"..."},'
        '{"scene":"enter","tag":"进入后","text":"...","emotion":"..."},'
        '{"scene":"during","tag":"体验中","text":"...","emotion":"..."},'
        '{"scene":"leave","tag":"总结","text":"...","emotion":"..."}'
        ']}'
    )
    raw = await _chat(system, user, max_tokens=500, timeout=9.0)
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"persona_review JSON 解析失败: {e}") from e

    slices = data.get("slices", [])
    summary = str(data.get("summary", ""))

    # 补全缺失切片，防止 LLM 输出不完整
    scene_defaults = [
        ("to_door", "到门口"), ("enter", "进入后"),
        ("during", "体验中"), ("leave", "总结"),
    ]
    slice_map = {s["scene"]: s for s in slices if isinstance(s, dict)}
    normalized_slices = []
    for scene_key, tag in scene_defaults:
        s = slice_map.get(scene_key, {})
        normalized_slices.append({
            "scene":   scene_key,
            "tag":     s.get("tag", tag),
            "text":    str(s.get("text", "") or "—"),
            "emotion": str(s.get("emotion", "") or "—"),
        })

    leave_slice = normalized_slices[3]
    return {
        "summary":    summary,
        "slices":     normalized_slices,
        # 向后兼容
        "review":     summary,
        "risk":       leave_slice["emotion"] or None,
        "conclusion": leave_slice["text"],
    }


async def celebrity_persona_review(
    *,
    poi_name: str,
    poi_type: str,
    eta_min: int,
    budget: str,
    celebrity_id: str,
) -> dict:
    """
    生成名人视角切片评价，使用 .skill 文件作为 system prompt。
    返回与 persona_review() 相同的 dict 格式。
    """
    system = _load_celebrity_skill(celebrity_id)
    user = (
        f"以你自己的身份和视角，评价这个目的地，帮用户决定今天是否值得去。\n"
        f"地点：{poi_name}（{poi_type}），约{eta_min}分钟路程，人均{budget}。\n\n"
        "生成：1条核心判断 + 1段深度点评 + 4个场景切片。\n\n"
        "风格要求（必须遵守）：\n"
        "- 用第一人称「我」，直接说，不要说「乔布斯会认为」\n"
        "- 二元判断：要么 insanely great，要么 shit，没有中间地带\n"
        "- 中英文自然混用，他的口头禅和标志性词汇要出现\n"
        "- summary：最核心的一句话定论，≤30字\n"
        "- review：用他的思维框架深度分析这个地方，2-3句，80-120字，"
        "要体现他的某个心智模型（聚焦/端到端/人文与技术的交汇等），有观点有温度\n"
        "- verdict：最后一句拍板辣评，≤25字，用「我」，"
        "带他最锋利的一面——可以骂、可以封神，绝不中庸，像舞台上最后一句话\n"
        "- text 字段：一句有力的判断，≤40字\n"
        "- emotion 字段：1-3个词，可以是英文\n"
        "- tag 字段保持中文：到门口 / 进入后 / 体验中 / 总结\n\n"
        "JSON输出，不加任何其他文字和代码块符号：\n"
        '{"summary":"...","review":"...","verdict":"...","slices":['
        '{"scene":"to_door","tag":"到门口","text":"...","emotion":"..."},'
        '{"scene":"enter","tag":"进入后","text":"...","emotion":"..."},'
        '{"scene":"during","tag":"体验中","text":"...","emotion":"..."},'
        '{"scene":"leave","tag":"总结","text":"...","emotion":"..."}'
        ']}'
    )
    raw = await _chat(system, user, max_tokens=1500, timeout=22.0)
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"celebrity_persona_review JSON 解析失败: {e}") from e

    slices = data.get("slices", [])
    summary = str(data.get("summary", ""))
    review_text = str(data.get("review", summary))
    verdict_text = str(data.get("verdict", ""))

    scene_defaults = [
        ("to_door", "到门口"), ("enter", "进入后"),
        ("during", "体验中"), ("leave", "总结"),
    ]
    slice_map = {s["scene"]: s for s in slices if isinstance(s, dict)}
    normalized_slices = []
    for scene_key, tag in scene_defaults:
        s = slice_map.get(scene_key, {})
        normalized_slices.append({
            "scene":   scene_key,
            "tag":     s.get("tag", tag),
            "text":    str(s.get("text", "") or "—"),
            "emotion": str(s.get("emotion", "") or "—"),
        })

    leave_slice = normalized_slices[3]
    return {
        "summary":    summary,
        "slices":     normalized_slices,
        "review":     review_text,
        "verdict":    verdict_text,
        "risk":       leave_slice["emotion"] or None,
        "conclusion": leave_slice["text"],
    }


async def pick_reason(
    *,
    poi_name: str,
    poi_type: str,
    eta_min: int,
    budget: str,
    user_prompt: str,
    context: dict | None = None,
) -> str:
    """
    生成候选卡片推荐理由（命运独白，一句话，不超过25字）。
    context 可包含：weather, temperature, weekday, hour, season, is_wild_card
    """
    angle = random.choice(NARRATIVE_ANGLES)
    is_wild = bool(context and context.get("is_wild_card"))

    ctx_parts = []
    if context:
        if context.get("weather"):
            temp = context.get("temperature", "")
            ctx_parts.append(f"{context['weather']}{f' {temp}°' if temp else ''}")
        if context.get("weekday") and context.get("hour") is not None:
            ctx_parts.append(f"{context['weekday']}{context['hour']}点")
        if context.get("season"):
            ctx_parts.append(f"{context['season']}天")
    ctx_str = "，".join(ctx_parts)

    if is_wild:
        system = (
            "你是「今天的命运」，你刚刚为这个人选了一个他根本没预料到的地方。\n"
            f"叙事角度：{angle}\n"
            "用一句话（不超过25字），用一个完全出乎意料但成立的理由，让他忍不住想去看看。\n"
            "禁止说「适合你」「推荐」「AI」。只输出这一句，不加句号。"
        )
    else:
        system = (
            "你是「今天的命运」，你刚刚为这个人选好了一个地方。\n"
            f"叙事角度：{angle}\n"
            "用一句话（不超过25字），有具体画面感，像命运在平静地说话。\n"
            "禁止说「适合你」「推荐」「AI」。禁止重复用户说过的词。只输出这一句，不加句号。"
        )
    user = (
        f"用户说：「{user_prompt}」\n"
        + (f"此刻：{ctx_str}\n" if ctx_str else "")
        + f"命运选中了：{poi_name}（{poi_type}）/ {eta_min}分钟可到 / {budget}\n"
        "命运说："
    )
    return await _chat(system, user, max_tokens=80, temperature=0.95, timeout=5.0)


async def generate_inspire() -> str:
    """
    高 temperature 随机生成一条用户出门心情描述，供首页「AI 帮我想一个」按钮使用。
    每次调用都应有不同结果。
    """
    system = (
        "你是一个随机心情发生器。生成一句简短中文（15-30字），"
        "模拟用户今天想出门的具体状态和偏好。"
        "从以下维度随机选 1-2 个加入：通勤方式（步行/骑车/地铁/驾车）、"
        "时间限制（N分钟内）、场景（一个人/约朋友/带娃）、"
        "氛围（安静/热闹/有新鲜感/有水有绿）、预算。"
        "语言要口语化有生活气息，直接描述状态，不要开头说「想去」「我想」，"
        "禁止重复示例，每次都要不同。"
    )
    user = "随机生成一条。只输出那句话，不加引号，不加其他文字。"
    return await _chat(system, user, max_tokens=60, temperature=1.1, timeout=6.0)


# ─── AI 版意图解析（使用 LLM 替代规则 NLU） ───────────────────────────────

# 高德 POI 类型码映射表
AMAP_CATEGORY_CODES = {
    "公园": "110100|110101|110102|110103",
    "咖啡": "050118|050000",
    "书店": "060100|080703",
    "博物馆": "080300|080301|080302",
    "餐厅": "050000",
    "商场": "060200|060201",
    "户外": "110100|110200",
    "健身": "090301|090302",
    "酒吧": "050100",
    "电影院": "120000",
    "KTV": "050200",
    "美发": "070200",
}

TRANSPORT_MODES = {
    "步行": "walk",
    "骑车": "bike",
    "电动车": "ebike",
    "地铁": "subway",
    "驾车": "car",
}

TRANSPORT_DEFAULT_RADIUS = {
    "walk": 1500,
    "bike": 4000,
    "ebike": 6000,
    "subway": 8000,
    "car": 12000,
}


async def parse_intent_with_ai(
    prompt: str,
    location: str | None = None,
    time_context: dict | None = None,
) -> dict:
    """
    使用 LLM 解析用户自然语言 prompt 为结构化搜索意图。支持时间上下文和多类型偏好。

    返回结构：
    {
        "radius_m": int,
        "poi_types": str,               # 高德类型码，"|" 分隔（多类型合并）
        "keywords": str,                # 补充关键词搜索
        "transport": str,               # walk/bike/subway/car/ebike
        "budget_max": int | None,       # None = 不限
        "open_now": bool,
        "preferred_category": str,      # 主要意图类别（用于评分加权）
        "type_weights": dict,           # {类别名: 权重} 供评分器使用
        "llm_used": bool,
    }

    失败时抛异常，让调用方决定降级策略。
    """
    category_help = "\n".join([f"  - {k}" for k in AMAP_CATEGORY_CODES])

    # 构建时间上下文注入
    time_hint = ""
    if time_context:
        hour = time_context.get("hour")
        weekday = time_context.get("weekday", "")
        season = time_context.get("season", "")
        weather = time_context.get("weather", "")
        parts = []
        if weekday:
            parts.append(weekday)
        if hour is not None:
            if hour < 6:
                parts.append("深夜")
            elif hour < 11:
                parts.append("上午")
            elif hour < 14:
                parts.append("午间")
            elif hour < 18:
                parts.append("下午")
            elif hour < 21:
                parts.append("傍晚")
            else:
                parts.append("晚上")
        if season:
            parts.append(f"{season}季")
        if weather:
            parts.append(weather)
        if parts:
            time_hint = f"\n【当前时间】{' '.join(parts)}。请根据此时间偏好选择合适的室内外场景。"

    system = (
        "你是地点搜索引擎的自然语言理解模块。\n"
        "用户会用口语描述今天想去的地点类型、通勤方式、预算等需求。\n"
        "你的任务是把这个需求结构化，返回 JSON。\n"
        f"{time_hint}\n"
        "【可用地点类型】\n"
        f"{category_help}\n\n"
        "【多类型规则】\n"
        "用户意图模糊时（如「放松」「随便逛逛」「有氛围感的地方」），可选 1-3 个类型，\n"
        "用 weight（0.1-1.0）表示偏好强度，主意图 weight=1.0，次选降权。\n"
        "意图明确时（如「找奶茶」「去公园」），只选1个类型 weight=1.0。\n\n"
        "【通勤方式】步行/骑车/电动车/地铁/驾车，未提及默认骑车。\n\n"
        "【预算】「免费」→0，「20块」→20，未提及→null。\n\n"
        "【关键词】特定品牌/口味写在 keywords（如「奶茶|喜茶」），通用心情词不写。\n\n"
        "返回 JSON（不加代码块，不加其他文字）：\n"
        '{"categories":[{"name":"类型名","weight":1.0}],'
        '"transport":"通勤方式","time_min":分钟数或null,'
        '"keywords":"品牌|口味","budget":数字或null}'
    )

    user = f"用户说：「{prompt}」"
    if location:
        user += f"\n当前位置：{location}"

    raw = await _chat(system, user, max_tokens=250, temperature=0.3, timeout=7.0)
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"parse_intent_with_ai JSON 解析失败: {e}") from e

    # 解析多类型 categories（兼容旧格式单 category）
    categories_raw = data.get("categories", [])
    if not categories_raw and data.get("category"):
        categories_raw = [{"name": data["category"], "weight": 1.0}]
    if not categories_raw:
        raise ValueError("LLM 未返回任何 categories，降级到规则 NLU")

    # 合并 poi_types 并建立 type_weights
    seen_codes: set[str] = set()
    all_codes: list[str] = []
    type_weights: dict[str, float] = {}
    preferred_category = ""

    for entry in categories_raw:
        name = str(entry.get("name", "")).strip()
        weight = float(entry.get("weight", 1.0))
        codes = AMAP_CATEGORY_CODES.get(name, "")
        if codes:
            for code in codes.split("|"):
                code = code.strip()
                if code and code not in seen_codes:
                    seen_codes.add(code)
                    all_codes.append(code)
        if name:
            type_weights[name] = weight
            if not preferred_category or weight > type_weights.get(preferred_category, 0):
                preferred_category = name

    poi_types = "|".join(all_codes) if all_codes else "110100|050118|060100|080300"

    # 通勤方式
    transport = str(data.get("transport", "骑车")).strip()
    transport_key = TRANSPORT_MODES.get(transport, "bike")

    # 搜索半径
    time_min = data.get("time_min")
    radius_m = TRANSPORT_DEFAULT_RADIUS[transport_key]
    if time_min and isinstance(time_min, (int, float)) and time_min > 0:
        transport_speed = {"walk": 83, "bike": 250, "ebike": 350, "subway": 500, "car": 600}
        speed = transport_speed.get(transport_key, 250)
        radius_m = min(int(time_min * speed), 15000)

    # 预算
    budget = data.get("budget")
    budget_max = None
    if budget is not None:
        try:
            budget_max = int(budget)
        except (TypeError, ValueError):
            budget_max = None

    keywords = str(data.get("keywords", "")).strip()

    return {
        "radius_m":           radius_m,
        "poi_types":          poi_types,
        "keywords":           keywords,
        "transport":          transport_key,
        "budget_max":         budget_max,
        "open_now":           True,
        "preferred_category": preferred_category,
        "type_weights":       type_weights,
        "must_keywords":      [k.strip() for k in keywords.split("|") if k.strip()],
        "exclude_keywords":   [],
        "llm_used":           True,
    }


async def generate_search_summary(
    *,
    prompt: str,
    type_labels: list[str],
    count: int,
    time_context: dict | None = None,
) -> str:
    """
    根据用户 prompt 和搜索结果，生成一句自然语言摘要，用于候选页面标题。
    ≤25字，有温度，不模板化。失败时由调用方使用兜底文案。
    """
    time_hint = ""
    if time_context:
        hour = time_context.get("hour")
        weekday = time_context.get("weekday", "")
        parts = [weekday] if weekday else []
        if hour is not None:
            if hour < 11:
                parts.append("上午")
            elif hour < 14:
                parts.append("午间")
            elif hour < 18:
                parts.append("下午")
            elif hour < 21:
                parts.append("傍晚")
            else:
                parts.append("晚上")
        time_hint = "".join(parts)

    type_str = "、".join(type_labels[:3]) if type_labels else "附近地点"
    system = (
        "你是一个简短的搜索摘要生成器。\n"
        "根据用户原始诉求和找到的结果，写一句话（≤25字）摘要，像一个知心朋友在说话。\n"
        "不要用「已为你」「推荐」「搜索完成」等机器感的词。\n"
        "只输出这一句话，不加标点结尾。"
    )
    user = (
        f"用户说：「{prompt}」\n"
        f"找到了 {count} 个{type_str}"
        + (f"，时间：{time_hint}" if time_hint else "")
    )
    return await _chat(system, user, max_tokens=60, temperature=0.8, timeout=5.0)
