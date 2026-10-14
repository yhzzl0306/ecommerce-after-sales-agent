# Dify 接入下一步

## 1. 先启动工具服务

```powershell
cd C:\Users\ZZL\Desktop\shixixiangmu\after-sales-agent
uvicorn app.main:app --host 0.0.0.0 --reload --port 8001
```

先确认（保持服务终端不要关闭）：

```powershell
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8001/orders/202609070001
```

## 2. Dify 工具配置

导入 `openapi.yaml` 作为自定义工具，或使用 HTTP Request 节点逐个配置接口。

Dify 在 Docker 中运行时，宿主机服务地址使用：

```text
http://host.docker.internal:8001
```

不要使用 `http://127.0.0.1:8001`，因为那会指向 Dify 容器自身。

## 3. 推荐工作流

```text
开始
  ↓
意图分类：查订单 / 查物流 / 退款退货 / 转人工
  ↓
知识库检索：售后规则
  ↓
条件分支
  ├── 查订单 → getOrder
  ├── 查物流 → getLogistics
  └── 退款退货 → getOrder + getLogistics
                  ↓
              规则判断
                  ↓
      用户确认后再 createAfterSaleApplication
                  ↓
              结构化回复
```

## 4. 给 LLM 节点的关键约束

- 工具返回的订单不存在时，不得编造订单信息；
- 订单状态、金额、签收时间必须来自工具 JSON；
- 规则必须来自知识库检索结果；
- 创建售后前必须先得到用户明确确认；
- `idempotency_key` 应由订单号、售后类型和会话/请求标识组合生成；
- 遇到特殊商品、规则不足或已有处理中申请时，转人工。

## 5. 当前尚未完成

- 尚未在 Dify 实例中导入工具并保存工作流；
- 当前工具数据是内存种子数据，不是 mall 数据；
- 尚未接入真实售后规则知识库；
- 尚未完成端到端截图和评估记录。

