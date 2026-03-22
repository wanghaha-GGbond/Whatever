# Exception Test Script (Mock 阶段)

> 目的：系统化验证异常路径，不靠临场发挥。
> 记录规则：每项都填写“实际结果”，并标记 PASS/FAIL。

## 前置条件
- 后端启动：`uvicorn app.main:app --reload --port 8000`
- 前端启动：`npm run dev`
- 默认无 debug 头时，走正常链路
- 异常复现通过 Header：`X-Debug-Scenario`

---

## 测试记录表

| 场景 | 触发方式 | 预期结果 | 实际结果 |
|---|---|---|---|
| 1. 定位拒绝 | `POST /recommend/init` 带 `X-Debug-Scenario: location_denied` | 首页提示无法获取附近地点，可重试或手动继续 | 待填写 |
| 2. 候选为空 | `POST /recommend/candidates` 带 `X-Debug-Scenario: empty_candidates` | 候选页显示“附近没找到合适地点”，可放宽条件/返回首页 | 待填写 |
| 3. 抓阄失败 | `POST /recommend/pick` 带 `X-Debug-Scenario: pick_error` | 保留候选页，不丢 session，可重试 | 待填写 |
| 4. 人格试玩超时 | `POST /persona/review` 带 `X-Debug-Scenario: persona_timeout` | 结果页保留地点，试玩区展示降级模板文案 | 待填写 |
| 5. 反馈提交失败 | `POST /feedback/submit` 带 `X-Debug-Scenario: feedback_500` | 主流程不受阻，提示稍后重试 | 待填写 |
| 6. 历史为空 | `GET /history/list` 带 `X-Debug-Scenario: history_empty` | 展示历史空状态，不报错 | 待填写 |
| 7. 网络断开 | 前端 DevTools -> Offline | 页面不白屏，统一错误提示 | 待填写 |
| 8. 导航失败 | 前端模拟导航拉起失败（mock reject） | 提示“无法打开导航”，保留地点信息 | 待填写 |

---

## 推荐手测命令（curl）

```bash
# 1) 定位拒绝
curl -X POST http://localhost:8000/api/v1/recommend/init \
  -H 'Content-Type: application/json' \
  -H 'X-Debug-Scenario: location_denied' \
  -d '{"prompt":"骑车20分钟内，预算50"}'

# 2) 候选为空（先正常 init 获取 session_id）
curl -X POST http://localhost:8000/api/v1/recommend/candidates \
  -H 'Content-Type: application/json' \
  -H 'X-Debug-Scenario: empty_candidates' \
  -d '{"session_id":"rec_s_xxx","limit":5}'

# 3) 抓阄失败
curl -X POST http://localhost:8000/api/v1/recommend/pick \
  -H 'Content-Type: application/json' \
  -H 'X-Debug-Scenario: pick_error' \
  -d '{"session_id":"rec_s_xxx"}'

# 4) 人格超时
curl -X POST http://localhost:8000/api/v1/persona/review \
  -H 'Content-Type: application/json' \
  -H 'X-Debug-Scenario: persona_timeout' \
  -d '{"session_id":"rec_s_xxx","pick_id":"pick_xxx","persona":"独处型"}'

# 5) 反馈失败
curl -X POST http://localhost:8000/api/v1/feedback/submit \
  -H 'Content-Type: application/json' \
  -H 'X-Debug-Scenario: feedback_500' \
  -d '{"session_id":"rec_s_xxx","pick_id":"pick_xxx","went":true,"satisfaction":4}'

# 6) 历史为空
curl 'http://localhost:8000/api/v1/history/list?page=1&page_size=20' \
  -H 'X-Debug-Scenario: history_empty'
```

---

## 测试结论
- 主链路连续成功次数：___ / 3
- 关键异常稳定复现数：___ / 4（最少）
- 总结：PASS / FAIL
- 阻塞问题：
  1. 
  2. 
