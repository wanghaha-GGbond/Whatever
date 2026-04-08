# Whatever 开发路线图

> 最后更新：2026-04-08

---

## 已完成版本回顾

### v0.1 — MVP 闭环（2026-03 初）
- FastAPI + React 基础框架搭建
- 高德 POI 搜索接入
- 规则 NLU（intent_parser.py）
- 基础 4 人格模板评价
- Render + Vercel 部署

### v0.2 — 稳定性升级
- LLM SOTA 人格声音（DeepSeek 深度 prompt 调优）
- 异常降级体系（超时 / 空结果 / LLM 失败均有兜底）
- 前端异常态处理

### v0.3 — 惊喜引擎
- `pick_reason()` 命运独白：LLM 生成候选卡片理由
- Wild Card 机制：一张低分牌随机晋级（serendipity）
- 时间 + 天气上下文注入 LLM（傍晚雨天推室内场所）

### v0.4 — 地图预览
- 结果页嵌入高德静态地图（后端代理，不暴露 key）
- 用户位置蓝点 + 目标绿点双标记

### v0.5 — 分享卡片 + 切片升级
- `/persona/review` 响应从纯文本升级为 4 场景切片结构（`slices[]` + `summary`）
- `PersonaSliceView` 横向滑动切片组件
- `ShareCardNode` + `useShareCard` — html2canvas 生成分享图，Web Share API + 下载兜底

### v0.6 — 名人视角 PRO（当前版本，2026-04-06 ～ 04-08）
- Steve Jobs `.skill` 文件（persona system prompt 独立文件化）
- `celebrity_persona_review()` — 名人风格评价，含 `verdict` 辣评字段
- `CelebrityPersonaCard` 深色 PRO 卡片 + `ProGateSheet` 订阅底栏（UI 已做，逻辑 beta 直接开）
- AI 地图搜索升级：LLM 多类型权重意图解析（`parse_intent_with_ai`），替代纯规则 NLU
- `generate_search_summary()` — 候选页自然语言标题
- `recommend/init` 并发重构（3 路 async.gather，-1s 延迟）
- inspire 预取（页面加载即预热，点按钮瞬间响应）
- LLM 层全面加固（json.loads 保护、独立超时、celebrity 降级修正、prompt injection 截断）

---

## 当前状态（2026-04-08）

| 模块 | 状态 | 说明 |
|------|------|------|
| 核心推荐流程 | ✅ 稳定 | init → candidates → pick 全流程跑通 |
| 人格评价切片 | ✅ 完成 | 4 场景切片 + summary，LLM 生成 |
| 名人 PRO（Jobs） | ✅ 完成 | verdict 辣评，Beta 全员开放 |
| AI 意图解析 | ✅ 完成 | 多类型权重，时间天气上下文 |
| 分享卡片 | ✅ 完成 | html2canvas，微信/下载双兜底 |
| 地图预览 | ✅ 完成 | 静态图代理 |
| 匿名用户体系 | ✅ 完成 | cookie-based anon token |
| 历史记录 | ✅ 完成 | 分页列表 + 首页上次去了卡片 |
| Dashboard | 🟡 基础 | 存在但功能简单 |
| PRO 付费逻辑 | 🔴 未做 | `isPro()` beta 硬编码 true |
| 多名人（非 Jobs） | 🔴 未做 | skill 文件只有 jobs.skill |
| Web Search 真实评价 | 🔴 未做 | 切片内容仍为纯 AI 推测 |
| 用户认证（手机号/微信） | 🔴 未做 | 仍是匿名 |

---

## 近期规划（v0.7 ～ v1.0）

### v0.7 — 更多名人 + PRO 打通（预估 1 周）

**目标**：让 PRO 功能有内容深度，并打通付费路径

- [ ] 新增 2-3 个名人 skill 文件（候选：马斯克、巴菲特、村上春树）
  - 每个 skill 文件要有独特的决策框架和语言风格
  - 在 `celebrities.ts` 中注册，结果页 celebrity 选择栏展示
