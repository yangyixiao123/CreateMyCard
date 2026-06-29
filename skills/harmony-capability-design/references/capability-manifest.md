# Data Capability Input/Output Schema 设计指南

## 推荐结构

Manifest 顶层必须且只能保留以下字段：

```json
{
  "id": "domain.resource.action",
  "version": "1.0",
  "description": "一句话说明该能力面向什么卡片场景，返回什么展示友好的结果。",
  "inputSchema": {
    "type": "object",
    "properties": {},
    "required": []
  },
  "outputSchema": {
    "type": "object",
    "properties": {}
  }
}
```

不要在 manifest JSON 中加入 `source`、`runtimeInjected`、`hiddenFields`、策略对象或实现细节。底层接口来源、端侧注入字段、隐藏字段、数量长度约束、排序和格式化规则，放在正文的封装建议或使用规则中说明；其中能用 JSON Schema 表达的约束，写入 `inputSchema` / `outputSchema` 的字段定义。

## 字段命名

- `id` 使用稳定域名式命名，例如 `calendar.events.compactSearch`、`todo.items.today`、`commute.route.summary`。
- 展示字段使用 `Text` 后缀，例如 `timeText`、`titleText`、`temperatureText`、`summaryText`。
- 原始值字段可以保留无后缀名，例如 `temperatureC`、`startTimeMs`，但不要让卡片只依赖原始值。
- 数组字段用 `items`、`daily`、`routes` 等语义名。
- 详情跳转 ID 用 `entityId`、`instanceId`、`targetId` 等稳定字段；说明是否可展示，默认不可展示。

## 模型可见输入

优先暴露这些类型：

- 简单字符串：`districtName`、`keyword`、`date`。
- 语义日期：`today`、`tomorrow`、`yyyy-MM-dd`。
- 语义时间范围：`allDay`、`morning`、`afternoon`、`evening`、`next24Hours`。
- 小整数上限：`maxItems`、`forecastDays`，必须给最大值。
- 业务枚举：`priority`、`status`、`trafficType`，枚举值用模型容易理解的稳定值。

避免暴露：

- token、secret、cookie、session、accountId、deviceId。
- 毫秒时间戳、复杂 filter object、分页游标、内部 code。
- 需要端侧本地上下文才能确定的参数。

## 端侧注入与隐藏字段

端侧注入和隐藏字段只作为正文分析输出，不进入 manifest JSON。

建议用简短列表说明：

- 端侧注入：`timezone`、`locale`、`accountId`、`location` 等。
- 隐藏字段：`token`、`secret`、`deviceId`、底层 debug/code/trace 字段等。
- 模型可填字段：只保留在 `inputSchema.properties` 中。

## 输出 ViewModel

输出应适合桌面卡片直接绑定：

```json
{
  "summaryText": "今日 3 个日程",
  "items": [
    {
      "entityId": "cal-001",
      "titleText": "方案评审",
      "timeText": "09:30-10:00",
      "locationText": "A座 12F",
      "statusText": "即将开始"
    }
  ],
  "moreCount": 2,
  "updatedAtText": "06-27 18:30"
}
```

规则：

- 每个卡片可能展示的字段都提供展示友好版本。
- 数组默认裁剪到适合 `2x2` 或 `2x4` 的数量。
- 保留 `moreCount` 或 `hasMore` 表示还有更多结果。
- 如需表达空结果，可以在正常输出 schema 中提供 `emptyText`、`summaryText` 或空数组。

## 数量、长度和格式约束

当前阶段把约束写入 `inputSchema`、`outputSchema` 的 `description`、`minimum`、`maximum`、`maxItems`、`maxLength` 等字段。

```json
{
  "inputSchema": {
    "type": "object",
    "properties": {
      "maxItems": {
        "type": "integer",
        "minimum": 1,
        "maximum": 5,
        "description": "最多返回条数；不传时端侧默认返回 3 条。"
      }
    }
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "maxItems": 5,
        "description": "端侧按开始时间升序返回，默认最多 3 条，最多 5 条。",
        "items": {
          "type": "object",
          "properties": {
            "titleText": {
              "type": "string",
              "maxLength": 18,
              "description": "适合卡片展示的标题，端侧负责裁剪。"
            }
          }
        }
      }
    }
  }
}
```

约束应回答：

- 模型最多能请求几条，端侧默认返回几条。
- 输出数组最多包含几条。
- 标题、地点、摘要、状态文案最长多少字符。
- 展示字符串由端侧生成，还是模型可直接提供。
- 结果排序规则是什么。

## 转换说明

为每个关键转换写清楚端侧职责：

- 时间戳转换：模型输入 `today`，端侧按本地时区转 `[startMs,endMs]`。
- 枚举转换：模型输入 `Drive`，端侧转底层交通方式 code。
- 字符串格式化：端侧生成 `06-27 18:30`、`09:30-10:00`、`28°C`。
- 数量裁剪：端侧按 schema 约束返回前 N 条和 `moreCount`。
- 字符串裁剪：端侧生成 `titleText`，必要时保留 `titleRaw` 但默认不让卡片绑定。

## 精简能力文档模板

使用下面结构输出可放入 `harmony-card-generation/reference/data-capability/` 的文档：

````markdown
# 能力名称

```json
{
  "id": "domain.resource.action",
  "version": "1.0",
  "description": "...",
  "inputSchema": {
    "type": "object",
    "properties": {},
    "required": []
  },
  "outputSchema": {
    "type": "object",
    "properties": {}
  }
}
```

## 使用规则

- 适用于...
- CardSpec 的 `capabilityId` 使用 `...`。
- `arguments` 只能使用 `inputSchema.properties` 声明的字段。
- 推荐 `writeResultTo: "/data/..."`。
- 常用路径：`/data/.../summaryText`、`/data/.../items`。
- 初始 `updateDataModel` 使用空对象、空数组和加载态，不写真实用户数据。

```json
{
  "data": {
    "...": {
      "summaryText": "",
      "items": []
    }
  },
  "state": {
    "loading": true
  }
}
```
````
