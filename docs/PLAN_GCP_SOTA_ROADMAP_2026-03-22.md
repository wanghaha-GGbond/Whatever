# Whatever 项目云原生上线方案（GCP / 大厂级可落地版）

> 存档日期：2026-03-22
> 适用项目：`wanghaha-GGbond/Whatever`

## 总原则

对本项目，SOTA 不是一上来拆成 8 个微服务，而是：

**云原生 modular monolith（模块化单体）+ 托管基础设施 + 可观测 + 可回滚**。

Google Well-Architected Framework 强调的是安全、可靠、性能、成本和运维效率的平衡，而不是无脑复杂化。

## 当前仓库状态（基线）

- Vercel 只构建 `UIUX`，并把所有路由 rewrite 到 `index.html`。
- 前端 API 默认走 `VITE_API_BASE_URL || '/api/v1'`。
- 后端是 FastAPI，但数据库仍是本地 SQLite 文件。
- 前端存在大量 mock fallback，生产故障会被伪装成“还能用”。
- CORS 当前全开。

目标是把“好看的 demo”升级成“能上线、能排障、能扩展的 MVP”。

## 1. 目标架构（推荐最终形态）

### 推荐：Vercel + GCP 后端

```text
User
  ↓
Vercel (SPA / Static Assets / Edge CDN)
  ↓
api.yourdomain.com
  ↓
GCP HTTPS Load Balancer
  ↓
Cloud Armor (WAF / Rate Limit)
  ↓
Cloud Run (FastAPI API Service)
  ├─ Cloud SQL for PostgreSQL
  ├─ Cloud Tasks
  ├─ Secret Manager
  ├─ Cloud Logging / Monitoring / Trace
  └─ External APIs
      ├─ AMap
      └─ DeepSeek
```

### 这样配置的原因

- 前端继续留在 Vercel：Vite + React Router SPA 无需大改。
- 后端改 Cloud Run：全托管、自动扩缩容、支持 revision 流量切分与回滚。
- 数据库改 Cloud SQL PostgreSQL：托管关系型数据库，适合事务与历史/偏好模型。
- 异步任务用 Cloud Tasks：把 LLM 评价、埋点聚合、画像更新异步化。
- 镜像仓库用 Artifact Registry：Google 已推荐，Container Registry 已停止写入。
- Secrets 用 Secret Manager：集中管理，默认加密存储。
- 边界防护用 Cloud Armor：支持 throttle 和 rate-based ban。

## 2. 架构哲学：当前阶段不拆微服务

### 结论

**第一阶段坚持模块化单体，不拆微服务。**

### 理由

当前业务域仅 6 个核心域，可在单一 FastAPI 服务内做清晰边界：

1. Identity / Anonymous User
2. Recommendation Session
3. Maps & Geocoding
4. Pick & Persona Review
5. History / Feedback / Preference
6. Analytics / Dashboard

建议仅在以下信号出现至少 2 条时拆分服务：

- 某域有完全不同的伸缩曲线
- 某域有独立数据所有权
- 某域需要独立发布节奏

## 3. 业务层重构：流程驱动 → 域驱动

### 当前问题

- 首页写 session 到本地/后端
- 候选页再拿 candidates
- 结果页从 localStorage 拼 picked
- 历史页直接取全局 history

导致：

- 前端成业务真相源
- 页面状态漂移
- localStorage 污染
- 多用户隔离失效

### 目标域模型

```text
User
Session
Candidate
Pick
Feedback
History
Event
UserPreference
```

### 核心原则

- `Session` 是一次决策会话
- `Pick` 是一次最终抽中结果
- `History` 来自服务端持久化投影，不由前端拼装
- `Event` 是埋点原子事实
- `Preference` 从反馈和事件归纳

## 4. 前端改造方案（Vercel / React / Vite）

### 4.1 保留

- Vite
- React Router
- 当前页面信息架构
- 移动端优先 UI

### 4.2 必改

#### A. 生产禁用 mock fallback

- `development`：允许 mock fallback
- `staging/production`：禁止 mock fallback
- 失败必须进入 error state，而不是伪成功跳转

