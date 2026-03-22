import json as _json
import logging
import random
from datetime import datetime
from pathlib import Path
from random import choices
from uuid import uuid4

from fastapi import APIRouter, Request
from pydantic import BaseModel

from .services.intent_parser import (
    parse_intent, eta_min, budget_text, make_judgement, make_risk_label, transport_label,
)
from .services.amap import search_around, get_type_label, nav_url, regeo, geocode
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

def debug_scenario(request: Request) -> str:
    return request.headers.get("X-Debug-Scenario", "").strip()


def _score_poi(poi: dict, intent: dict, type_weights: dict | None = None) -> float:
    w = RANKING_CFG["weights"]
    score = 1.0
    radius = intent.get("radius_m", 4000)
    dist = poi.get("distance", radius)
    score -= w["distance"] * min(dist / radius, 1.0)

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

    if type_weights:
        type_label = get_type_label(poi["type"])
        tw = type_weights.get(type_label, 1.0)
        score *= tw
        if type_label not in type_weights:
            score += w["novelty"]

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

    # Step 1：评分 + 硬过滤
    scored = []
    for poi in pois:
        type_weights = intent.get("type_weights")
        s = _score_poi(poi, intent, type_weights)
        if s > 0:  # 0 = 被硬排除
            scored.append((s, poi))

    if not scored:
        return []

    # Step 2：加随机噪音，让分数相近的 POI 每次结果不同
    noisy = [(s + random.uniform(-RANKING_CFG["noise"]["range"], RANKING_CFG["noise"]["range"]), poi) for s, poi in scored]
    noisy.sort(key=lambda x: x[0], reverse=True)

    # Step 3：类型多样性 — 同类型最多 max_same_type 个
    type_count: dict[str, int] = {}
    pool = []
    for s, poi in noisy:
        type_label = get_type_label(poi["type"])
        if type_count.get(type_label, 0) < RANKING_CFG["diversity"]["max_same_type"]:
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
            "nav_url":      nav_url(poi["name"], poi["location"]),
        })
    return result


# ─── 路由 ───────────────────────────────────────────────────────────────────────

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
    intent = parse_intent(req.prompt)

    # 把用户历史偏好混入 intent
    if req.user_id:
        user_prefs_data = prefs_get(req.user_id)
        if user_prefs_data:
            if intent["budget_max"] is None and user_prefs_data.get("budget_avg"):
                intent["budget_max"] = user_prefs_data["budget_avg"]
            if user_prefs_data.get("type_weights"):
                intent["type_weights"] = user_prefs_data["type_weights"]

    # 位置解析：坐标直接用；文字地址先 geocode；无位置用默认
    raw_loc = req.location or ""
    if raw_loc and "," not in raw_loc:
        # 用户手动输入的文字地址，转成坐标
        try:
            geocoded = await geocode(raw_loc)
            location = geocoded or DEFAULT_LOCATION
        except Exception:
            location = DEFAULT_LOCATION
    else:
        location = raw_loc or DEFAULT_LOCATION

    # 逆地理编码：把坐标转成地名，供前端 LocationBar 展示
    address_name = req.location if (raw_loc and "," not in raw_loc) else ""
    try:
        address_name = await regeo(location)
    except Exception:
        pass

    session_set(session_id, {
        "prompt":       req.prompt,
        "intent":       intent,
        "location":     location,
        "address_name": address_name,
        "user_id":      req.user_id,
        "created_at":   datetime.now().isoformat(),
    })
    return {
        "code": "OK",
        "data": {
            "session_id":        session_id,
            "address_name":      address_name,   # 前端 LocationBar 用
            "normalized_intent": intent,
            "fallback_used":     False,
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
        pois = await search_around(
            location=location,
            poi_types=intent["poi_types"],
            keywords=intent.get("keywords", ""),
            radius=intent["radius_m"],
            limit=min(req.limit * 4, 25),
        )
        if not pois:
            raise ValueError("高德返回空结果")
        candidates = _select_candidates(pois, intent, limit=req.limit)
    except Exception as exc:
        logger.warning("高德搜索失败，降级 mock: %s", exc)
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

    session_set_candidates(req.session_id, candidates)

    return {
        "code": "OK",
        "data": {
            "session_id":    req.session_id,
            "summary":       f"已排除超预算、过远、当前不适合的地点，保留 {len(candidates)} 个候选",
            "candidates":    candidates,
            "fallback_used": fallback_used,
        },
    }


class PickReq(BaseModel):
    session_id: str
    strategy: str = "weighted_random"
    temperature: float = 0.7


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
    weights = [c["score"] for c in candidates]
    picked = choices(candidates, weights=weights, k=1)[0]
    picked_transport_mode = picked.get("transport_mode") or transport_label(
        (session.get("intent") or {}).get("transport", "bike")
    )
    pick_id = f"pick_{uuid4().hex[:10]}"
    pick_set(pick_id, req.session_id, picked)

    # LLM 生成推荐理由，失败降级默认文案
    reason = "离你近，现在去负担最低"
    try:
        session_data = session_get(req.session_id) or {}
        reason = await llm.pick_reason(
            poi_name=picked["name"],
            poi_type=picked["type"],
            eta_min=picked["eta_min"],
            budget=picked["budget_text"],
            user_prompt=session_data.get("prompt", ""),
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
            },
            "alternatives": [c["candidate_id"] for c in candidates if c != picked][:2],
            "fallback_used": False,
        },
    }


