# 搜索质量修复计划

> 创建：2026-04-09 | 基于完整体验走查发现的4个问题

---

## 问题总览

| # | 问题 | 严重度 | 根本原因 |
|---|------|--------|---------|
| 1 | 说"咖啡馆"搜出来全是餐厅 | P0 — 功能性失效 | `AMAP_CATEGORY_CODES["咖啡"]` 包含 `050000`（所有餐饮的父类），把咖啡馆淹没 |
| 2 | `risk_label` 10张卡片全是同一句话 | P1 — 体验损失 | `make_risk_label()` 纯模板，所有餐厅类型命中同一个 key |
| 3 | `budget_text` 全显示"不限" | P1 — 信息缺失 | 仅读 Amap `price_level` 字段，该字段大多数 POI 为空；未读 `biz_ext.per_cost` |
| 4 | candidates 页标题和实际结果不符 | P2 — 信任损失 | 是问题1的下游效果；summary 说"有咖啡馆"但实际结果全是餐厅 |

---

## 修复方案

### 问题1：咖啡搜出餐厅（已修复 ✅）

**根本原因：**
```python
# 修复前
"咖啡": "050118|050000",   # 050000 = 所有餐饮父类，权重压倒咖啡馆
# 修复后
"咖啡": "050118|050119",   # 050118 = 咖啡厅, 050119 = 茶馆/茶艺馆
```

Amap POI 类型码是层级结构：`050000`（餐饮服务）> `050118`（咖啡厅）。
把父类和子类混在一起搜，高德返回所有餐饮 POI，咖啡馆被淹没。

同理检查其他类别是否有类似问题：
- `"商场": "060200|060201"` — 060200 是购物服务父类，060201 是购物中心；问题同上，修为只用 `060201|060202`
- `"书店": "060100|080703"` — 060100 是商场，080703 是书店；去掉 060100

---

### 问题2：risk_label 模板化（待修复）

**根本原因：** `_RISK_TEMPLATES` 是纯关键词匹配，同类型 POI 全部输出相同文案。

**方案：** 去掉 `risk_label` 字段，功能合并进 LLM 生成的 `ai_judgement`。
- `ai_judgement` 已经是 LLM 生成（命运独白），风险提示可以融入其中
- 不需要单独一个模板字段，前端隐藏 `risk_label` 或后端不再返回

---

### 问题3：budget_text 全是"不限"（待修复）

**根本原因：** Amap 的 `price_level`（0-4档）大多数 POI 不填，但 `biz_ext.per_cost` 字段有真实人均价格数字（如 "35"、"128"）。

**方案：** 在 `amap.py` 的 POI 处理逻辑中，优先读 `biz_ext.per_cost`：
```python
per_cost = poi.get("biz_ext", {}).get("per_cost", "")
if per_cost and per_cost.isdigit():
    budget_text = f"人均¥{per_cost}"
else:
    budget_text = budget_text_from_level(price_level, budget_max)
```

---

### 问题4：summary 内容不符（问题1修复后自动改善）

问题1修复后，搜出来的就是真正的咖啡馆，`generate_search_summary` 的 `type_labels` 会传入正确类型，summary 自然准确。不需要单独修复。

---

## 执行顺序

- [x] **问题1** — `llm.py` AMAP_CATEGORY_CODES 类型码清理
- [x] **问题2** — `routes.py` risk_label 返回 null，移除模板调用
- [x] **问题3** — `amap.py` per_cost + `intent_parser.py` budget_text 读真实人均价
- [x] **问题4** — 问题1修复后自动改善