#### B. 前端仅保存最小状态

仅保留：

- `anonymous_user_token`
- 少量 UI 偏好

不再保存：

- `candidate_pool`
- `picked` 真相
- `history` 真相

#### C. 统一 API Client

统一到一个 `apiClient.ts`，支持：

- baseURL
- timeout
- request_id
- auth/anonymous token
- typed errors

#### D. 页面状态四分法

每页仅四态：

- loading
- success
- empty
- error

#### E. 埋点升级

- 普通事件：批量 flush
- 关键事件：即时 flush
- `pagehide` 使用 `sendBeacon`
- 埋点失败不影响主流程，但必须可观测

## 5. FastAPI 重构方案（Cloud Run API）

### 5.1 分层结构

```text
backend/app/
  api/
    v1/
      recommend.py
      history.py
      feedback.py
      analytics.py
      admin.py
  core/
      config.py
      logging.py
      security.py
      errors.py
      middleware.py
  domain/
      users/
      sessions/
      picks/
      preferences/
      analytics/
  services/
      amap_client.py
      llm_client.py
      ranking_service.py
      persona_service.py
  repositories/
      user_repo.py
      session_repo.py
      pick_repo.py
      history_repo.py
      event_repo.py
  models/
      orm.py
      schemas.py
  workers/
      tasks.py
```

### 5.2 接口语义标准化

统一 HTTP 语义：

- 200/201：成功
- 400：参数错误
- 401：未授权
- 404：资源不存在
- 409：幂等冲突
- 429：限流
- 502/504：上游失败
- 500：内部错误

统一响应结构：

```json
{
  "success": true,
  "data": {},
  "request_id": "req_xxx"
}
```

失败结构：

```json
{
  "success": false,
  "error": {
    "code": "UPSTREAM_TIMEOUT",
    "message": "LLM timeout"
  },
  "request_id": "req_xxx"
}
```

### 5.3 请求链路治理

每请求日志字段：

- request_id
- user_id
- session_id（如有）
- route
- latency_ms
- upstream（AMap / DeepSeek）
- fallback_used

### 5.4 同步/异步边界

同步请求只做：

- intent parse
- session init
- candidate fetch
- quick pick

异步任务（Cloud Tasks）：

- persona review 预计算
- 偏好画像更新
- dashboard 预聚合
- 埋点异步落库/清洗
- 上游调用重试

策略：**用户请求保持短、确定、可回退；慢逻辑异步化。**

### 5.5 推荐逻辑闭环

`keywords/open_now/budget/transport` 必须真正进入 ranking pipeline；
否则删掉假能力，只保留真实生效参数。

## 6. 数据库方案（PostgreSQL / Cloud SQL）

### 6.1 从 SQLite 升级到 PostgreSQL

Cloud SQL for PostgreSQL 用作线上主库。

### 6.2 建议表

```text
users
sessions
candidates
picks
feedbacks
histories
events
user_preferences
api_idempotency_keys
outbox_jobs
```

### 6.3 关键调整

- `history` 增加 `user_id`
- `picks` 增加 `user_id`
- `events` 与 user/session 强关联
- `sessions.candidates` 不长期存 JSON 真相
- `picked` 改为规范列 + snapshot JSON

### 6.4 数据治理

- Alembic 做 migration
- 表统一 `created_at/updated_at`
- 关键写操作引入幂等键
- dashboard 优先读事件表/聚合表

## 7. 安全架构

### 7.1 匿名身份

- 首访后端签发 `anonymous_user_token`
- HttpOnly Cookie 存储
- 服务端校验签名与过期
- 后续可升级账号体系

### 7.2 API 防护

Cloud Run 前置：

- HTTPS Load Balancer
- Cloud Armor

基础规则：

- `/recommend/init`：IP + cookie 限频
- `/events/track`：高频 throttle
- `/dashboard/*`：admin token
- 异常 UA / 爬虫行为 ban

### 7.3 CORS 收口

不再 `*`，仅允许可信域名（生产 + 预发域）。

### 7.4 Secrets

`AMAP_KEY`、`DEEPSEEK_API_KEY`、数据库连接串全部放 Secret Manager。

