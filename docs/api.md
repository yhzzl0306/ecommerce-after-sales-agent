# API 约定

## GET /orders/{order_no}

查询订单摘要，订单号必须是 12 位数字。

## GET /orders/{order_no}/logistics

查询物流状态和签收信息。

## GET /orders/{order_no}/after-sales/active

查询订单是否存在处理中售后申请。处理中状态包括 `PENDING_REVIEW`、`APPROVED` 和 `REFUNDING`。

无申请示例：

```json
{
  "order_no": "202609070003",
  "has_active_application": false,
  "application": null
}
```

已有申请时返回申请号和状态，Dify 可据此直接告知用户，不必重复调用创建接口。

## POST /after-sales/applications

请求体：

```json
{
  "order_no": "202609070001",
  "type": "QUALITY_REFUND",
  "reason": "商品有质量问题",
  "idempotency_key": "202609070001-quality-1"
}
```

业务约束：

1. 订单必须存在；
2. 只有 `COMPLETED` 订单可以申请售后；
3. 特殊定制商品必须转人工；
4. 同一订单不能同时存在处理中申请；
5. 相同幂等键重复提交时返回第一次结果；
6. 幂等键若绑定了不同订单或类型，返回 409。

## 与 Dify 对接建议

在 Dify 中使用 HTTP Request/Tool 节点调用：

```text
GET http://host.docker.internal:8001/orders/{order_no}
GET http://host.docker.internal:8001/orders/{order_no}/logistics
GET http://host.docker.internal:8001/orders/{order_no}/after-sales/active
POST http://host.docker.internal:8001/after-sales/applications
```

Dify 运行在 Docker 时，不能直接把宿主机地址写成 `127.0.0.1`；Windows Docker Desktop 优先使用 `host.docker.internal`。工具返回 JSON 后，将其和知识库检索结果一起传给 LLM 节点。
