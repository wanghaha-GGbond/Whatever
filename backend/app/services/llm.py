"""
DeepSeek LLM 客户端（OpenAI 兼容格式）。
调用方负责降级：所有函数失败时抛异常，不在这里 catch。
"""
import json
import logging
import os

import httpx

logger = logging.getLogger(__name__)

PERSONA_CHARS = {
    # ── 通用人格（周末去哪玩） ──
    "独处型": "你内向、需要安静空间、厌倦社交压力。最在意：不会被打扰。",
    "探索型": "你好奇、喜欢发现新鲜事物、容忍不确定性。最在意：有没有新鲜感。",
    "务实型": "你效率优先、在意性价比、不喜欢浪费时间和钱。最在意：值不值。",
    "审美型": "你视觉敏感、在意空间设计和环境美感。最在意：好不好看。",
    # ── 午饭专项人格 ──
    "老饕": "你是资深吃货，极度在意口味、食材和烹饪水准，对难吃的东西零容忍。最在意：好不好吃。",
    "效率党": "你午休时间有限，一切以快为准，步数、等餐时间、排队情况都要算清楚。最在意：够不够快。",
    "精算师": "你精打细算，人均、份量、性价比全在脑子里，绝不为溢价买单。最在意：值不值这个钱。",
    "氛围感": "你对环境极度敏感，光线、音乐、座位设计都影响你的心情，吃饭也要有仪式感。最在意：氛围好不好。",
}

_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
_BASE_URL = "https://api.deepseek.com/chat/completions"
_MODEL = "deepseek-chat"
_TIMEOUT = 8.0  # 与 engineering-bootstrap REQUEST_TIMEOUT_MS=8000 对齐


async def _chat(system: str, user: str) -> str:
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
                "max_tokens": 200,
                "temperature": 0.8,
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
    生成人格视角评价。
    返回 {"review": str, "risk": str | None, "conclusion": str}
    """
    char = PERSONA_CHARS.get(persona, "你是一个普通都市白领。")
    system = (
        f"你是一个说话直接、接地气的出行决策助手，正在扮演「{persona}」这类人。{char}"
        "请严格用 JSON 格式回复，只输出 JSON，不要任何额外文字。"
    )
    user = (
        f"用户想要：{user_prompt}\n"
        f"推荐地点：{poi_name}（{poi_type}），{eta_min}分钟到达，花费{budget}。\n"
        f"请以「{persona}」的视角评价，JSON格式：\n"
        '{"review":"一句话评价，不超过25字","risk":"潜在风险不超过15字，无则null","conclusion":"结论不超过10字"}'
    )
    raw = await _chat(system, user)
    # 兼容 LLM 返回 markdown 代码块的情况
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(raw)
    return {
        "review":     str(data.get("review", "")),
        "risk":       data.get("risk") or None,
        "conclusion": str(data.get("conclusion", "")),
    }


async def pick_reason(
    *,
    poi_name: str,
    poi_type: str,
    eta_min: int,
    budget: str,
    user_prompt: str,
) -> str:
    """
    生成抓阄结果的推荐理由（一句话，不超过20字）。
    """
    system = "用一句话（不超过20字）解释为什么推荐这个地方，语气轻松直接。只输出这一句话，不要其他内容。"
    user = (
        f"用户想要：{user_prompt}\n"
        f"推荐：{poi_name}（{poi_type}），{eta_min}分钟，{budget}。"
    )
    return await _chat(system, user)
