# 电商售后智能体项目交接总结

> 更新时间：2026-10-10  
> 用途：项目整理、面试准备、后续模型接续开发  
> 项目路径：`C:\Users\ZZL\Desktop\shixixiangmu\after-sales-agent`

## 1. 用户目标

用户正在准备 Agent/Java 后端实习面试，希望完成一个真实、可运行、可解释的项目：

```text
基于 Dify + FastAPI 的电商售后智能体
```

要求：

- 每个阶段记录 Markdown 或 HTML 文档；
- 真实记录测试结果和故障，不虚构指标；
- 能够写进简历；
- 能够回答面试官关于 RAG、工作流、幂等、异常处理和后端校验的问题；
- 后续更换模型时，新模型读取本文件即可继续工作。

## 2. 项目定位与技术栈

```text
Dify：工作流编排、LLM、RAG 知识库和条件分支
FastAPI：订单、物流、售后申请工具服务
Python/Pydantic：数据模型与参数校验
pytest：后端自动化测试
Docker Desktop：Dify 本地容器访问宿主机服务
PowerShell：本地启动和接口验证
```

当前使用内存仓储，第一阶段目标是验证工具契约、业务流程和 Dify 联调，不是生产部署。

## 3. 当前系统架构

```text
用户
  ↓
Dify 工作流
  ├─ 查询订单
  ├─ 查询物流
  ├─ 售后规则知识库
  ├─ LLM 售后判断
  ├─ 用户确认条件分支
  ├─ 查询处理中售后申请
  ├─ 代码节点解析 JSON
  ├─ 判断售后创建资格
  └─ 创建售后申请 HTTP
          ↓
FastAPI 工具服务
          ↓
InMemoryRepository
```

安全链路：

```text
Prompt 约束模型
      ↓
Dify 条件分支控制调用路径
      ↓
代码节点解析和类型转换
      ↓
创建前确定性业务判断
      ↓
FastAPI 后端最终兜底
```

## 4. FastAPI 接口

```http
GET /health
GET /orders/{order_no}
GET /orders/{order_no}/logistics
GET /orders/{order_no}/after-sales/active
GET /orders/{order_no}/lookup
POST /after-sales/applications
GET /after-sales/applications/{application_id}
```

### lookup 稳定查询接口

`GET /orders/{order_no}/lookup` 专门给 Dify 使用。订单存在、订单不存在、订单号格式错误都返回 HTTP 200，通过业务字段表达结果，避免 Dify 把预期业务异常当成 HTTP 节点失败。

正常订单：

```json
{
  "found": true,
  "order_no": "202609070001",
  "status": "COMPLETED",
  "product_type": "NORMAL"
}
```

不存在订单：

```json
{
  "found": false,
  "order_no": "209901010001",
  "error_code": "NOT_FOUND",
  "message": "没有查询到该订单，请核对订单号后重试"
}
```

错误订单号：

```json
{
  "found": false,
  "order_no": "123",
  "error_code": "INVALID_ORDER_NO",
  "message": "订单号格式不正确，订单号应为 12 位数字"
}
```

### 创建售后申请

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
2. 只有 `COMPLETED` 订单可以自动提交售后；
3. `SPECIAL` 定制商品必须转人工；
4. 同一订单不能同时存在处理中售后申请；
5. 相同幂等键重复请求返回第一次结果；
6. 幂等键绑定其他订单或类型时返回 409。

## 5. 测试数据

### 普通已完成订单

```text
订单号：202609070001
订单状态：COMPLETED
商品类型：NORMAL
商品名称：示例蓝牙耳机
物流状态：SIGNED
```

### 特殊定制商品

```text
订单号：202609070002
订单状态：COMPLETED
商品类型：SPECIAL
商品名称：定制商品
物流状态：SIGNED
```

规则：不能自动创建售后申请，必须转人工审核。

### 待付款订单

```text
订单号：202609070003
订单状态：PENDING_PAYMENT
商品类型：NORMAL
商品名称：示例数据线
物流状态：NOT_SHIPPED
```

规则：只有已完成订单才能自动提交售后申请。

## 6. 当前 Dify 工作流

```text
开始
  ├─ 查询订单
  ├─ 查询物流
  ├─ 知识检索
  └─ LLM
        ↓
用户是否明确确认？
  ├─ ELSE：未确认
  │     ↓
  │   原咨询 Output
  │
  └─ IF：用户明确确认
        ↓
    查询处理中售后申请
        ↓
    解析处理中申请结果
        ↓
    是否已有处理中申请？
      ├─ IF：has_active_application == true
      │     ↓
      │   已有申请结果 LLM
      │     ↓
      │   existing_after_sale_result Output
      │
      └─ ELSE
            ↓
        判断售后创建资格
            ↓
        can_create == true？
          ├─ IF
          │   ↓
          │ 创建售后申请 HTTP
          │   ↓
          │ 申请结果 LLM
          │   ↓
          │ after_sale_result Output
          │
          └─ ELSE
              ↓
          business_rejection_message Output
```

