# Git 仓库规范

## 1. 目的

本规范用于统一项目仓库的目录结构、分支管理、提交规范、代码合并流程与协作方式，降低多人协作、Codex/Web 端提交、本地开发并行时产生的混乱和冲突风险。

适用场景：

* 个人项目长期维护
* 与 AI 编码工具协作开发
* 多分支并行开发
* 网站 / 前端 / 产品原型 / Agent 项目管理

---

## 2. 基本原则

### 2.1 主分支始终可用

* `main` 分支必须保持可运行、可部署、可回滚。
* 未完成功能、试验代码、临时调试代码不得直接提交到 `main`。

### 2.2 小步提交，清晰可追踪

* 一次提交只做一类改动。
* 提交信息必须清晰描述改动目的。
* 禁止使用无意义提交信息，如：`update`、`test`、`123`、`fix bug`。

### 2.3 所有改动优先走分支

* 新功能、修复、重构、文案修改均应在独立分支完成。
* 合并到 `main` 前应先 review。

### 2.4 先看状态，再操作 Git

每次进行 Git 操作前，优先执行：

```bash
git status
git branch
git log --oneline --graph --decorate -10
```

---

## 3. 仓库目录规范

建议目录结构如下：

```text
project/
├─ app/                  # Next.js App Router 或页面入口
├─ src/                  # 核心业务代码（如有）
├─ public/               # 静态资源
├─ docs/                 # 项目文档、方案、规划
│  ├─ brand/
│  ├─ copywriting/
│  ├─ product/
│  └─ roadmap/
├─ scripts/              # 构建、迁移、辅助脚本
├─ tests/                # 测试代码（如有）
├─ .gitignore
├─ README.md
├─ package.json
└─ repository-guidelines.md
```

### 3.1 推荐纳入版本管理的内容

* 源代码
* 配置文件
* 文档
* 必要静态资源
* 脚本文件

### 3.2 禁止纳入版本管理的内容

* `node_modules/`
* `.next/`
* `dist/`
* `build/`
* 本地数据库
* 临时导出文件
* 日志文件
* 系统缓存文件
* 各类密钥、令牌、环境变量文件

---

## 4. `.gitignore` 规范

前端 / Next.js 项目建议至少包含：

```gitignore
node_modules/
.next/
out/
dist/
build/
coverage/
.env
.env.local
.env.development.local
.env.test.local
.env.production.local
*.log
.DS_Store
Thumbs.db
.vercel/
```

若项目包含本地数据库或实验文件，也应补充：

```gitignore
*.sqlite
*.db
tmp/
temp/
.cache/
```

---

## 5. 分支管理规范

## 5.1 主分支

* `main`：稳定分支，仅保留可运行、可部署版本。

## 5.2 功能分支命名规范

统一使用以下前缀：

* `feat/`：新功能
* `fix/`：问题修复
* `refactor/`：重构
* `docs/`：文档修改
* `content/`：文案、页面内容修改
* `style/`：样式调整
* `chore/`：杂项维护

示例：

```text
feat/new-age-homepage
fix/mobile-navbar-overflow
refactor/product-card-structure
docs/repository-guidelines
content/new-age-copy-update
style/homepage-hero-spacing
chore/update-dependencies
```

## 5.3 分支使用规则

* 一个分支只处理一个主题。
* 不要在同一个分支里混合功能开发、文案修改、样式调整和 Bug 修复。
* 分支合并完成后及时删除。

---

## 6. 提交规范

## 6.1 提交格式

统一采用：

```text
<type>: <summary>
```

推荐类型：

* `feat`
* `fix`
* `docs`
* `refactor`
* `style`
* `test`
* `chore`

示例：

```bash
git commit -m "feat: add New Age landing page"
git commit -m "fix: resolve mobile navbar overflow"
git commit -m "docs: add repository management guidelines"
git commit -m "refactor: rename New_Age to New Age in UI"
git commit -m "style: adjust homepage hero spacing"
```

## 6.2 提交粒度

* 一次提交只做一件事。
* 不要把多个无关改动塞到同一个 commit。
* 提交前尽量自查是否包含无关文件。

---

## 7. 日常开发流程

## 7.1 开发前

先同步主分支：

```bash
git checkout main
git pull origin main
```

## 7.2 新建开发分支

```bash
git checkout -b feat/xxx
```

## 7.3 开发完成后提交

