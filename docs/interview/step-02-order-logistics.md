# 阶段记录：订单查询与物流查询工具联调

> 日期：2026-09-27
> 项目：电商售后智能体
> 阶段：Dify 工作流接入第一个外部业务工具
> 状态：已完成

## 一、目标

让 Dify 工作流能够：

1. 从开始节点接收订单号；
2. 调用 FastAPI 查询订单；
3. 调用 FastAPI 查询物流；
4. 将两个工具结果交给 LLM；
5. 通过输出节点返回结构化结果。

## 二、最终工作流

```text
开始
  ├── order_no
  └── user_question
        ↓
查询订单
  GET /orders/{order_no}
        ↓
查询物流
  GET /orders/{order_no}/logistics
        ↓
LLM
        ↓
输出 answer
```

## 三、工具接口

订单查询：

```http
GET /orders/{order_no}
```

物流查询：

```http
GET /orders/{order_no}/logistics
```

Dify Docker 访问宿主机 FastAPI 时使用：

```text
http://host.docker.internal:8001
```

查询物流节点的动态 URL 使用 Dify 变量：

```text
http://host.docker.internal:8001/orders/{用户输入/order_no}/logistics
```

## 四、最终验证结果

测试输入：

```text
order_no: 202609070001
user_question: 请查询订单状态、商品和物流状态。
```

订单工具返回：

```json
{
  "order_no": "202609070001",
  "status": "COMPLETED",
  "pay_amount": 99.9,
  "product_type": "NORMAL",
  "product_name": "示例蓝牙耳机",
  "after_sale_status": "NONE"
}
```

物流工具返回：

```json
{
  "order_no": "202609070001",
  "status": "SIGNED",
  "carrier": "示例物流",
  "tracking_no": "SF1234567890"
}
```

最终 LLM 能够生成订单信息、售后判断和下一步建议，工作流不再返回空对象。

## 五、遇到的问题与处理

### 问题 1：工作流运行结果是 `{}`

#### 现象

开始节点有输入，但测试结果没有输出。

#### 原因

工作流只有：

```text
开始 → 查询订单 → LLM
```

没有“输出”节点，LLM 结果没有被声明为工作流最终输出。

#### 处理

新增输出节点，配置：

```text
变量名：answer
变量值：LLM / text
```

#### 面试知识点

工作流节点执行成功不代表应用有最终返回值。编排系统除了关注节点状态，还要检查最终输出变量和节点之间的边连接。

### 问题 2：LLM 没有读到输入和工具结果

#### 现象

Prompt 中虽然写了 `{{用户问题变量}}` 和 `{{查询订单节点的返回结果}}`，但它们只是普通文字。

#### 原因

Dify 的变量必须通过变量选择器插入，不能把自然语言描述当作变量引用。

#### 处理

使用 Dify 变量选择器插入：

```text
用户输入 / user_question
查询订单 / body
查询物流 / body
```

#### 面试知识点

工作流平台中的变量通常带有节点作用域和类型信息。字符串、对象、数组不能混用；工具 JSON 必须以结构化对象或字符串变量传递给后续 LLM。

### 问题 3：查询物流返回 404

#### 现象

Dify 报错：

```text
Request failed with status code 404
```

#### 排查

本地直接请求正确接口：

```powershell
Invoke-RestMethod http://127.0.0.1:8001/orders/202609070001/logistics
```

接口返回 200，说明 FastAPI 路由本身正常。

#### 原因

Dify 节点 URL 没有正确拼接订单号和 `/logistics` 路径，或者订单号变量没有传入。

#### 正确地址

```text
http://host.docker.internal:8001/orders/{order_no}/logistics
```

#### 面试知识点

排查 HTTP 404 时要先区分：

1. 服务不存在；
2. 路由不存在；
3. 路径参数为空；
4. 业务对象不存在；
5. 请求实际没有到达预期服务。

不能看到 404 就直接修改后端代码，应先记录实际请求 URL 并用 curl/PowerShell 独立验证。

## 六、面试表达

可以这样介绍本阶段：

> 我使用 FastAPI 封装了订单查询和物流查询接口，并通过 Dify HTTP Request 节点接入工作流。调试过程中遇到过工作流执行成功但返回空对象、LLM Prompt 变量未真正绑定、物流接口 404 等问题。我分别通过增加输出节点、使用节点变量选择器、记录实际请求 URL 和独立验证接口的方式定位并修复，最终完成了“用户输入订单号 → 查询订单/物流 → LLM 结构化输出”的端到端链路。
