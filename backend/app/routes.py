import asyncio
import base64
import hashlib
import hmac
import json as _json
import logging
import math
import os
import random
import time
from datetime import datetime
from pathlib import Path
from random import choices
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from .services.intent_parser import (
    parse_intent, eta_min, budget_text, make_judgement, make_risk_label, transport_label, DEFAULT_TYPES,
)
from .services.amap import search_around, get_type_label, nav_url, regeo, geocode, get_weather_from_location, get_static_map
from .services import llm
from .db import (
    init_db,
    session_set, session_get, session_set_candidates,
    pick_set, pick_get,
    history_insert, history_list as db_history_list,
    prefs_get, prefs_update,
    events_insert_batch, dashboard_metrics,
)

logger = logging.getLogger(__name__)
router = APIRouter()

ANON_COOKIE_NAME = "p003_anon_token"
ANON_TOKEN_TTL_SECONDS = 60 * 60 * 24 * 180


def _load_ranking_cfg() -> dict:
    cfg_path = Path(__file__).parent.parent.parent / "configs" / "ranking-config.json"
    try:
        return _json.loads(cfg_path.read_text())
    except Exception:
        logger.warning("ranking-config.json 加载失败，使用默认权重")
        return {
            "weights": {"distance": 0.4, "rating": 0.15, "match": 0.2, "novelty": 0.05, "risk": 0.0},
            "noise": {"range": 0.08},
            "diversity": {"max_same_type": 2, "pool_multiplier": 3},
            "radius": {"max_m": 15000, "fallback_expand": 1.5},
        }

RANKING_CFG = _load_ranking_cfg()

# 启动时建表
init_db()

# 无定位时兜底：上海市中心
DEFAULT_LOCATION = "121.4737,31.2304"

# ─── Mock fallback 数据（高德挂了 / 无 Key 时使用） ────────────────────────────
MOCK_CANDIDATES = [
    {
        "candidate_id": "cand_1", "poi_id": "amap_mock_1",
        "name": "新泾公园", "type": "公园",
        "distance_m": 2300, "eta_min": 12, "budget_text": "¥0",
        "transport_mode": "骑车",
        "score": 0.82, "ai_judgement": "现在去比较轻松，适合一个人待一会",
        "risk_label": "傍晚人会变多", "nav_url": "",
    },
    {
        "candidate_id": "cand_2", "poi_id": "amap_mock_2",
        "name": "社区咖啡店", "type": "咖啡",
        "distance_m": 1900, "eta_min": 10, "budget_text": "¥28",
        "transport_mode": "骑车",
        "score": 0.75, "ai_judgement": "距离近，坐一小时不会有负担",
        "risk_label": "周末3点后可能满座", "nav_url": "",
    },
    {
        "candidate_id": "cand_3", "poi_id": "amap_mock_3",
        "name": "上生新所", "type": "文化空间",
        "distance_m": 2600, "eta_min": 15, "budget_text": "¥0-50",
        "transport_mode": "骑车",
        "score": 0.70, "ai_judgement": "有新鲜感，适合随便逛逛",
        "risk_label": None, "nav_url": "",
    },
    {
        "candidate_id": "cand_4", "poi_id": "amap_mock_4",
        "name": "苏州河畔骑行道", "type": "户外",
        "distance_m": 1700, "eta_min": 8, "budget_text": "¥0",
        "transport_mode": "骑车",
        "score": 0.68, "ai_judgement": "风景好，可以边骑边看，比较放松",
        "risk_label": "下午太阳比较晒", "nav_url": "",
    },
    {
        "candidate_id": "cand_5", "poi_id": "amap_mock_5",
        "name": "天山书局", "type": "书店",
        "distance_m": 2100, "eta_min": 18, "budget_text": "¥0-30",
        "transport_mode": "骑车",
        "score": 0.65, "ai_judgement": "安静，适合一个人翻翻书",
        "risk_label": None, "nav_url": "",
    },
]

PERSONA = {
    # ── 通用人格（周末去哪玩）──
    "独处型": {
        "review": "这里不会逼你社交，适合一个人慢慢待着。",
        "risk": "傍晚可能没有你想的那么空。",
        "conclusion": "我会去。",
    },
    "探索型": {
        "review": "可以发现一些周边没注意过的角落，有点意思。",
        "risk": "可能没有特别惊喜的地方。",
        "conclusion": "值得试试。",
    },
    "务实型": {
        "review": "时间和金钱成本都合理，不会后悔。",
        "risk": "如果下雨就不太方便。",
        "conclusion": "靠谱选择。",
    },
    "审美型": {
        "review": "环境还不错，有一些美的细节可以留意。",
        "risk": "光线不是最佳时段。",
        "conclusion": "可以去看看。",
    },
    # ── 午饭专项人格 ──
    "老饕": {
        "review": "看品类和评分，这家大概率不会让你失望。",
        "risk": "没有真实口碑数据，踩雷概率未知。",
        "conclusion": "值得一试。",
    },
    "效率党": {
        "review": "距离近，出餐应该不慢，午休时间够用。",
        "risk": "高峰期可能排队，建议早点去。",
        "conclusion": "时间上可以。",
    },
    "精算师": {
        "review": "人均在合理范围内，不算坑。",
        "risk": "实际消费可能超出预期，注意隐形消费。",
        "conclusion": "性价比过关。",
    },
    "氛围感": {
        "review": "环境信息有限，但这个品类通常还行。",
        "risk": "实际氛围可能和想象有落差。",
        "conclusion": "可以去感受一下。",
    },
}


