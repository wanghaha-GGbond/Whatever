# Render + Vercel 文件级改造清单

## 前端

- `UIUX/src/app/lib/env.ts`
  - 新增环境开关：`VITE_APP_ENV`、`VITE_ENABLE_MOCK_FALLBACK`、`VITE_API_BASE_URL`
- `UIUX/src/app/lib/api.ts`
  - 统一 API 基址、超时、错误对象
  - 新增 `getDashboardMetrics`
  - `getHistory` 支持 `user_id` 过滤
- `UIUX/src/app/lib/analytics.ts`
  - 埋点请求统一走 API 前缀
  - 增加 `pagehide + sendBeacon` 保底上报
- `UIUX/src/app/pages/home.tsx`
  - 生产禁用本地兜底，失败显示错误不自动跳转
- `UIUX/src/app/pages/candidates.tsx`
  - 生产禁用 mock 候选与 mock 抽签
  - 增加加载错误/抽签错误状态
- `UIUX/src/app/pages/result.tsx`
  - 生产禁用随机 mock 结果
  - 增加页面错误与人格试玩错误状态
- `UIUX/src/app/pages/history.tsx`
  - 历史查询按 `user_id` 请求
  - 生产禁用 mock 历史
- `UIUX/src/app/pages/dashboard.tsx`
  - 改为统一 API client，不再裸 `fetch`
- `UIUX/.env.example`
  - 新增前端环境变量示例

## 后端

- `backend/app/db.py`
  - 重构为 SQLAlchemy 持久化层
  - 支持 `DATABASE_URL`（Postgres）+ SQLite 回退
  - 历史查询支持按 `user_id` 过滤
  - 增加旧库字段自动补齐兼容
- `backend/app/routes.py`
  - `feedback` 写历史时透传 `user_id`
  - `history/list` 增加 `user_id` 查询参数
- `backend/app/main.py`
  - CORS 改为 `ALLOWED_ORIGINS` 环境变量控制
- `backend/requirements.txt`
  - 新增 `sqlalchemy`、`psycopg[binary]`
- `backend/.env.example`
  - 补齐生产环境关键变量
- `backend/Dockerfile`
  - 新增后端容器启动配置
- `backend/.dockerignore`
  - 新增容器构建忽略规则

## 部署与计划文档

- `docs/deploy-backend-render.md`
  - 补充 Vercel/Render 环境变量对照
- `docs/PLAN_STAGE_RENDER_FIRST_2026-03-22.md`
  - 阶段计划（Render 优先）
- `docs/PLAN_VERCEL_RENDER_BLUEPRINT_2026-03-22.md`
  - 架构蓝图（Vercel + Render）
- `docs/PLAN_GCP_SOTA_ROADMAP_2026-03-22.md`
  - 后续 GCP 演进路线（预留）

