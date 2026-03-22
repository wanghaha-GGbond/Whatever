# Orchestrator Flow (MVP v1)

> 目标：保证主链路可跑通，并在外部依赖失败时可降级。

## 状态机

```text
ParseIntent
  -> RetrievePOI
  -> RankCandidates
  -> PickDestination
  -> GeneratePersonaReview
  -> ReturnResult
```

---

## 0) 全局执行策略

- 单次请求总超时：`8s`（不含前端重试）
- 外部依赖超时：地图 `2s`，LLM `3s`
- 重试：仅对幂等读请求重试 1 次（指数退避 200ms）
- 降级优先级：
  1. 缓存结果
  2. 规则模板
  3. 明确失败提示 + 可重试

---

## 1) ParseIntent

### 输入
- `prompt`
- `location`
- 可选标签（scene/transport/budget/atmosphere）

### 输出 schema
```json
{
  "radius_m": 4000,
  "categories": ["park", "cafe"],
  "constraints": {"open_now": true, "budget_max": 50, "transport": "bike"}
}
```

### timeout / retry / fallback
- timeout: `1200ms`
- retry: `0`
- fallback: 使用规则解析（关键词字典）

---

## 2) RetrievePOI

### 输入
- `normalized_intent`
- `location`

### 输出 schema
```json
{
  "pois": [
    {"poi_id":"amap_xxx","name":"新泾公园","category":"park","distance_m":2300,"eta_min":12,"price_level":"0","open_now":true}
  ]
}
```

### timeout / retry / fallback
- timeout: `2000ms`
- retry: `1`
- fallback: 放宽半径/类别；仍失败则返回缓存 POI

---

## 3) RankCandidates

### 输入
- `pois`
- `user_preferences`
- `weights`

### 输出 schema
```json
{
  "candidates": [
    {"candidate_id":"cand_1","score":0.82,"risk_label":"傍晚人会变多","ai_judgement":"现在去比较轻松"}
  ],
  "top_n": 5
}
```

### timeout / retry / fallback
- timeout: `1500ms`
- retry: `0`
- fallback: 仅规则打分（距离/预算/营业中）

---

## 4) PickDestination

### 输入
- TopN candidates
- strategy: weighted_random

### 输出 schema
```json
{
  "pick_id": "pick_xxx",
  "picked_candidate_id": "cand_1",
  "alternatives": ["cand_2", "cand_3"]
}
```

### timeout / retry / fallback
- timeout: `300ms`
- retry: `0`
- fallback: 按分数最高直接选第一

---

## 5) GeneratePersonaReview

### 输入
- picked candidate
- persona

### 输出 schema
```json
{
  "persona": "独处型",
  "review": "这里不会逼你社交，适合一个人慢慢待着。",
  "risk": "傍晚可能没有你想的那么空。",
  "conclusion": "我会去。"
}
```

### timeout / retry / fallback
- timeout: `3000ms`
- retry: `1`
- fallback: 模板化文案（基于 category + risk）

---

## 6) ReturnResult

### 输入
- pick + persona_review + alternatives

### 输出
- 最终响应对象（前端直出）
- 写入 `recommendation_sessions/final_picks`

### 保证
- 只要 Pick 成功，即使 Persona 失败，也返回结果（persona 走 fallback）

---

## 失败场景最小可用策略

1. 定位拒绝：提示授权 + 手动输入位置
2. POI 空结果：自动放宽条件一次
3. LLM 超时：模板文案替代
4. 导航失败：返回经纬度供用户复制/切换地图
