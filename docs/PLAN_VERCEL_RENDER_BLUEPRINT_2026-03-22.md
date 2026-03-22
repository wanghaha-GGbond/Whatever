# Vercel + Render 落地蓝图（阶段执行版）

> 日期：2026-03-22
> 方向：前端 Vercel，后端 Render，先跑通真实链路再做异步化。

## 最终拓扑（当前阶段）

```text
Vercel
  └─ whatever-jade.vercel.app    # 前端 SPA

Render
  ├─ whatever-api                # FastAPI Web Service
  └─ whatever-db                 # Render Postgres
```

## 第二阶段预留（暂不上）

```text
Render
  ├─ whatever-worker             # Background Worker
  └─ whatever-kv                 # Key Value / Redis
```

## 环境变量约定

### Vercel Production

```bash
VITE_API_BASE_URL=https://whatever-api.onrender.com/api/v1
VITE_ENABLE_MOCK_FALLBACK=false
VITE_APP_ENV=production
```

### Render API

```bash
APP_ENV=production
DATABASE_URL=postgresql://...    # Render Postgres internal URL
AMAP_KEY=...
DEEPSEEK_API_KEY=...
ALLOWED_ORIGINS=https://whatever-jade.vercel.app
ADMIN_TOKEN=...
COOKIE_SIGNING_KEY=...
LOG_LEVEL=INFO
```

## 本阶段代码改造

1. 生产环境禁用 mock fallback（dev 保留）
2. Dashboard 改为统一 API client
3. CORS 从 `*` 收口到白名单域名
4. 增加后端 Dockerfile（为后续迁移与标准化部署做准备）

## 验收接口顺序

1. `/health`
2. `/api/v1/recommend/init`
3. `/api/v1/recommend/candidates`
4. `/api/v1/recommend/pick`
5. `/api/v1/history/list`
6. `/api/v1/dashboard/metrics`

