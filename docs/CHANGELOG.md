# CHANGELOG

所有重要变更按版本倒序记录。

---

## [v0.6.1] — 2026-04-08

### Fixed
- LLM 层全面加固：所有 `json.loads()` 加 try/except，LLM 输出乱码不再返回 500
- `parse_intent_with_ai` 空 categories 改为抛 ValueError，触发规则 NLU 降级而非错误默认"公园"
- Celebrity 降级不再复用 `PERSONA["独处型"]` 模板（缺少 `verdict`/`slices` 字段），改为独立错误 dict
- `_load_celebrity_skill` 加 FileNotFoundError 保护
- `user_prompt` 截断至 300 字符，防止 prompt injection

### Performance
- 各 LLM 函数加独立超时：`persona_review=9s`, `pick_reason=5s`, `generate_inspire=6s`, `generate_search_summary=5s`, `parse_intent_with_ai=7s`
- `celebrity_persona_review` max_tokens 1200→1500（更完整的名人点评）
- `pick_reason` temperature 1.1→0.95（减少废话漂移）
- `generate_inspire` temperature 1.4→1.1（依然有创意，减少乱输出）
- `ai_judgement` 长度限制 50 字符

### Docs
- CLAUDE.md 更新至 v0.6 实际架构（8 个端点、并发重构、celebrity PRO、skill 文件）
- 新增 `docs/ROADMAP.md`：v0.1～v0.6 历史、当前状态表、v0.7～v1.0 规划、技术债清单

---

## [v0.6.0] — 2026-04-06 ～ 2026-04-08

### Added
- **名人视角 PRO**：`backend/app/skills/jobs.skill` Steve Jobs 专属 persona 文件
- `celebrity_persona_review()` — .skill 文件作为 system prompt，输出含 `verdict` 辣评字段
- `CelebrityPersonaCard` 深色 PRO 卡片（结果页）
- `ProGateSheet` 订阅底栏（UI 完成，订阅逻辑 beta 期全员开放）
- `verdict` 辣评渲染块（结果页 PRO 面板底部，🔥 amber 样式）
- `generate_search_summary()` — 候选页标题自然语言生成
- **AI 地图搜索升级**：`parse_intent_with_ai()` 多类型权重意图解析，替代纯规则 NLU
- 时间 + 天气上下文注入 LLM（傍晚雨天推室内）
- `_score_poi()` 支持 `type_weights` 加权 + `preferred_category` +0.07 加成
- `regeo_with_adcode()` + `get_weather_by_adcode()` — 消除双 regeo 问题

### Performance
- `recommend/init` 并发重构：GPS 路径 3 路 asyncio.gather，文字地址 2+2 路，约减少 1s
- inspire 预取：页面加载即后台预热，点按钮瞬间响应（stale-while-revalidate 模式）
- `celebrity_persona_review` timeout 提升至 22s，解决 max_tokens=1200 必然超时问题

### Fixed
- Celebrity panel 只显示一句话的 bug（根本原因：8s 全局 timeout < 1200 token 所需时间）
- `/persona/review` 响应漏掉 `verdict` 字段
- `prefetchInspire` 缺少 `useCallback` 导致 React Strict Mode 下重复触发

---

## [v0.5.0] — 2026-04-04

### Added
- **分享卡片**：`ShareCardNode` 隐藏 DOM + `useShareCard` hook（html2canvas + Web Share API + 下载兜底）
- `PersonaSliceView` 横向滑动切片组件
- `/persona/review` 响应升级：新增 `slices[]`（4 场景切片）+ `summary` 字段
- `persona_review()` 输出结构化 4 切片（to_door / enter / during / leave）

---

## [v0.4.0] — 2026-03 末

### Added
- 结果页嵌入高德静态地图（后端代理，不暴露 API key）
- `GET /static-map` 端点（poi_location + user_location 双标记）
- 用户位置蓝点 + 目标绿点标记

---

## [v0.3.0] — 2026-03 中

### Added
- **惊喜引擎**：`pick_reason()` LLM 命运独白，替代模板文案
- Wild Card 机制：候选池中随机晋级一张低分牌（serendipity）
- 时间上下文注入（星期/时段/季节/天气）→ `_build_time_context()`
- `generate_inspire()` — 首页"AI 帮我想一个"按钮

---

## [v0.2.0] — 2026-03 初

### Added
- DeepSeek LLM SOTA 人格声音（8 个人格深度 prompt 调优）
- 全链路异常降级体系（LLM 超时 / POI 空结果 / 网络故障均有兜底）
- `X-Debug-Scenario` 调试头支持

### Fixed
- 前端多处异常态处理（定位拒绝、服务冷启动提示）

---

## [v0.1.0] — 2026-03 初（初始上线）

### Added
- FastAPI 后端骨架（6 端点，SQLite）
- React 18 + Vite + Tailwind 4 前端
- 高德 POI 周边搜索接入
- 规则 NLU（intent_parser.py）意图解析
- 4 人格模板评价（独处型/探索型/务实型/审美型）
- 4 午饭专项人格（老饕/效率党/精算师/氛围感）
- Render + Vercel 部署，PWA 支持
- 匿名用户体系（cookie-based anon token）
- 历史记录存储 + 分页列表