## 8. 可观测性（SRE）

### 8.1 三件套

- Logs
- Metrics
- Traces

可在 Cloud Run 上部署 Google-built OpenTelemetry Collector。

### 8.2 核心监控指标

业务指标：

- session_start
- candidate_fetch_success_rate
- pick_success_rate
- nav_click_rate
- feedback_submit_rate
- persona_review_latency
- llm_fallback_rate
- amap_fallback_rate

系统指标：

- p50/p95/p99 latency
- 4xx/5xx
- Cloud Run instance count
- DB connection saturation
- queue backlog
- queue retry count

### 8.3 建议 SLO

- API availability：99.9%
- `recommend/init` p95 < 500ms（不含外部 API）
- `recommend/candidates` p95 < 1.5s
- `persona/review` 同步 p95 < 2.5s（否则异步）

## 9. 部署与交付（DevOps）

### 9.1 制品流

```text
GitHub
  → GitHub Actions
  → Build Docker image
  → Push to Artifact Registry
  → Deploy Cloud Run
```

### 9.2 发布策略

Cloud Run revision + traffic splitting：

- `main` 自动部署到 staging
- 验收后 production canary 10%
- 观察 15~30 分钟
- 扩到 50%
- 最终 100%
- 异常立即 rollback

### 9.3 IaC

Terraform 管理：

- Cloud Run
- Cloud SQL
- Secret Manager
- Cloud Tasks
- Load Balancer
- Cloud Armor
- IAM
- Artifact Registry

## 10. 最终模块图

```text
[Web App]
Home / Candidates / Result / History / Dashboard

[API]
/auth/anonymous
/recommend/init
/recommend/candidates
/recommend/pick
/persona/review
/feedback/submit
/history/list
/events/track
/admin/dashboard/metrics

[Core Services]
IntentParser
RankingService
MapSearchService
PickService
PersonaService
PreferenceService
AnalyticsService

[Infra]
Postgres
Task Queue
Secrets
WAF
Observability
CI/CD
```

## 11. 分阶段落地计划

### Phase 1（7 天）

- 后端上 Cloud Run
- DB 切 Postgres
- 前端接 `VITE_API_BASE_URL`
- 关闭生产 mock fallback
- `history` 按 user 隔离
- `dashboard` 增加 admin token

### Phase 2（14 天）

- 结构化日志
- request_id
- Secret Manager
- Cloud Armor rate limit
- GitHub Actions
- staging/prod 双环境
- rollback 流程

### Phase 3（30 天）

- Cloud Tasks 异步任务
- persona review 异步化
- 偏好画像更新异步化
- metrics 聚合优化
- 更细 ranking pipeline
- A/B test + canary 发布

## 12. 最终结论

对本项目，专业且可落地的路线是：

**Vercel SPA + Cloud Run modular monolith + Cloud SQL PostgreSQL + Cloud Tasks + Cloud Armor + Secret Manager + OpenTelemetry + GitHub Actions + Terraform。**

优势：

- 复杂度最低
- 上线速度快
- 运维负担轻
- 可平滑扩展

## 参考资料

- Google Cloud Well-Architected Framework: https://cloud.google.com/architecture/framework
- Cloud Run 概览: https://docs.cloud.google.com/run/docs/overview/what-is-cloud-run
- Cloud SQL for PostgreSQL: https://cloud.google.com/sql/postgresql
- Cloud Tasks 文档: https://cloud.google.com/tasks/docs/
- Artifact Registry 迁移说明: https://cloud.google.com/artifact-registry/docs/transition/transition-from-gcr
- Secret Manager 相关文档: https://docs.cloud.google.com/workflows/docs/use-secret-manager
- Cloud Armor 限流: https://docs.cloud.google.com/armor/docs/rate-limiting-overview
- Cloud Run 请求超时: https://docs.cloud.google.com/run/docs/configuring/request-timeout
- Cloud Run + OTel Collector: https://cloud.google.com/stackdriver/docs/instrumentation/opentelemetry-collector-cloud-run
- Cloud Run 渐进发布/回滚: https://docs.cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration
