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
    content = skill_path.read_text(encoding="utf-8")
    # Strip YAML frontmatter (--- ... ---)
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            content = content[end + 4:].lstrip("\n")
    return content


async def _chat(system: str, user: str, max_tokens: int = 200, temperature: float = 0.9) -> str:
    if not _API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY 未配置")
    async with httpx.AsyncClient(timeout=_TIMEOUT, trust_env=False) as client:
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
    return resp.json()["choices"][0]["message"]["content"].strip()


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
    raw = await _chat(system, user, max_tokens=500)
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(raw)

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
            "text":    str(s.get("text", "")),
            "emotion": str(s.get("emotion", "")),
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
        f"你正在以自己的视角评价一个目的地，供用户决定今天是否前往。\n"
        f"地点：{poi_name}（{poi_type}），约{eta_min}分钟路程，人均{budget}。\n"
        "用你独特的语气、思维方式和判断标准，生成 4 个场景切片评价。\n"
        "每个切片 text ≤30字，emotion ≤6字（情感词）。"
        "summary ≤20字，是你的核心判断句。\n"
        "严格输出 JSON，不加任何其他文字，不加代码块符号：\n"
        '{"summary":"...","slices":['
        '{"scene":"to_door","tag":"到门口","text":"...","emotion":"..."},'
        '{"scene":"enter","tag":"进入后","text":"...","emotion":"..."},'
        '{"scene":"during","tag":"体验中","text":"...","emotion":"..."},'
        '{"scene":"leave","tag":"总结","text":"...","emotion":"..."}'
        ']}'
    )
    raw = await _chat(system, user, max_tokens=600)
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(raw)

    slices = data.get("slices", [])
    summary = str(data.get("summary", ""))

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
            "text":    str(s.get("text", "")),
            "emotion": str(s.get("emotion", "")),
        })

    leave_slice = normalized_slices[3]
    return {
        "summary":    summary,
        "slices":     normalized_slices,
        "review":     summary,
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
    return await _chat(system, user, max_tokens=80, temperature=1.1)


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
    return await _chat(system, user, max_tokens=60, temperature=1.4)
