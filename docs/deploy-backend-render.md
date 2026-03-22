# 后端上线（Render）

仓库已添加 `render.yaml`，可直接用 Blueprint 部署 FastAPI 后端。

## 1) 推送代码到 GitHub

```bash
git add render.yaml
git commit -m "chore: add render blueprint for backend"
git push origin main
```

## 2) 在 Render 创建服务

打开下面链接（已绑定你的仓库）：

`https://dashboard.render.com/blueprint/new?repo=https://github.com/wanghaha-GGbond/Whatever`

然后在页面里：
- 确认服务名 `whatever-backend`
- 填写环境变量：
  - `APP_ENV=production`
  - `ALLOWED_ORIGINS=https://whatever-jade.vercel.app`
  - `AMAP_KEY`
  - `DEEPSEEK_API_KEY`
  - `ADMIN_TOKEN`
  - `COOKIE_SIGNING_KEY`
- 点击 `Apply`

## 3) 校验服务

部署完成后，访问：

`https://<你的-render-域名>/health`

返回 `{"status":"ok"}` 即正常。

## 4) 连接前端（Vercel）

在 Vercel 项目环境变量新增：

- `VITE_API_BASE_URL=https://<你的-render-域名>/api/v1`
- `VITE_ENABLE_MOCK_FALLBACK=false`
- `VITE_APP_ENV=production`

保存后重新部署前端。

## 注意：SQLite 持久化

当前 `DB_PATH=/tmp/p003.db`，重启/重建实例后数据会丢失（临时盘）。

如果要长期保存历史记录，建议改为托管数据库（如 Render Postgres），再把 `backend/app/db.py` 切换到 PostgreSQL。