- [ ] PRO 付费逻辑实现（简单版）
  - `isPro()` 从 localStorage 读取，默认 false
  - ProGateSheet 支持"限时体验"或微信联系解锁
  - 不需要支付宝/微信支付对接，联系方式即可
- [ ] celebrity 切片 UI 打磨
  - verdict 辣评块视觉再强化（现有 amber 卡片是否够味）
  - review paragraph 和 slices 视觉层次感

### v0.8 — 真实内容注入（预估 2 周）

**目标**：切片从"AI 推测"升级为"有依据的推测"

- [ ] Web Search Agent（基于 Tavily / Brave Search API）
  - 在 `/persona/review` 前异步搜 `{店名} 评价`
  - 提取评价片段作为 LLM context 注入（不替代 AI 生成，而是作为素材）
  - 超时 3s 内没结果则降级纯 AI 生成
- [ ] 切片真实性标注
  - 如有搜索来源，切片底部显示小小的"来源参考"标记
  - 纯 AI 生成切片标注"AI 推测"

### v0.9 — 体验打磨 + 增长钩子（预估 1-2 周）

**目标**：为真实用户传播做准备

- [ ] 分享卡片 2.0
  - 加入名人 verdict 辣评到分享卡片（目前只有普通人格）
  - 优化分享卡片视觉，更适合小红书比例（4:3 或竖版）
- [ ] 首页体验优化
  - 筛选 chips 当前状态检视（"和谁去" 选项是否覆盖场景）
  - 加入"工作日午餐"快速模式入口（一键进入午饭专项人格）
- [ ] 候选页优化
  - Wild Card 视觉标记（"命运之选"特殊样式）
  - 已淘汰候选灰显动画

### v1.0 — 基础设施完善（预估 2 周）

**目标**：支撑真实用户量，可公开推广

- [ ] 用户认证
  - 手机号验证码登录（阿里云短信 / 腾讯云）
  - 匿名 → 注册数据合并（保留历史）
- [ ] PostgreSQL 正式迁移
  - Render PostgreSQL 实例（当前已有 DATABASE_URL 支持，需测试）
  - 数据库 schema migration 脚本
- [ ] Dashboard 权限保护
  - 简单密码 or IP 白名单
  - 核心指标：北极星（抓阄→导航率）、LLM 超时率、每日 session 数
- [ ] CORS 收紧
  - 当前允许所有域名，上线后锁定 Vercel 域名
- [ ] 错误监控
  - Sentry 接入（前端 + 后端）

---

## 中期规划（V1.x）

| 功能 | 说明 | 依赖 |
|------|------|------|
| 群决策模式 | 多人同时投票候选，最终抓阄 | 用户认证 |
| 偏好学习 | 反馈数据驱动下次推荐权重调整 | 足够反馈量 |
| 午餐专项人格 | 4 午饭人格（老饕/效率党/精算师/氛围感）当前已有 prompt，需 UI 入口 | 场景路由 |
| 咖啡/下午茶场景 | 第二场景扩展，独立入口 | V1.0 稳定后 |
| PWA 离线缓存 | 上次结果可离线查看，Service Worker | 稳定版本 |

---

## 技术债 / 已知问题

| 问题 | 优先级 | 说明 |
|------|--------|------|
| `isPro()` 硬编码 true | P1 | v0.7 前解决，不然 PRO 功能白做 |
| LLM 超时在 Render Free 冷启动场景 | P1 | 冷启动 ~30s，init 超时概率高；考虑 /health 预热或迁移付费实例 |
| `ai_judgement` 截断 50 字可能太短 | P2 | 部分命运独白被截，可调到 60-70 |
| 候选页 generate_search_summary 并发 | P2 | 目前与 enrich_ai_judgements 并发，但 summary 失败时 fallback 文案需要更好 |
| 分享卡片 html2canvas 中文字体渲染 | P2 | 在某些 Android 设备上中文字体可能 fallback |
| intent_parser.py 规则覆盖不足 | P3 | 作为 LLM 降级方案，目前 CATEGORY_MAP 覆盖有限 |