class PersonaReq(BaseModel):
    session_id: str
    pick_id: str
    persona: str


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
        result = await llm.persona_review(
            poi_name=picked["name"],
            poi_type=picked["type"],
            eta_min=picked["eta_min"],
            budget=picked["budget_text"],
            persona=req.persona,
            user_prompt=session_data.get("prompt", ""),
        )
    except Exception as exc:
        logger.warning("LLM persona_review 失败，降级模板: %s", exc)
        p = PERSONA.get(req.persona, PERSONA["独处型"])
        result = {"review": p["review"], "risk": p["risk"], "conclusion": p["conclusion"]}
        fallback_used = True

    return {
        "code": "OK",
        "data": {
            "persona":    req.persona,
            **result,
            "fallback_used": fallback_used,
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


@router.post("/feedback/submit")
async def feedback_submit(req: FeedbackReq, request: Request):
    scenario = debug_scenario(request)
    if scenario == "feedback_500":
        return {"code": "INTERNAL_ERROR", "message": "feedback failed",
                "data": {"fallback_used": True}}

    feedback_id = f"fb_{uuid4().hex[:10]}"
    pick_data = pick_get(req.pick_id)
    if pick_data:
        picked = pick_data["picked"]
        session = session_get(req.session_id) or {}
        history_insert(
            pick_id=req.pick_id,
            name=picked["name"],
            timestamp=datetime.now().isoformat(),
            conditions=session.get("prompt", ""),
            satisfaction=req.satisfaction,
        )
        if req.user_id:
            intent = session.get("intent", {})
            prefs_update(
                req.user_id,
                transport=intent.get("transport"),
                budget=req.actual_cost or intent.get("budget_max"),
                poi_type=picked.get("type"),
                satisfaction=req.satisfaction,
                persona=req.persona,
            )
    return {"code": "OK", "data": {"feedback_id": feedback_id, "profile_updated": True}}


@router.get("/history/list")
async def history_list(request: Request, page: int = 1, page_size: int = 20):
    scenario = debug_scenario(request)
    if scenario == "history_empty":
        return {"code": "OK", "data": {"list": [], "page": page,
                                        "page_size": page_size, "total": 0}}
    items, total = db_history_list(page, page_size)
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
async def dashboard(days: int = 7):
    return {"code": "OK", "data": dashboard_metrics(days)}
