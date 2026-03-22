# Engineering Bootstrap (MVP v1)

> 目标：任何新同学拉代码后，30 分钟内本地跑通 mock 闭环。

## 1. 技术栈冻结

- Node.js: **v24.4.1**
- 包管理器：**npm（统一，不混用 pnpm）**
- 前端：React + Vite + TypeScript + Tailwind
- 后端：FastAPI（Python 3.11+）
- 数据库：PostgreSQL 16
- 缓存（可选）：Redis 7
- ORM/SQL：
  - Python: SQLAlchemy + Alembic

---

## 2. 目录结构（统一）

```text
P003-Whatever/
  docs/
    api-contract.md
    data-schema.md
    orchestrator-flow.md
    dependency-boundary.md
    engineering-bootstrap.md
    milestone.md
  frontend/
    src/
    package.json
  backend/
    app/
      api/
      services/
      orchestrator/
      models/
      schemas/
    tests/
    requirements.txt
  configs/
    ranking-config.json
    logging.yaml
  scripts/
    bootstrap.sh
    dev-up.sh
    lint.sh
    test.sh
```

> 当前已有 UIUX 原型，可在第 2 周迁移/重命名至 `frontend/`。

---

## 3. 环境变量规范

## 3.1 文件分层
- `.env.example`：仅示例，不含真实密钥
- `.env.development`
- `.env.staging`
- `.env.production`

## 3.2 必填变量

```bash
APP_ENV=development
PORT=8000
FRONTEND_PORT=5173

DATABASE_URL=postgresql://user:pass@localhost:5432/p003
REDIS_URL=redis://localhost:6379/0

AMAP_KEY=***
LLM_API_KEY=***
LLM_BASE_URL=https://...

LOG_LEVEL=INFO
REQUEST_TIMEOUT_MS=8000
```

规则：
- 密钥只放 env，不入库、不写死、不打日志、不进前端
- `.env*` 加入 `.gitignore`（`.env.example` 除外）
- 前端禁止直接调任何带 Key 的第三方接口，一律经后端代理
- 所有 Key 在对应平台设置每日调用上限（开发阶段建议 500次/天）

---

## 4. 启动方式（标准命令）

## 4.1 前端

```bash
cd frontend
npm install
npm run dev
npm run build
npm run lint
npm run format
npm run test
```

## 4.2 后端

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
pytest
ruff check .
ruff format .
```

## 4.3 一键本地（可选脚本）

```bash
./scripts/bootstrap.sh
./scripts/dev-up.sh
```

---

## 5. 代码质量约束

- JS/TS：ESLint + Prettier
- Python：Ruff + Pytest
- Commit 规范：Conventional Commits
  - `feat: ...`
  - `fix: ...`
  - `docs: ...`
- 分支命名：
  - `feat/<module>-<short-desc>`
  - `fix/<module>-<short-desc>`

PR 合并前必须：
- [ ] lint 通过
- [ ] test 通过
- [ ] 契约变更同步更新 docs

---

## 6. 日志与脱敏规范

- 不打印完整 API key（仅前后 3 位）
- 不记录完整原始定位（经纬度保留 2~3 位精度）
- 用户输入日志需脱敏（手机号、邮箱、身份证等）
- 错误日志包含 `request_id`，便于追踪
- 严禁将第三方响应原文全量落日志

示例：
- ✅ `location=121.40,31.22`
- ❌ `location=121.397123,31.217889`

---

## 7. Secrets 泄漏响应流程

发现 Key 可能泄漏后，按此顺序处理，不要等确认再动：

1. **立即吊销** — 去对应平台（高德控制台 / LLM 平台）删除或禁用该 Key
2. **生成新 Key** — 创建新 Key，更新所有环境的 `.env` 文件
3. **排查来源** — `git log -S "泄漏的key字符串"` 检查是否已入库
4. **检查日志** — 看是否有异常调用记录（异常 IP、异常时段、异常调用量）
5. **回归验证** — 部署新 Key 后确认服务正常，旧 Key 确实失效

> 如果 Key 已进入 git 历史，必须用 `git filter-repo` 清除，不能只删文件。

---

## 8. 工程级 fallback 约束

新增接口/状态必须满足：
1. 有契约（request/response/error）
2. 有 fallback（降级路径）
3. 有前端状态（loading/empty/error/degraded）

如果缺任一项，不允许合并到主分支。

---

## 8. 第 2 周 Mock 闭环执行清单

### Day 1
- 前端 4 页（首页/候选/结果/历史）静态 mock 点通

### Day 2
- 后端搭 6 个 API 路由，先返回固定 JSON

### Day 3
- 前后端联调跑通主链路

### Day 4
- 补异常态（POI 空结果/LLM 超时/网络失败）

### Day 5
- 进行一次完整演示（必须真实走流程）
