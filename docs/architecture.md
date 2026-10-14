# 第一阶段架构

```text
Dify 工作流
   ├── 意图分类
   ├── 售后规则知识库检索
   ├── HTTP Request / Tool
   │      └── after-sales-tool-service
   │             └── 当前：内存种子数据
   │             └── 后续：mall HTTP API
   └── 结构化售后结论
```

服务层使用仓储抽象的最小实现：

- `repository.py`：当前内存仓储与测试数据；
- `service.py`：业务规则、幂等与状态校验；
- `main.py`：HTTP 层、错误映射和 OpenAPI；
- `models.py`：请求/响应契约。

后续接入 mall 时，优先新增 `MallHttpRepository`，不要让 Dify 或模型直接访问数据库。