重要配置：HTTP 节点只展示 `body`、`status_code`、`headers`、`files`，不能直接选择 `body.has_active_application`。因此增加代码节点解析 body，输出真正的布尔变量。

## 7. 已完成的安全能力

### 用户确认门槛

用户询问“这个订单可以申请售后吗？”时不会创建申请。只有“确认申请售后”“帮我提交售后”“我确认退款”等明确操作表达才进入申请判断流程。

### 重复申请保护

已有 `PENDING_REVIEW`、`APPROVED` 或 `REFUNDING` 状态时，直接返回原申请信息，不创建新的申请。

### 特殊商品拦截

特殊商品在 Dify 资格判断和 FastAPI 后端均会被拦截：

```text
特殊定制商品需要转人工审核，不能自动创建售后申请。
```

### 待付款订单拦截

```text
当前订单尚未完成，只有已完成订单才能提交售后申请。
```

### 状态解释

```text
PENDING_REVIEW：待人工审核
APPROVED：审核通过
REFUNDING：退款中
COMPLETED：退款完成
```

不能把 `PENDING_REVIEW` 解释成退款已完成。

## 8. 已完成测试

### Dify 评估集

```text
E001-E015：全部通过
```

覆盖：普通订单、已有申请、特殊商品、待付款订单、未明确确认、自然语言确认、退款状态查询、订单不存在、订单号错误、物流状态冲突、用户尚未决定等场景。

### lookup 接口

已验证：

```text
正常订单：found = true
不存在订单：found = false / NOT_FOUND
错误订单号：found = false / INVALID_ORDER_NO
```

### pytest

用户反馈最后一次 pytest 执行全部通过，终端显示绿色。后续记录时应保留终端的准确通过数量，不要只写“100%”。

## 9. 真实申请记录

历史测试中出现过：

```text
ASDA7035BB9B4B
ASA199F40A7B8B
```

由于当前使用内存仓储，重启 FastAPI 后申请数据会恢复，之后重新测试可能产生不同申请号。

最近一次重复申请查询结果：

```text
申请号：ASA199F40A7B8B
订单号：202609070001
状态：PENDING_REVIEW
创建售后申请节点：未执行
```

## 10. 已解决的主要故障

| 问题 | 根因 | 处理方式 |
|---|---|---|
| Dify 被 SSRF 拦截 | 默认禁止访问私有地址 | 配置本地 Docker 访问并重启 |
| 工作流输出 `{}` | 缺少 Output 节点 | 增加 Output 并绑定 LLM 输出 |
| 查询物流 404 | URL 缺少 `/logistics` | 修正接口路径 |
| 看不到知识检索 result | RAG 未绑定上下文 | 绑定上下文并插入特殊变量 |
| body 字段不能用于条件分支 | Dify 不自动展开 JSON | 增加代码节点解析 body |
| 409 没有业务提示 | HTTP 非 2xx 被当成节点失败 | 创建前增加资格判断 |
| 原始咨询与业务结果重复 | Output 直接连接在 LLM 后 | 移到未确认分支 |
| E012/E013 返回 404 | Dify 暴露 HTTP 异常 | 增加稳定 lookup 接口 |
| 虚拟环境激活失败 | `.venv` 尚未创建 | 当前使用全局 Python，暂不阻塞项目 |

## 11. 当前限制

- 使用内存仓储，重启服务后数据恢复；
- 尚未接入真实 mall；
- 尚未接入 MySQL 或 Redis；
- 没有生产鉴权、限流和监控；
- 当前主要用于本地开发和面试演示；
- Dify 工作流暂时保持草稿，不需要发布生产。

## 12. 下一步

1. 更新 README、API、架构和测试文档；
2. 保存 Dify、Swagger 和 pytest 截图；
3. 准备 30 秒、1 分钟和 3 分钟项目介绍；
4. 准备 RAG、幂等、异常处理、安全边界面试题；
5. 生成最终简历项目描述；
6. 后续可选：MySQL、Redis、真实 mall、鉴权和 CI/CD。

## 13. 后续模型工作规则

- 不要点击 Dify 发布，除非用户明确要求；
- 删除 Dify 节点前必须询问；
- 不要把 `PENDING_REVIEW` 描述成退款成功；
- 不要再次用已有申请订单测试新建成功；
- 不要虚构测试结果；
- 修改代码后运行 pytest；
- 每个阶段更新 Markdown 或 HTML；
- 新故障写入 `docs/incidents/incident-index.md`；
- 优先完善文档和面试材料，不要无目的增加节点。
