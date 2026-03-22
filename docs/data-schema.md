# Data Schema (MVP v1)

> 数据库建议：PostgreSQL 16+
> 命名：snake_case；主键 `bigserial` 或 `uuid`

## 1) users

| 字段 | 类型 | 说明 |
|---|---|---|
| id | uuid pk | 用户ID |
| channel | varchar(32) | 来源渠道（feishu/web） |
| external_user_id | varchar(128) | 渠道侧ID |
| created_at | timestamptz | 创建时间 |
| updated_at | timestamptz | 更新时间 |

索引：`uniq(channel, external_user_id)`

---

## 2) user_preferences

| 字段 | 类型 | 说明 |
|---|---|---|
| id | uuid pk | 记录ID |
| user_id | uuid fk users(id) | 用户ID |
| preferred_categories | jsonb | 偏好类型权重 |
| budget_min | int | 偏好预算下限 |
| budget_max | int | 偏好预算上限 |
| preferred_transport | varchar(32) | 常用通勤 |
| preferred_persona | varchar(32) | 常用人格 |
| updated_by_feedback_count | int | 被反馈更新次数 |
| created_at | timestamptz | 创建时间 |
| updated_at | timestamptz | 更新时间 |

索引：`idx_user_preferences_user_id`

---

## 3) recommendation_sessions

| 字段 | 类型 | 说明 |
|---|---|---|
| id | varchar(64) pk | 会话ID（rec_s_xxx） |
| user_id | uuid nullable | 登录用户ID |
| prompt | text | 原始输入 |
| normalized_intent | jsonb | 结构化意图 |
| city_code | varchar(16) | 城市码 |
| location_lng | numeric(10,6) | 经度 |
| location_lat | numeric(10,6) | 纬度 |
| status | varchar(32) | init/candidates/picked/closed |
| fallback_flags | jsonb | 各步骤是否降级 |
| created_at | timestamptz | 创建时间 |
| updated_at | timestamptz | 更新时间 |

索引：`idx_rec_sessions_user_id_created_at desc`

---

## 4) candidate_pois

| 字段 | 类型 | 说明 |
|---|---|---|
| id | varchar(64) pk | candidate_id |
| session_id | varchar(64) fk recommendation_sessions(id) | 所属会话 |
| poi_id | varchar(128) | 外部POI ID |
| name | varchar(128) | 地点名 |
| category | varchar(64) | 类别 |
| distance_m | int | 距离 |
| eta_min | int | 到达时长 |
| price_level | varchar(32) | 价格层级 |
| rating | numeric(3,2) nullable | 评分 |
| score | numeric(6,4) | 最终得分 |
| ai_judgement | text | AI判断 |
| risk_label | varchar(128) nullable | 风险标签 |
| rank_order | int | 排名 |
| created_at | timestamptz | 创建时间 |

索引：`idx_candidate_session_rank(session_id, rank_order)`

---

## 5) final_picks

| 字段 | 类型 | 说明 |
|---|---|---|
| id | varchar(64) pk | pick_id |
| session_id | varchar(64) fk recommendation_sessions(id) | 会话ID |
| candidate_id | varchar(64) fk candidate_pois(id) | 命中候选 |
| strategy | varchar(64) | weighted_random |
| temperature | numeric(3,2) | 随机温度 |
| reason_text | text | 入选理由 |
| alternatives | jsonb | 备选ID列表 |
| nav_url | text nullable | 导航链接 |
| created_at | timestamptz | 创建时间 |

索引：`idx_final_picks_session_id`

---

## 6) feedback_records

| 字段 | 类型 | 说明 |
|---|---|---|
| id | varchar(64) pk | feedback_id |
| session_id | varchar(64) fk recommendation_sessions(id) | 会话ID |
| pick_id | varchar(64) fk final_picks(id) | pick ID |
| went | boolean | 是否去了 |
| satisfaction | smallint | 1-5 |
| actual_cost | int nullable | 实际花费 |
| transport_used | varchar(32) nullable | 实际通勤 |
| tags | jsonb | 反馈标签 |
| note | text nullable | 文本备注 |
| created_at | timestamptz | 创建时间 |

索引：`idx_feedback_session_id`, `idx_feedback_pick_id`

---

## 补充（建议）

- `event_logs`（埋点事件表）
- `api_call_logs`（外部依赖调用日志，脱敏）