# ─── 工具函数 ───────────────────────────────────────────────────────────────────

def _cookie_secure() -> bool:
    app_env = (os.getenv("APP_ENV") or "").strip().lower()
    return app_env in {"production", "prod"}


def _cookie_samesite() -> str:
    # 跨域前端（Vercel）访问后端（Render）时，生产环境需 SameSite=None
    return "none" if _cookie_secure() else "lax"


def _cookie_signing_key() -> str:
    return (os.getenv("COOKIE_SIGNING_KEY") or "local-dev-cookie-signing-key").strip()


def _create_anon_token(user_id: str, expires_at: int) -> str:
    payload = f"{user_id}:{expires_at}"
    sig = hmac.new(
        _cookie_signing_key().encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    raw = f"{payload}:{sig}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8").rstrip("=")


def _parse_anon_token(token: str | None) -> str | None:
    if not token:
        return None
    try:
        padded = token + "=" * (-len(token) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8")
        user_id, exp_raw, sig = raw.split(":", 2)
        payload = f"{user_id}:{exp_raw}"
        expect_sig = hmac.new(
            _cookie_signing_key().encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(sig, expect_sig):
            return None
        if int(exp_raw) <= int(time.time()):
            return None
        return user_id
    except Exception:
        return None


def _resolve_user_id(request: Request, explicit_user_id: str | None = None) -> str | None:
    if explicit_user_id:
        raw = explicit_user_id.strip()
        if raw:
            return raw
    return _parse_anon_token(request.cookies.get(ANON_COOKIE_NAME))


def _assert_admin_token(request: Request) -> None:
    expected = (os.getenv("ADMIN_TOKEN") or "").strip()
    # 本地未配置 ADMIN_TOKEN 时放行，线上建议必须配置
    if not expected:
        return
    provided = (
        request.headers.get("x-admin-token")
        or request.headers.get("X-Admin-Token")
        or request.query_params.get("admin_token")
        or ""
    ).strip()
    if provided != expected:
        raise HTTPException(status_code=401, detail="admin token invalid")


def _backend_mock_fallback_enabled() -> bool:
    raw = (os.getenv("BACKEND_ENABLE_MOCK_FALLBACK") or "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    app_env = (os.getenv("APP_ENV") or "").strip().lower()
    return app_env not in {"production", "prod"}


def debug_scenario(request: Request) -> str:
    return request.headers.get("X-Debug-Scenario", "").strip()


def _build_time_context() -> dict:
    """构建当前时间上下文，注入给 LLM 以生成有时间感的命运独白。"""
    now = datetime.now()
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    month = now.month
    if month in (3, 4, 5):
        season = "春"
    elif month in (6, 7, 8):
        season = "夏"
    elif month in (9, 10, 11):
        season = "秋"
    else:
        season = "冬"
    return {
        "weekday": weekdays[now.weekday()],
        "hour": now.hour,
        "season": season,
    }


def _poi_blob(poi: dict) -> str:
    return " ".join(
        [
            str(poi.get("name", "")),
            str(poi.get("type", "")),
            str(poi.get("address", "")),
        ]
    ).lower()


def _poi_matches_keywords(poi: dict, keywords: list[str]) -> bool:
    if not keywords:
        return True
    blob = _poi_blob(poi)
    return any(k.lower() in blob for k in keywords if k)


def _poi_blocked(poi: dict, exclude_keywords: list[str]) -> bool:
    if not exclude_keywords:
        return False
    blob = _poi_blob(poi)
    return any(k.lower() in blob for k in exclude_keywords if k)


def _score_poi(poi: dict, intent: dict, type_weights: dict | None = None) -> float:
    w = RANKING_CFG["weights"]
    score = 1.0
    radius = intent.get("radius_m", 4000)
    dist = poi.get("distance", radius)
    # sqrt 曲线让距离惩罚更平缓，避免半径内远端好地方被线性压死
    score -= w["distance"] * min(math.sqrt(dist / radius), 1.0)

    budget_max = intent.get("budget_max")
    pl = poi.get("price_level", "")
    level_cost = {"0": 0, "1": 20, "2": 50, "3": 120, "4": 200}
    if budget_max is not None and pl in level_cost:
        if level_cost[pl] > budget_max:
            return 0.0

    try:
        score += float(poi.get("rating") or 0) / 10.0 * w["rating"]
    except (ValueError, TypeError):
        pass

    must_keywords = intent.get("must_keywords") or []
    if must_keywords:
        # 显式关键词（奶茶/麦当劳等）命中时加分，不命中时降权，减少跑偏候选
        if _poi_matches_keywords(poi, must_keywords):
            score += 0.22
        else:
            score -= 0.18

    if type_weights:
        type_label = get_type_label(poi["type"])
        # exact match first; fall back to partial (e.g. "咖啡" matches "咖啡厅")
        tw = type_weights.get(type_label)
        if tw is None:
            tw = next((v for k, v in type_weights.items() if k in type_label or type_label in k), None)
        if tw is not None:
            score *= tw
        else:
            score += w["novelty"]

    # 主意图偏好加分（来自 LLM 解析的首选类型）
    preferred_cat = intent.get("preferred_category", "")
    if preferred_cat:
        tl = get_type_label(poi["type"])
        if preferred_cat in tl or tl in preferred_cat:
            score += 0.07

    return round(max(0.05, min(score, 1.0)), 4)


def _select_candidates(pois: list[dict], intent: dict, limit: int = 5) -> list[dict]:
    """
    筛选逻辑（替代纯 Top-N 打分）：
    1. 硬过滤：排除超预算 POI
    2. 打分 + 加噪：相近分数的 POI 会有随机扰动，避免每次都一样
    3. 类型去重：相同类型最多选 2 个，保证候选多样性
    4. 从"合格池"里按权重抽取，而不是死板取 Top-N
    """
    transport = intent.get("transport", "bike")
    transport_mode = transport_label(transport)
    budget_max = intent.get("budget_max")
    must_keywords = intent.get("must_keywords") or []
    exclude_keywords = intent.get("exclude_keywords") or []

    # Step 1：评分 + 硬过滤 + 干扰词剔除
    scored = []
    for poi in pois:
        if _poi_blocked(poi, exclude_keywords):
            continue
        type_weights = intent.get("type_weights")
        s = _score_poi(poi, intent, type_weights)
        if s > 0:  # 0 = 被硬排除
            scored.append((s, poi))

    if not scored:
        return []

    # Step 2：加随机噪音，让分数相近的 POI 每次结果不同
    noisy = [(s + random.uniform(-RANKING_CFG["noise"]["range"], RANKING_CFG["noise"]["range"]), poi) for s, poi in scored]
    noisy.sort(key=lambda x: x[0], reverse=True)

    # Step 3：类型多样性（动态）
    # 之前固定 max_same_type=2 会导致「奶茶/快餐」这类单类型场景最多只出 2~5 个候选。
    # 这里按"类型数 + 目标数量"动态放宽，保证能尽量凑满 limit。
    unique_types = {get_type_label(p["type"]) for _, p in noisy}
    base_max_same_type = int(RANKING_CFG["diversity"]["max_same_type"])
    dynamic_max_same_type = max(base_max_same_type, math.ceil(limit / max(1, len(unique_types))))

    # Step 3：类型多样性 — 同类型最多 dynamic_max_same_type 个
    type_count: dict[str, int] = {}
    pool = []
    for s, poi in noisy:
        type_label = get_type_label(poi["type"])
        if type_count.get(type_label, 0) < dynamic_max_same_type:
            type_count[type_label] = type_count.get(type_label, 0) + 1
            pool.append((s, poi))
        if len(pool) >= limit * RANKING_CFG["diversity"]["pool_multiplier"]:  # 候选池够大就停
            break

    if not pool:
        return []

    # Step 4：按权重抽取（分高的概率大，但不是必然）
    weights = [max(s, 0.01) for s, _ in pool]
    k = min(limit, len(pool))
    picked_items = random.choices(pool, weights=weights, k=k * 3)  # 多抽再去重
    seen_ids: set[str] = set()
    selected = []
    for s, poi in picked_items:
        if poi["id"] not in seen_ids:
            seen_ids.add(poi["id"])
            selected.append((s, poi))
        if len(selected) >= k:
            break

    # 若随机去重后数量不足，按分数从高到低补齐，尽量满足 limit
    if len(selected) < k:
        for s, poi in pool:
            if poi["id"] in seen_ids:
                continue
            seen_ids.add(poi["id"])
            selected.append((s, poi))
            if len(selected) >= k:
                break

    # Step 5：转换为 candidate 格式
    result = []
    for i, (s, poi) in enumerate(selected):
        type_label = get_type_label(poi["type"])
        result.append({
            "candidate_id": f"cand_{i + 1}",
            "poi_id":       poi["id"],
            "name":         poi["name"],
            "type":         type_label,
            "distance_m":   poi["distance"],
            "eta_min":      eta_min(poi["distance"], transport),
            "transport_mode": transport_mode,
            "budget_text":  budget_text(poi["price_level"], budget_max),
            "score":        round(max(0.05, min(s, 1.0)), 4),
            "ai_judgement": make_judgement(type_label),
            "risk_label":   make_risk_label(type_label),
            "poi_location": poi.get("location", ""),
            "nav_url":      nav_url(poi["name"], poi["location"]),
        })
    # Wild Card：随机将一个非首位候选标记为「意外之选」，LLM 会用惊喜叙事角度处理它
    if len(result) >= 2:
        wild_idx = random.randint(1, len(result) - 1)
        result[wild_idx]["wild_card"] = True

    return result


def _pick_with_temperature(candidates: list[dict], temperature: float) -> dict:
    """
    temperature 越高随机性越强；越低越偏向高分项。
    """
    safe_temp = max(0.25, min(2.5, temperature))
    power = 1.0 / safe_temp
    weights = []
    for c in candidates:
        s = float(c.get("score", 0.1))
        s = max(0.01, s)
        # 在 log 空间收敛，避免权重差异过大导致随机性不足
        adjusted = math.exp(math.log(s) * power)
        weights.append(max(0.001, adjusted))
    return choices(candidates, weights=weights, k=1)[0]


async def _enrich_ai_judgements(
    candidates: list[dict], user_prompt: str, context: dict | None = None
) -> None:
    """
    用 LLM 生成候选卡片的命运独白。
    失败时保持原有模板文案，不抛异常。
    """
    if not candidates:
        return

    tasks = [
        llm.pick_reason(
            poi_name=c["name"],
            poi_type=c["type"],
            eta_min=c["eta_min"],
            budget=c["budget_text"],
            user_prompt=user_prompt,
            context={**(context or {}), "is_wild_card": c.get("wild_card", False)},
        )
        for c in candidates
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for c, r in zip(candidates, results):
        if isinstance(r, Exception):
            continue
        text = str(r).strip()
        if text:
            c["ai_judgement"] = text


# ─── 路由 ───────────────────────────────────────────────────────────────────────

class AnonymousAuthReq(BaseModel):
    user_id: str | None = None


@router.post("/auth/anonymous")
async def auth_anonymous(request: Request, response: Response, req: AnonymousAuthReq | None = None):
    # 优先复用已存在 cookie，避免同一用户每次刷新都换身份
    existing_user_id = _resolve_user_id(request)
    if existing_user_id:
        return {"code": "OK", "data": {"user_id": existing_user_id, "is_new": False}}

    requested_user_id = (req.user_id or "").strip() if req else ""
    user_id = requested_user_id or f"anon_{uuid4().hex[:12]}"
    expires_at = int(time.time()) + ANON_TOKEN_TTL_SECONDS
    token = _create_anon_token(user_id, expires_at)
    response.set_cookie(
        key=ANON_COOKIE_NAME,
        value=token,
        max_age=ANON_TOKEN_TTL_SECONDS,
        httponly=True,
        secure=_cookie_secure(),
        samesite=_cookie_samesite(),
        path="/",
    )
    return {
        "code": "OK",
        "data": {
            "user_id": user_id,
            "is_new": True,
            "expires_at": datetime.fromtimestamp(expires_at).isoformat(),
        },
    }


class InitReq(BaseModel):
    user_id: str | None = None
    prompt: str
    city_code: str | None = None
    location: str | None = None   # "lng,lat"，由前端 Geolocation API 提供


class ResolveLocationReq(BaseModel):
    location: str | None = None


@router.post("/location/resolve")
async def location_resolve(req: ResolveLocationReq):
    raw_loc = (req.location or "").strip()
    fallback_used = False
    used_default = False

    if raw_loc and "," not in raw_loc:
        try:
            geocoded = await geocode(raw_loc)
            if geocoded:
                location = geocoded
            else:
                location = DEFAULT_LOCATION
                fallback_used = True
                used_default = True
        except Exception:
            location = DEFAULT_LOCATION
            fallback_used = True
            used_default = True
    else:
        location = raw_loc or DEFAULT_LOCATION
        if not raw_loc:
            fallback_used = True
            used_default = True

    address_name = raw_loc if (raw_loc and "," not in raw_loc) else ""
    try:
        resolved_name = await regeo(location)
        if resolved_name:
            address_name = resolved_name
    except Exception:
        fallback_used = True

    return {
        "code": "OK",
        "data": {
            "location": location,
            "address_name": address_name,
            "fallback_used": fallback_used,
            "used_default": used_default,
        },
    }


@router.post("/recommend/init")
async def recommend_init(req: InitReq, request: Request):
    scenario = debug_scenario(request)
    if scenario == "location_denied":
        return {"code": "LOCATION_REQUIRED", "message": "location denied",
                "data": {"fallback_used": True}}

    session_id = f"rec_s_{uuid4().hex[:10]}"

    # 时间上下文先行构建（纯 CPU，无外部依赖），注入给 LLM 以提升类型选择准确性
    time_context_early = _build_time_context()

    intent_llm_used = False
    intent: dict = {}
    _regeo_done: str | None = None
    _weather_done: dict | None = None

    resolved_user_id = _resolve_user_id(request, req.user_id)

    # 位置解析：坐标直接用；文字地址先 geocode（必须先完成，后续依赖坐标）
    raw_loc = req.location or ""
    if raw_loc and "," not in raw_loc:
        # 文字地址：LLM intent 与 geocode 并发执行（互不依赖）
        try:
            (intent_result, geocode_result) = await asyncio.gather(
                llm.parse_intent_with_ai(req.prompt, req.location, time_context_early),
                geocode(raw_loc),
                return_exceptions=True,
            )
            if isinstance(intent_result, Exception):
                logger.warning("LLM intent 失败，降级规则版本: %s", str(intent_result)[:100])
                intent = parse_intent(req.prompt)
                intent_llm_used = False
            else:
                intent = intent_result
                intent_llm_used = True
            location = (geocode_result if isinstance(geocode_result, str) and geocode_result else None) or DEFAULT_LOCATION
        except Exception:
            intent = parse_intent(req.prompt)
            intent_llm_used = False
            location = DEFAULT_LOCATION
    else:
        location = raw_loc or DEFAULT_LOCATION
        # GPS 坐标：LLM intent / regeo / weather 三者全部并发（都只依赖原始坐标字符串）
        try:
            (intent_result, regeo_result, weather_result) = await asyncio.gather(
                llm.parse_intent_with_ai(req.prompt, req.location, time_context_early),
                regeo(location),
                get_weather_from_location(location),
                return_exceptions=True,
            )
            if isinstance(intent_result, Exception):
                logger.warning("LLM intent 失败，降级规则版本: %s", str(intent_result)[:100])
                intent = parse_intent(req.prompt)
                intent_llm_used = False
            else:
                intent = intent_result
                intent_llm_used = True
            # regeo / weather 结果暂存，跳过下方的串行调用
            _regeo_done = regeo_result if isinstance(regeo_result, str) else None
            _weather_done = weather_result if isinstance(weather_result, dict) else None
        except Exception:
            intent = parse_intent(req.prompt)
            intent_llm_used = False
            _regeo_done = None
            _weather_done = None

    # 把用户历史偏好混入 intent
    if resolved_user_id:
        user_prefs_data = prefs_get(resolved_user_id)
        if user_prefs_data:
            if intent["budget_max"] is None and user_prefs_data.get("budget_avg"):
                intent["budget_max"] = user_prefs_data["budget_avg"]
            if user_prefs_data.get("type_weights"):
                intent["type_weights"] = user_prefs_data["type_weights"]

    # 逆地理编码 + 天气：GPS 路径已并发完成，文字路径在这里补做
    address_name = req.location if (raw_loc and "," not in raw_loc) else ""
    session_context = time_context_early.copy()

    if raw_loc and "," not in raw_loc:
        # 文字地址路径：geocode 已完成，还需 regeo + weather（并发）
        try:
            (regeo_result, weather_result) = await asyncio.gather(
                regeo(location),
                get_weather_from_location(location),
                return_exceptions=True,
            )
            if isinstance(regeo_result, str) and regeo_result:
                address_name = regeo_result
            if isinstance(weather_result, dict):
                session_context.update(weather_result)
        except Exception:
            pass
    else:
        # GPS 路径：直接使用已并发完成的结果
        if _regeo_done:
            address_name = _regeo_done
        if _weather_done:
            session_context.update(_weather_done)

    session_set(session_id, {
        "prompt":       req.prompt,
        "intent":       intent,
        "location":     location,
        "address_name": address_name,
        "user_id":      resolved_user_id,
        "context":      session_context,
        "intent_llm_used": intent_llm_used,
        "created_at":   datetime.now().isoformat(),
    })
    return {
        "code": "OK",
        "data": {
            "session_id":        session_id,
            "user_id":           resolved_user_id,
            "address_name":      address_name,   # 前端 LocationBar 用
            "normalized_intent": intent,
            "fallback_used":     False,
            "intent_llm_used":   intent_llm_used,
        },
    }


class CandidateReq(BaseModel):
    session_id: str
    limit: int = 10


@router.post("/recommend/candidates")
async def recommend_candidates(req: CandidateReq, request: Request):
    scenario = debug_scenario(request)
    session = session_get(req.session_id)

    if not session:
        return {"code": "INVALID_PARAMS", "message": "invalid session_id",
                "data": {"candidates": [], "summary": "会话已过期", "fallback_used": True}}

    if scenario == "empty_candidates":
        return {"code": "NO_CANDIDATE", "data": {
            "session_id": req.session_id,
            "summary": "附近没找到合适地点，已建议放宽条件",
            "candidates": [], "fallback_used": True,
        }}

    intent   = session["intent"]
    location = session["location"]
    fallback_used = False

    try:
        poi_types  = intent["poi_types"]
        keywords   = intent.get("keywords", "")
        radius     = intent["radius_m"]
        fetch_limit = min(req.limit * 4, 25)
        effective_types = poi_types  # 跟踪降级后实际使用的类型，供补齐时复用

        pois = await search_around(
            location=location, poi_types=poi_types,
            keywords=keywords, radius=radius, limit=fetch_limit,
        )

        # 降级重试 1：去掉 keywords，有时品牌词过滤导致空结果
        if not pois and keywords:
            logger.info("首次查询空结果，去掉 keywords 重试")
            pois = await search_around(
                location=location, poi_types=poi_types,
                keywords="", radius=radius, limit=fetch_limit,
            )

        # 降级重试 2：扩大半径（最大 15km）
        if not pois:
            wider = min(15000, max(int(radius * 2.5), 5000))
            logger.info("仍为空，扩圈至 %dm 重试", wider)
            pois = await search_around(
                location=location, poi_types=poi_types,
                keywords="", radius=wider, limit=fetch_limit,
            )

        # 降级重试 3：换默认综合类型 + 扩圈
        if not pois and poi_types != DEFAULT_TYPES:
            wider = min(15000, max(int(radius * 2.5), 5000))
            logger.info("仍为空，改用默认类型 + %dm 重试", wider)
            effective_types = DEFAULT_TYPES  # 记录实际生效的类型
            pois = await search_around(
                location=location, poi_types=effective_types,
                keywords="", radius=wider, limit=fetch_limit,
            )

        if not pois:
            raise ValueError("高德返回空结果（三次降级均无结果）")
        candidates = _select_candidates(pois, intent, limit=req.limit)

        # 不足 10 个时，自动扩圈补齐（先同类型扩圈，再用默认综合类型补充）
        if len(candidates) < req.limit:
            expanded_radius = min(15000, max(int(intent["radius_m"] * 2), 6000))
            merged_pois = {p.get("id"): p for p in pois if p.get("id")}

            try:
                extra_same_type = await search_around(
                    location=location,
                    poi_types=effective_types,
                    keywords="",
                    radius=expanded_radius,
                    limit=25,
                )
                for p in extra_same_type:
                    pid = p.get("id")
                    if pid and pid not in merged_pois:
                        merged_pois[pid] = p
            except Exception as exc:
                logger.warning("同类型扩圈补齐失败: %s", exc)

            if len(merged_pois) < req.limit and effective_types != DEFAULT_TYPES:
                try:
                    extra_default = await search_around(
                        location=location,
                        poi_types=DEFAULT_TYPES,
                        keywords="",
                        radius=expanded_radius,
                        limit=25,
                    )
                    for p in extra_default:
                        pid = p.get("id")
                        if pid and pid not in merged_pois:
                            merged_pois[pid] = p
                except Exception as exc:
                    logger.warning("默认类型补齐失败: %s", exc)

            if merged_pois:
                candidates = _select_candidates(list(merged_pois.values()), intent, limit=req.limit)
    except Exception as exc:
        logger.warning("高德搜索失败: %r", exc)
        if not _backend_mock_fallback_enabled():
            return {
                "code": "UPSTREAM_ERROR",
                "message": "map service unavailable",
                "data": {
                    "session_id": req.session_id,
                    "summary": "地图服务暂时不可用，请稍后重试",
                    "candidates": [],
                    "fallback_used": False,
                },
            }

        logger.warning("已启用后端 mock 降级")
        fallback_transport = intent.get("transport", "bike")
        fallback_transport_mode = transport_label(fallback_transport)
        candidates = [
            {
                **c,
                "eta_min": eta_min(c.get("distance_m") or 0, fallback_transport),
                "transport_mode": fallback_transport_mode,
            }
            for c in MOCK_CANDIDATES[:req.limit]
        ]
        fallback_used = True

    # 并发：候选卡片 AI 理由 + 搜索结果摘要
    default_summary = (
        f"已为你找到「{'、'.join((intent.get('must_keywords') or [])[:2])}」相关的 {len(candidates)} 个去处"
        if intent.get("must_keywords")
        else f"命运已为你备好 {len(candidates)} 个候选，其中藏着一个意外之选"
    )
    ai_summary = default_summary
    try:
        type_labels = list(dict.fromkeys(c["type"] for c in candidates if c.get("type")))
        enrich_task = _enrich_ai_judgements(
            candidates, session.get("prompt", ""), session.get("context")
        )
        summary_task = asyncio.wait_for(
            llm.generate_search_summary(
                prompt=session.get("prompt", ""),
                type_labels=type_labels[:3],
                count=len(candidates),
                time_context=session.get("context"),
            ),
            timeout=4.0,
        )
        enrich_result, ai_summary_result = await asyncio.gather(
            enrich_task, summary_task, return_exceptions=True
        )
        if isinstance(enrich_result, Exception):
            logger.warning("候选 ai_judgement 生成失败，使用模板: %s", enrich_result)
        if isinstance(ai_summary_result, str) and ai_summary_result.strip():
            ai_summary = ai_summary_result.strip()
        elif isinstance(ai_summary_result, Exception):
            logger.warning("AI 摘要生成失败: %s", ai_summary_result)
    except Exception as exc:
        logger.warning("候选 enrichment 失败，使用模板: %s", exc)
        try:
            await _enrich_ai_judgements(candidates, session.get("prompt", ""), session.get("context"))
        except Exception:
            pass

    session_set_candidates(req.session_id, candidates)

    return {
        "code": "OK",
        "data": {
            "session_id":    req.session_id,
            "summary":       ai_summary,
            "candidates":    candidates,
            "fallback_used": fallback_used,
        },
    }


class PickReq(BaseModel):
    session_id: str
    strategy: str = "weighted_random"
    temperature: float = 1.2


@router.post("/recommend/pick")
async def recommend_pick(req: PickReq, request: Request):
    scenario = debug_scenario(request)
    session = session_get(req.session_id)

    if not session:
        return {"code": "INVALID_PARAMS", "message": "invalid session_id",
                "data": {"fallback_used": True}}

    if scenario == "pick_error":
        return {"code": "INTERNAL_ERROR", "message": "pick failed",
                "data": {"fallback_used": True}}

    candidates = session.get("candidates") or MOCK_CANDIDATES
    picked = _pick_with_temperature(candidates, req.temperature)
    picked_transport_mode = picked.get("transport_mode") or transport_label(
        (session.get("intent") or {}).get("transport", "bike")
    )
    pick_id = f"pick_{uuid4().hex[:10]}"
    pick_set(pick_id, req.session_id, picked)

    # LLM 生成推荐理由（命运独白），失败降级默认文案
    reason = "就是今天，就是这里"
    try:
        session_data = session_get(req.session_id) or {}
        reason = await llm.pick_reason(
            poi_name=picked["name"],
            poi_type=picked["type"],
            eta_min=picked["eta_min"],
            budget=picked["budget_text"],
            user_prompt=session_data.get("prompt", ""),
            context=session_data.get("context"),
        )
    except Exception as exc:
        logger.warning("LLM pick_reason 失败，使用默认文案: %s", exc)

    return {
        "code": "OK",
        "data": {
            "session_id": req.session_id,
            "pick_id":    pick_id,
            "picked": {
                "candidate_id": picked["candidate_id"],
                "name":         picked["name"],
                "type":         picked["type"],
                "distance_m":   picked.get("distance_m"),
                "eta_min":      picked["eta_min"],
                "transport_mode": picked_transport_mode,
                "budget_text":  picked["budget_text"],
                "reason":       reason,
                "nav_url":      picked.get("nav_url", ""),
                "location":     picked.get("poi_location", ""),
            },
            "alternatives": [c["candidate_id"] for c in candidates if c != picked][:2],
            "fallback_used": False,
        },
    }


@router.get("/inspire")
async def inspire():
    """
    随机生成一条用户出门心情描述，供首页「AI 帮我想一个」按钮使用。
    高 temperature LLM 生成，失败时返回随机内置模板。
    """
    fallback_prompts = [
        "骑车20分钟内，找个安静能坐一下午的地方",
        "下班了不想回家，想去个有点意思的地方待会",
        "约了朋友出来，不知道去哪，预算不高",
        "想找个有水或者有树的地方，安静走走",
        "今天突然想去没去过的地方随便逛逛",
        "一个人，步行能到，不要太吵的地方就行",
        "骑车半小时内，有点新鲜感，最好不用花钱",
        "驾车去个稍微远点的地方，喘口气",
    ]
    try:
        text = await llm.generate_inspire()
        return {"code": "OK", "data": {"prompt": text.strip()}}
    except Exception:
        return {"code": "OK", "data": {"prompt": random.choice(fallback_prompts)}}


@router.get("/map/preview")
async def map_preview(session_id: str, pick_id: str):
    """
    代理高德静态地图图片，避免在前端暴露 API Key。
    返回 image/png 字节流。
    """
    from fastapi.responses import Response as FastAPIResponse
    session = session_get(session_id)
    pick_data = pick_get(pick_id)
    if not session or not pick_data:
        raise HTTPException(status_code=404, detail="session or pick not found")

    poi_location = pick_data["picked"].get("poi_location") or pick_data["picked"].get("location", "")
    user_location = session.get("location", "")

    if not poi_location:
        raise HTTPException(status_code=404, detail="poi location not available")

    try:
        image_bytes = await get_static_map(
            poi_location=poi_location,
            user_location=user_location,
        )
    except Exception as exc:
        logger.warning("静态地图获取失败: %s", exc)
        raise HTTPException(status_code=502, detail="map service unavailable")

    return FastAPIResponse(
        content=image_bytes,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=300"},
    )


class PersonaReq(BaseModel):
    session_id: str
    pick_id: str
    persona: str
    celebrity: str | None = None


@router.post("/persona/review")
async def persona_review(req: PersonaReq, request: Request):
    scenario = debug_scenario(request)

    pick_data = pick_get(req.pick_id)
    if not pick_data:
        return {"code": "INVALID_PARAMS", "message": "invalid pick_id",
                "data": {"fallback_used": True}}

    if scenario == "persona_timeout":
        return {"code": "UPSTREAM_TIMEOUT", "data": {
            "persona": req.persona,
            "review": "当前试玩服务较慢，先给你一个保守判断。",
            "risk": "详细人格分析暂不可用。",
            "conclusion": "可以先出发，稍后补充。",
            "fallback_used": True,
        }}

    picked = pick_data["picked"]
    session_data = session_get(req.session_id) or {}

    # LLM 生成人格评价，失败降级模板
    fallback_used = False
    try:
        if req.celebrity:
            result = await llm.celebrity_persona_review(
                poi_name=picked["name"],
                poi_type=picked["type"],
                eta_min=picked["eta_min"],
                budget=picked["budget_text"],
                celebrity_id=req.celebrity,
            )
        else:
            result = await llm.persona_review(
                poi_name=picked["name"],
                poi_type=picked["type"],
                eta_min=picked["eta_min"],
                budget=picked["budget_text"],
                persona=req.persona,
                user_prompt=session_data.get("prompt", ""),
            )
    except Exception as exc:
        logger.warning("LLM persona/celebrity_review 失败，降级模板: %s", exc)
        p = PERSONA.get(req.persona, PERSONA["独处型"])
        result = {"review": p["review"], "risk": p["risk"], "conclusion": p["conclusion"]}
        fallback_used = True

    if fallback_used:
        return {
            "code": "OK",
            "data": {
                "persona":      req.persona,
                "summary":      result.get("review", ""),
                "slices":       [],
                # 向后兼容字段
                "review":       result.get("review", ""),
                "risk":         result.get("risk"),
                "conclusion":   result.get("conclusion", ""),
                "fallback_used": fallback_used,
            },
        }
    return {
        "code": "OK",
        "data": {
            "persona":      req.persona,
            "summary":      result.get("summary", result.get("review", "")),
            "slices":       result.get("slices", []),
            "verdict":      result.get("verdict", ""),
            # 向后兼容字段
            "review":       result.get("review", ""),
            "risk":         result.get("risk"),
            "conclusion":   result.get("conclusion", ""),
            "fallback_used": False,
        },
    }


class FeedbackReq(BaseModel):
    session_id: str
    pick_id: str
    user_id: str | None = None
    went: bool = False
    satisfaction: int = 3
    actual_cost: int | None = None
    persona: str | None = None
    title: str | None = None
    content: str | None = None
    tags: list[str] = Field(default_factory=list)
    transport_used: str | None = None


@router.post("/feedback/submit")
async def feedback_submit(req: FeedbackReq, request: Request):
    scenario = debug_scenario(request)
    if scenario == "feedback_500":
        return {"code": "INTERNAL_ERROR", "message": "feedback failed",
                "data": {"fallback_used": True}}

    feedback_id = f"fb_{uuid4().hex[:10]}"
    pick_data = pick_get(req.pick_id)
    profile_updated = False
    if pick_data:
        picked = pick_data["picked"]
        session = session_get(req.session_id) or {}
        resolved_user_id = _resolve_user_id(request, req.user_id or session.get("user_id"))
        clean_tags = [t.strip() for t in (req.tags or []) if str(t).strip()][:8]
        clean_title = (req.title or "").strip()[:80]
        clean_content = (req.content or "").strip()[:2000]
        satisfaction = max(1, min(5, req.satisfaction))
        history_insert(
            pick_id=req.pick_id,
            name=picked["name"],
            timestamp=datetime.now().isoformat(),
            conditions=session.get("prompt", ""),
            satisfaction=satisfaction,
            user_id=resolved_user_id,
            went=req.went,
            title=clean_title,
            content=clean_content,
            tags=clean_tags,
            actual_cost=req.actual_cost,
            transport_used=req.transport_used,
        )
        if resolved_user_id:
            intent = session.get("intent", {})
            prefs_update(
                resolved_user_id,
                transport=intent.get("transport"),
                budget=req.actual_cost or intent.get("budget_max"),
                poi_type=picked.get("type"),
                satisfaction=satisfaction,
                persona=req.persona,
            )
            profile_updated = True
    return {"code": "OK", "data": {"feedback_id": feedback_id, "profile_updated": profile_updated}}


@router.get("/history/list")
async def history_list(request: Request, page: int = 1, page_size: int = 20, user_id: str | None = None):
    scenario = debug_scenario(request)
    if scenario == "history_empty":
        return {"code": "OK", "data": {"list": [], "page": page,
                                        "page_size": page_size, "total": 0}}
    resolved_user_id = _resolve_user_id(request, user_id)
    if not resolved_user_id:
        return {"code": "OK", "data": {"list": [], "page": page, "page_size": page_size, "total": 0}}
    items, total = db_history_list(page, page_size, user_id=resolved_user_id)
    return {
        "code": "OK",
        "data": {
            "list":      items,
            "page":      page,
            "page_size": page_size,
            "total":     total,
        },
    }


class TrackReq(BaseModel):
    events: list[dict]


@router.post("/events/track")
async def events_track(req: TrackReq):
    try:
        events_insert_batch(req.events)
    except Exception as exc:
        logger.warning("事件写入失败: %s", exc)
    return {"code": "OK"}


@router.get("/dashboard/metrics")
async def dashboard(request: Request, days: int = 7):
    _assert_admin_token(request)
    return {"code": "OK", "data": dashboard_metrics(days)}
