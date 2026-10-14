# after-sales-agent

第一阶段实现一个可供 Dify 调用的售后工具服务。当前使用内存测试数据，目标是先验证：

- 结构化查询订单和物流；
- 创建售后申请时的参数校验、业务状态校验和幂等；
- 统一错误码和请求 ID；
- 后续替换为 mall HTTP 客户端时不改变 Dify 工具契约。

## 启动

```powershell
cd C:\Users\ZZL\Desktop\shixixiangmu\after-sales-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[test]"
uvicorn app.main:app --host 0.0.0.0 --reload --port 8001
```

打开 Swagger：http://127.0.0.1:8001/docs

保持这个终端窗口运行；Dify 在 Docker 中调用时会通过 host.docker.internal:8001 访问本服务。

## 示例

```powershell
curl http://127.0.0.1:8001/orders/202609070001
curl http://127.0.0.1:8001/orders/202609070001/logistics
```

创建售后申请：

```powershell
$body = '{"order_no":"202609070001","type":"QUALITY_REFUND","reason":"商品有质量问题","idempotency_key":"202609070001-quality-1"}'
curl -Method Post -ContentType 'application/json' -Body $body http://127.0.0.1:8001/after-sales/applications
```

重复使用同一个 `idempotency_key` 会返回第一次申请，并带有 `X-Idempotent-Replay: true` 响应头。

## 当前边界

- 数据保存在进程内存，重启后恢复为种子数据；
- 尚未接入 mall；
- 售后规则检索仍在 Dify 工作流中完成；
- 当前 API 只用于本地开发，不包含生产鉴权。




## 当前进度（2026-09-27）

已完成：

- FastAPI 售后工具服务；
- 订单查询、物流查询、售后申请接口；
- 订单状态校验和幂等键；
- Dify SSRF 本地联调配置；
- Dify 动态订单查询和物流查询；
- LLM 读取工具 JSON 并通过输出节点返回结果；
- 端到端测试：订单 `202609070001` 查询成功。

当前阶段（2026-09-28）：

1. 已将 `docs/kb/after-sales-rules.md` 导入 Dify 的 `电商售后规则库`；
2. 已创建从“开始”节点出发的 `知识检索 2`，绑定 `用户输入 / user_question`；
3. 已验证 FastAPI 健康、订单和物流接口仍可用；
4. 已把知识检索结果绑定到 LLM 上下文，并在 Prompt 中插入特殊变量 `上下文`；
5. 已完成普通商品联合测试；待清理早期未连通节点并测试特殊商品、待付款三类场景；
6. 再增加售后资格判断、转人工和“用户确认后创建售后申请”。

项目过程记录：

- RAG 阶段总结： `docs/interview/step-03-rag.md`；
- RAG HTML 材料： `docs/interview/step-03-rag.html`；

- 面试总结：`docs/interview/step-02-order-logistics.md`；
- HTML 面试材料：`docs/interview/step-02-order-logistics.html`；
- 故障复盘：`docs/incidents/incident-index.md`。




## 当前进度（2026-09-30）

本轮已完成：

- 修复 Dify“查询物流”节点遗漏 `/logistics` 路径的问题；
- 普通商品联合测试：确认订单状态 `COMPLETED` 与物流状态 `SIGNED` 分别来自正确工具，并正确读出承运商和运单号；
- 特殊定制商品测试：识别 `product_type = SPECIAL`，不直接承诺退款，建议补充凭证并转人工；
- 待付款订单测试：识别 `PENDING_PAYMENT` 和 `NOT_SHIPPED`，不在规则不完整时直接承诺退款；
- 记录了 URL 配置错误、字段来源混淆和三类测试结果；
- 工作流仍为“未发布”，未执行发布操作。

当前下一步：

1. 清理早期未连通的旧知识检索节点（删除前先确认）；
2. 增加售后资格判断节点和转人工分支；
3. 增加人工确认门槛，只有用户明确确认后才调用 `POST /after-sales/applications`；
4. 用重复请求验证幂等键和重复售后申请处理；
5. 编写 20-30 条评估集，记录通过/失败案例；
6. 在工具契约稳定后再接入 mall。

本轮新增材料：

- `docs/interview/step-03-rag.md` / `docs/interview/step-03-rag.html`：字段来源修复与三类场景测试；
- `docs/incidents/incident-index.md`：物流 URL 配置错误及测试复盘。

## Step 04 材料

- 售后申请与幂等测试：`docs/interview/step-04-after-sales.md`；
- HTML 面试材料：`docs/interview/step-04-after-sales.html`。

已验证 FastAPI 售后申请接口首次创建返回 `201`，相同幂等键重复请求返回 `200` 和 `X-Idempotent-Replay: true`。这只是接口层验证，Dify 仍未接入创建售后申请节点，后续必须先增加用户明确确认条件。

### 售后创建分支状态（2026-09-30）

已在 Dify 中搭建条件分支和 HTTP 请求节点的安全脚手架，但尚未开放执行：条件使用 `CONFIRMATION_GATE_NOT_READY`，请求体仍是占位 JSON。这样可以先保存流程结构，避免变量映射完成前误创建售后单。只有完成变量插入、专门测试并确认结果后，才会恢复“用户明确确认”条件；本工作流仍未发布。

### 安全分支回归（2026-09-30）

在售后创建条件设置为不可命中的占位值后，使用 `202609070003` 回归测试通过：原有订单/物流/RAG 输出正常，HTTP 创建节点未触发，未新增售后申请。

### 服务端执行兜底（2026-10-06）

已为特殊定制商品增加后端拦截：即使 Dify 后续误触发创建售后申请，订单 `product_type = SPECIAL` 也会返回 `409 BUSINESS_CONFLICT` 并要求转人工，不会创建申请。现有单元测试为 `7 passed`。

### Dify 创建申请联调（2026-10-06）

已完成确认分支端到端验证：待付款订单和特殊定制商品均被后端以 `409` 拦截；普通已完成订单在用户输入“确认申请售后”后返回 `201`、创建 `PENDING_REVIEW` 申请。当前待优化项是把 HTTP 返回的申请号合流到最终用户输出。

## 当前进度（2026-10-07）

本轮已完成：

- `python -m pytest -q`：`9 passed`；
- Dify 售后创建分支端到端验证；
- 用户明确确认后才创建售后申请；
- 申请号成功进入最终 Output，真实申请号为 `ASDA7035BB9B4B`，状态为 `PENDING_REVIEW`；
- 新增 `GET /orders/{order_no}/after-sales/active`，用于避免重复创建；
- 更新 Step 04、API 约定和 HTML 面试材料。

下一步：把“查询处理中售后申请”接入 Dify 确认分支，在已有申请时直接返回申请号；随后建立 20-30 条评估集。

### 重复申请查询分支联调（2026-10-09）

已解决 Dify HTTP `body` 无法直接参与条件判断的问题：增加代码节点解析 JSON，输出布尔变量 `has_active_application`。订单 `202609070001` 已成功进入“已有申请”分支，未重复调用创建接口；真实申请号为 `ASA199F40A7B8B`，状态为 `PENDING_REVIEW`。

## 项目交接与面试准备（2026-10-10）

项目交接总结：`docs/project-handoff-summary.md`

简历与面试准备：`docs/interview/resume-and-interview-prep.md`

当前状态：Dify E001-E015 全部通过，lookup 接口已验证，FastAPI pytest 全部通过。项目进入文档整理和面试准备阶段。
