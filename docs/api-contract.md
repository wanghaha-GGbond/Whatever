# API Contract (MVP v1)

> 原则：闭环优先、契约先行、风险前置。
> Base URL: `/api/v1`
> Auth: MVP 阶段支持匿名会话（`X-Session-Id`），登录后可绑定 `user_id`。

## 通用约定

- Content-Type: `application/json`
- Trace: `X-Request-Id`（可选，调用方透传）
- 时间格式: ISO-8601 (`2026-03-15T13:00:00+08:00`)
- 坐标: GCJ-02（高德）

### 通用错误码

| code | 含义 | 建议处理 |
|---|---|---|
| `OK` | 成功 | 正常渲染 |
| `INVALID_PARAMS` | 参数校验失败 | 前端提示并保留输入 |
| `LOCATION_REQUIRED` | 缺少定位 | 引导开启定位 |
| `UPSTREAM_TIMEOUT` | 外部服务超时 | 走降级结果 |
| `UPSTREAM_UNAVAILABLE` | 外部服务不可用 | 走模板结果 |
| `NO_CANDIDATE` | 无候选 | 放宽条件再试 |
| `INTERNAL_ERROR` | 服务内部错误 | 通用兜底 + 重试 |

---

## 1) POST `/recommend/init`

创建一次推荐会话，落盘用户请求上下文。

### request

```json
{
  "user_id": "optional-user-id",
  "prompt": "骑车20分钟内，预算50，适合一个人安静待会",
  "location": { "lng": 121.397, "lat": 31.217, "accuracy_m": 30 },
  "scene": "独处",
  "transport": "骑车",
  "budget_range": { "min": 0, "max": 50 },
  "atmosphere": ["安静"],
  "city_code": "310000"
}
```

### response

```json
{
  "code": "OK",
  "message": "ok",
  "data": {
    "session_id": "rec_s_20260315_xxx",
    "normalized_intent": {
      "radius_m": 4000,
      "categories": ["park", "cafe", "bookstore"],
      "constraints": {
        "open_now": true,
        "budget_max": 50,
        "transport": "bike"
      }
    },
    "fallback_used": false
  }
}
```

---

## 2) POST `/recommend/candidates`

基于 `session_id` 返回 Top5 候选。

### request

```json
{
  "session_id": "rec_s_20260315_xxx",
  "limit": 5
}
```

### response

```json
{
  "code": "OK",
  "data": {
    "session_id": "rec_s_20260315_xxx",
    "summary": "已排除超预算、过远、当前不适合的地点，保留 5 个候选",
    "candidates": [
      {
        "candidate_id": "cand_1",
        "poi_id": "amap_xxx",
        "name": "新泾公园",
        "type": "公园",
        "distance_m": 2300,
        "eta_min": 12,
        "budget_text": "¥0",
        "score": 0.82,
        "ai_judgement": "现在去比较轻松，适合一个人待一会",
        "risk_label": "傍晚人会变多"
      }
    ],
    "fallback_used": false
  }
}
```

### fallback 字段说明
- `fallback_used=true`：说明走了降级（规则模板或缓存候选）。
- `summary` 文案要明确告知是否放宽条件。

---

## 3) POST `/recommend/pick`

在当前候选池内执行“约束随机”，返回最终地点。

### request

```json
{
  "session_id": "rec_s_20260315_xxx",
  "strategy": "weighted_random",
  "temperature": 0.7
}
```

### response

```json
{
  "code": "OK",
  "data": {
    "session_id": "rec_s_20260315_xxx",
    "pick_id": "pick_20260315_xxx",
    "picked": {
      "candidate_id": "cand_1",
      "name": "新泾公园",
      "type": "公园",
      "eta_min": 12,
      "budget_text": "¥0",
      "reason": "离你近，安静，现在去负担最低"
    },
    "alternatives": ["cand_2", "cand_3"],
    "fallback_used": false
  }
}
```

---

## 4) POST `/persona/review`

基于最终地点和人格，生成试玩文案（结构化输出）。

### request

```json
{
  "session_id": "rec_s_20260315_xxx",
  "pick_id": "pick_20260315_xxx",
  "persona": "独处型"
}
```

### response

```json
{
  "code": "OK",
  "data": {
    "persona": "独处型",
    "review": "这里不会逼你社交，适合一个人慢慢待着。",
    "risk": "傍晚可能没有你想的那么空。",
    "conclusion": "我会去。",
    "fallback_used": false
  }
}
```

---

## 5) POST `/feedback/submit`

提交是否到店、满意度、真实花费，用于偏好更新。

### request

```json
{
  "session_id": "rec_s_20260315_xxx",
  "pick_id": "pick_20260315_xxx",
  "went": true,
  "satisfaction": 4,
  "actual_cost": 18,
  "transport_used": "bike",
  "tags": ["安静", "值得再去"],
  "note": "人不多，体验不错"
}
```

### response

```json
{
  "code": "OK",
  "data": {
    "feedback_id": "fb_20260315_xxx",
    "profile_updated": true
  }
}
```

---

## 6) GET `/history/list`

获取历史记录（分页）。

### request(query)

- `user_id`（可选）
- `session_id`（可选，匿名态用）
- `page` 默认 `1`
- `page_size` 默认 `20` 最大 `50`

### response

```json
{
  "code": "OK",
  "data": {
    "list": [
      {
        "pick_id": "pick_20260315_xxx",
        "name": "新泾公园",
        "timestamp": "2026-03-15T13:30:00+08:00",
        "conditions": "骑车20分钟内，预算50，安静",
        "satisfaction": 4
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 1
  }
}
```
