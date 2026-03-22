# 阶段计划（Render 优先）

> 日期：2026-03-22
> 执行策略：后端先稳定在 Render，后续再迁移到 GCP。

## 目标

在不做过度工程的前提下，把现有项目从 Demo 状态升级到可运维的线上 MVP。

## 当前基线

- 前端：Vite + React Router SPA（Vercel 部署）
- 后端：FastAPI（Render 部署）
- 数据：SQLite（现阶段保留）
- 现存问题：生产环境仍有 mock fallback、Dashboard 直连 fetch、错误态不清晰

## 本阶段必须落地

1. 生产环境禁用 mock fallback（dev 可保留）
2. 前端统一 API Client，避免页面直连 fetch
3. 错误态显式化（loading/success/empty/error）
4. Render 部署链路文档固化

## 本阶段执行清单

### 前端

- 新增环境开关：
  - `VITE_APP_ENV`
  - `VITE_ENABLE_MOCK_FALLBACK`
- 首页、候选页、结果页、历史页：
  - API 失败时在生产显示错误与重试
  - 不再静默切到 mock 数据
- Dashboard 改为统一 API Client 调用
- 埋点上报接口与 API 前缀统一

### 后端

- 保持 Render 运行方式稳定
- 补齐后端容器化基础文件（Dockerfile）用于后续迁移
- 继续沿用当前 `/api/v1` 路由契约

### 部署

- Vercel 继续以 `vercel.json` 构建 `UIUX`
- Render 继续作为后端线上环境
- 前端环境变量固定：
  - `VITE_API_BASE_URL=https://whatever-backend.onrender.com/api/v1`

## 验收标准

- 线上前端在后端异常时显示错误，不展示 mock 成功态
- Dashboard 指标请求走统一 API 客户端
- 本地 `npm run build` 通过
- 线上可通过 `/health` 和核心推荐链路验证

## 后续阶段（预留）

- SQLite -> PostgreSQL
- 匿名身份 token（HttpOnly）
- 请求链路 request_id + 结构化日志
- 云平台迁移至 Cloud Run / Cloud SQL / Cloud Tasks