```bash
git status
git add .
git commit -m "feat: xxx"
```

## 7.4 推送分支

```bash
git push origin feat/xxx
```

## 7.5 发起 Pull Request

* 在 GitHub 上创建 PR
* Review 通过后合并到 `main`

## 7.6 合并后本地同步

```bash
git checkout main
git pull origin main
```

## 7.7 删除已完成分支

```bash
git branch -d feat/xxx
git push origin --delete feat/xxx
```

---

## 8. Pull Request 规范

PR 应满足以下要求：

* 标题清晰说明本次改动目的
* 描述中说明：改了什么、为什么改、影响范围是什么
* 尽量附上截图或演示链接（前端项目）
* 不要把过大的改动集中到一个 PR 中

推荐 PR 模板：

```md
## Summary
- 改了什么
- 为什么改
- 影响哪些页面/模块

## Testing
- [ ] 本地运行通过
- [ ] 关键路径已验证
- [ ] 无明显样式错误

## Notes
- 需要关注的风险点
- 后续待做事项
```

---

## 9. 与 Codex / AI 工具协作规范

## 9.1 基本原则

* AI 工具的改动必须通过独立分支或 PR 合并。
* 禁止 AI 工具直接覆盖 `main`。
* AI 改动合并前必须人工 review。

## 9.2 推荐流程

1. 本地或 GitHub 创建任务分支
2. 让 Codex / Web 端在该分支上提交
3. 在 GitHub 查看 diff
4. Review 后合并 PR
5. 本地执行：

```bash
git checkout main
git pull origin main
```

## 9.3 注意事项

* 不要同时在本地和 Codex 上修改同一分支的同一批文件。
* 若必须并行修改，优先拆分文件或拆分任务边界。
* 所有 AI 生成代码都需要人工确认是否符合项目结构与风格。

---

## 10. 冲突处理规范

发生冲突时：

1. 先确认当前分支和目标分支
2. 阅读冲突标记
3. 决定保留哪部分代码
4. 修改完成后执行：

```bash
git add .
git commit -m "fix: resolve merge conflict"
```

### 严禁

* 不看内容直接全量覆盖
* 在不理解冲突来源的情况下强行 push

---

## 11. 发布与回滚建议

## 11.1 发布前检查

* 当前分支是否为 `main`
* 工作区是否干净
* 最近提交是否明确
* 关键页面是否本地验证
* 环境变量是否正确配置

## 11.2 打标签（可选）

重要版本建议打 tag：

```bash
git tag -a v0.1.0 -m "first stable release"
git push origin v0.1.0
```

## 11.3 回滚思路

若线上出问题：

* 优先回滚到最近稳定提交
* 或回滚到最近 tag 版本

---

## 12. README 建议结构

建议 `README.md` 至少包含：

```md
# 项目名称

## 项目简介

## 技术栈

## 目录结构

## 本地运行方式

## 部署方式

## 分支规范

## 仓库规范
```

---

## 13. 禁止事项

以下行为应避免：

* 直接在 `main` 上长时间开发
* 长期不提交，累积大量未保存改动
* 提交无意义 message
* 把 `.env`、数据库、构建产物提交到仓库
* 不 review 就合并 AI 工具生成代码
* 在未确认状态时执行 `push --force`

---

## 14. 最小执行版本

如果只保留最核心的规则，请至少做到：

1. `main` 只放稳定代码
2. 所有修改先开分支
3. 每次提交只做一类改动
4. 提交信息写清楚
5. 每次操作前先看 `git status`
6. 所有 Codex 改动通过 PR 合并

---

## 15. 常用命令速查

### 查看状态

```bash
git status
git branch
git log --oneline --graph --decorate -10
```

### 同步主分支

```bash
git checkout main
git pull origin main
```

### 新建分支

```bash
git checkout -b feat/xxx
```

### 提交

```bash
git add .
git commit -m "feat: xxx"
```

### 推送

```bash
git push origin feat/xxx
```

### 删除分支

```bash
git branch -d feat/xxx
git push origin --delete feat/xxx
```

---

## 16. 结语

Git 仓库管理的重点不在于命令多，而在于规则稳定。

当目录清楚、分支清楚、提交清楚、PR 清楚时，仓库就会保持长期可维护；
当项目开始接入 AI 工具、多人协作或持续迭代时，这套规范会显著降低混乱和返工成本。
